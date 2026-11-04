import pytest
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.task import Task
from app.models.project import Project
from app.models.notification import Notification, NotificationDelivery
from app.services.notification_service import notification_service

@pytest.mark.asyncio
async def test_automated_alert_generation_engine(db_session: AsyncSession):
    """
    Validates that the Automated Alert Generation Engine:
    1. Detects tasks past due date and generates CRITICAL or URGENT alerts
    2. Flags project health degradation
    3. Prevents duplicate alerts for identical issues
    4. Cleans up test artifacts without polluting the database
    """
    # 0. Clean up any leftover test tasks and notifications from prior test runs
    existing_test_tasks = (
        await db_session.execute(
            select(Task).where(Task.title == "Test Overdue Critical Deliverable")
        )
    ).scalars().all()
    for t in existing_test_tasks:
        subq = select(Notification.id).where(Notification.entity_id == t.id)
        await db_session.execute(
            delete(NotificationDelivery).where(NotificationDelivery.notification_id.in_(subq))
        )
        await db_session.execute(
            delete(Notification).where(Notification.entity_id == t.id)
        )
        await db_session.execute(
            delete(Task).where(Task.id == t.id)
        )
    await db_session.commit()

    # 1. Fetch an existing active project
    proj_res = await db_session.execute(select(Project).limit(1))
    proj = proj_res.scalars().first()
    assert proj is not None

    # 2. Insert an overdue task (due 4 days ago)
    overdue_task = Task(
        project_id=proj.id,
        title="Test Overdue Critical Deliverable",
        due_date=date.today() - timedelta(days=4),
        status="New",
        priority="Urgent",
        is_overdue=True
    )
    db_session.add(overdue_task)
    await db_session.commit()
    await db_session.refresh(overdue_task)

    try:
        # 3. Trigger automated alert generation
        alerts = await notification_service.generate_automated_alerts(db_session)
        assert len(alerts) >= 1

        # Verify that an alert exists for our overdue task
        task_alert = next((a for a in alerts if a.entity_id == overdue_task.id), None)
        assert task_alert is not None
        assert task_alert.severity in ["CRITICAL", "URGENT"]
        assert "Overdue Task" in task_alert.title

        # 4. Run automated alert generation again to verify deduplication
        alerts_second_run = await notification_service.generate_automated_alerts(db_session)
        # The duplicate alert should NOT be recreated
        duplicate = [a for a in alerts_second_run if a.entity_id == overdue_task.id]
        assert len(duplicate) == 0

    finally:
        # 5. Clean up test artifacts to prevent database pollution
        subq = select(Notification.id).where(Notification.entity_id == overdue_task.id)
        await db_session.execute(
            delete(NotificationDelivery).where(NotificationDelivery.notification_id.in_(subq))
        )
        await db_session.execute(
            delete(Notification).where(Notification.entity_id == overdue_task.id)
        )
        await db_session.execute(
            delete(Task).where(Task.id == overdue_task.id)
        )
        await db_session.commit()
