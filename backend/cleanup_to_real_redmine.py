import asyncio
from sqlalchemy import select, delete
from app.core.database import async_session_factory
from app.models.project import Project
from app.models.task import Task
from app.models.notification import Notification, NotificationDelivery
from app.models.redmine_sync import RedmineMapping
from app.services.redmine_service import redmine_service
from app.services.notification_service import notification_service


async def purge_and_sync():
    async with async_session_factory() as db:
        print("1. Syncing fresh from Redmine...")
        sync_result = await redmine_service.sync_all(db)
        print(f"Sync result: {sync_result}")

        # Get all mapped Redmine project IDs and task IDs
        proj_mappings = (
            await db.execute(
                select(RedmineMapping.internal_id).where(
                    RedmineMapping.entity_type == "PROJECT"
                )
            )
        ).scalars().all()
        mapped_project_ids = set(proj_mappings)

        task_mappings = (
            await db.execute(
                select(RedmineMapping.internal_id).where(
                    RedmineMapping.entity_type.in_(["TASK", "ISSUE"])
                )
            )
        ).scalars().all()
        mapped_task_ids = set(task_mappings)

        print(f"Mapped projects from Redmine: {len(mapped_project_ids)}")
        print(f"Mapped tasks from Redmine: {len(mapped_task_ids)}")

        # 2. Delete tasks not in Redmine
        all_tasks = (await db.execute(select(Task))).scalars().all()
        fake_task_count = 0
        for t in all_tasks:
            if t.id not in mapped_task_ids:
                # Also delete notifications referencing this task
                await db.execute(
                    delete(Notification).where(
                        Notification.entity_id == t.id
                    )
                )
                await db.delete(t)
                fake_task_count += 1
        print(f"Purged {fake_task_count} non-Redmine tasks.")

        # 3. Delete projects not in Redmine
        all_projs = (await db.execute(select(Project))).scalars().all()
        fake_proj_count = 0
        for p in all_projs:
            if p.id not in mapped_project_ids:
                await db.execute(
                    delete(Notification).where(
                        Notification.entity_id == p.id
                    )
                )
                await db.delete(p)
                fake_proj_count += 1
        print(f"Purged {fake_proj_count} non-Redmine projects.")

        # 4. Clean up notifications that don't belong to any real entity
        all_notifs = (await db.execute(select(Notification))).scalars().all()
        for n in all_notifs:
            if n.title in [
                "ANPR System deadline in 2 days",
                "3 overdue tasks in your team",
            ]:
                await db.delete(n)

        await db.commit()

        # 5. Re-run automated alerts strictly on genuine Redmine data
        alerts = await notification_service.generate_automated_alerts(db)
        print(f"Generated {len(alerts)} alerts strictly from real Redmine data.")

        # 6. Report final state
        remaining_projects = (await db.execute(select(Project))).scalars().all()
        remaining_tasks = (await db.execute(select(Task))).scalars().all()
        print("\n--- FINAL LIVE REDMINE DATA IN PLATFORM ---")
        print(f"Total Projects: {len(remaining_projects)}")
        for p in remaining_projects:
            print(f"  • [{p.code}] {p.name} (Health: {p.health_status})")
        print(f"\nTotal Tasks: {len(remaining_tasks)}")
        for t in remaining_tasks:
            print(f"  • {t.title} [Status: {t.status}, Due: {t.due_date}]")


if __name__ == "__main__":
    asyncio.run(purge_and_sync())
