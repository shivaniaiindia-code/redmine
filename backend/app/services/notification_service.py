import httpx
from datetime import datetime, date, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.notification import Notification, NotificationDelivery
from app.models.alert_config import AlertRecipientConfig
from app.models.task import Task
from app.models.project import Project
from app.core.config import settings


class NotificationService:

    # ------------------------------------------------------------------ #
    #  Internal: Load the active default recipient config from DB          #
    # ------------------------------------------------------------------ #
    @staticmethod
    async def _get_recipient_config(db: AsyncSession) -> AlertRecipientConfig | None:
        res = await db.execute(
            select(AlertRecipientConfig).where(AlertRecipientConfig.is_active == True).limit(1)
        )
        return res.scalars().first()

    # ------------------------------------------------------------------ #
    #  Core dispatch: create notification + dual-dispatch channels         #
    # ------------------------------------------------------------------ #
    @staticmethod
    async def create_and_dispatch(
        db: AsyncSession,
        title: str,
        message: str,
        severity: str = "INFO",
        entity_type: str = "SYSTEM",
        entity_id: str | None = None,
        recipient_id: str | None = None,
    ) -> Notification:
        """
        Creates a notification and dispatches it to ALL channels:
          Channel 1 — In-App System Notification Bar
          Channel 2 — Admin Google Chat (Cards v2) if webhook is set

        The single default recipient (anil.aiindia@gmail.com) receives every
        alert regardless of which entity triggered it (task, project, team, employee…).
        Both in-app and external delivery are tracked separately.
        """
        # 1. Load configurable recipient
        config = await NotificationService._get_recipient_config(db)

        # 2. Persist notification
        notification = Notification(
            recipient_id=recipient_id,   # DB user FK (optional)
            title=title,
            message=message,
            severity=severity,
            entity_type=entity_type,
            entity_id=entity_id,
            is_read=False,
        )
        db.add(notification)
        await db.flush()

        # 3. Channel 1: In-App Notification Bar
        if config is None or config.in_app_enabled:
            recipient_label = config.recipient_email if config else settings.DEFAULT_ALERT_EMAIL
            in_app = NotificationDelivery(
                notification_id=notification.id,
                channel="IN_APP",
                destination=f"ADMIN_BAR:{recipient_label}",
                status="SENT",
                delivered_at=datetime.now(timezone.utc),
            )
            db.add(in_app)

        # 4. Channel 2: Google Chat (external delivery, tracked separately)
        webhook_url = (
            (config.google_chat_webhook_url if config else None)
            or settings.GOOGLE_CHAT_ADMIN_WEBHOOK_URL
        )
        google_chat_enabled = config.google_chat_enabled if config else True

        if webhook_url and google_chat_enabled:
            await NotificationService._mirror_to_google_chat(db, notification, webhook_url)
        else:
            # Record that external dispatch is pending (webhook not configured yet)
            pending = NotificationDelivery(
                notification_id=notification.id,
                channel="GOOGLE_CHAT_ADMIN",
                destination=f"PENDING:{(config.recipient_email if config else settings.DEFAULT_ALERT_EMAIL)}",
                status="PENDING_WEBHOOK",
                error_message="Google Chat webhook URL not yet configured — add it in Admin Settings.",
                delivered_at=None,
            )
            db.add(pending)

        await db.commit()
        await db.refresh(notification)
        return notification

    # ------------------------------------------------------------------ #
    #  Automated Alert Generation Engine                                   #
    # ------------------------------------------------------------------ #
    @staticmethod
    async def generate_automated_alerts(db: AsyncSession) -> list[Notification]:
        """
        Scans all active tasks and projects and generates alerts for:
          - Overdue tasks (due_date < today)  → CRITICAL / URGENT
          - Blocked tasks (is_blocked = True) → CRITICAL
          - Approaching deadlines (≤ 2 days)  → WARNING
          - Project health changes            → URGENT / CRITICAL

        All alerts route to the single configurable default recipient.
        Deduplication prevents alert storms.
        """
        today = date.today()
        created_alerts: list[Notification] = []

        # ── Tasks ─────────────────────────────────────────────────────── #
        task_rows = (
            await db.execute(
                select(Task).where(
                    ~Task.status.in_(["Resolved", "Closed", "DONE", "Completed"])
                )
            )
        ).scalars().all()

        for task in task_rows:
            # A — Overdue
            if task.due_date and task.due_date < today:
                task.is_overdue = True
                days_late = (today - task.due_date).days
                sev = "CRITICAL" if days_late >= 3 else "URGENT"
                # Deduplicate: skip if an unread overdue alert already exists for this task
                existing_overdue = (await db.execute(
                    select(Notification).where(
                        and_(
                            Notification.entity_type == "TASK",
                            Notification.entity_id == task.id,
                            Notification.is_read == False,
                            Notification.title.like("Overdue Task%"),
                        )
                    )
                )).scalars().first()
                if not existing_overdue:
                    alert = await NotificationService.create_and_dispatch(
                        db=db,
                        title=f"Overdue Task: {task.title}",
                        message=(
                            f"Task was due on {task.due_date} ({days_late} day(s) late). "
                            f"Status: {task.status}. Immediate review required."
                        ),
                        severity=sev,
                        entity_type="TASK",
                        entity_id=task.id,
                    )
                    created_alerts.append(alert)

            # B — Blocked
            if task.is_blocked:
                existing = (await db.execute(
                    select(Notification).where(
                        and_(
                            Notification.entity_type == "TASK",
                            Notification.entity_id == task.id,
                            Notification.is_read == False,
                            Notification.title.like("Blocker Alert%"),
                        )
                    )
                )).scalars().first()
                if not existing:
                    reason = task.blocker_reason or "Blocked by upstream dependency"
                    alert = await NotificationService.create_and_dispatch(
                        db=db,
                        title=f"Blocker Alert: {task.title}",
                        message=f"Task is operationally blocked: '{reason}'. Progress stalled.",
                        severity="CRITICAL",
                        entity_type="TASK",
                        entity_id=task.id,
                    )
                    created_alerts.append(alert)

            # C — Approaching deadline (≤ 2 days)
            if task.due_date and 0 <= (task.due_date - today).days <= 2:
                days_left = (task.due_date - today).days
                existing = (await db.execute(
                    select(Notification).where(
                        and_(
                            Notification.entity_type == "TASK",
                            Notification.entity_id == task.id,
                            Notification.is_read == False,
                            Notification.title.like("Deadline Warning%"),
                        )
                    )
                )).scalars().first()
                if not existing:
                    day_str = "today" if days_left == 0 else ("tomorrow" if days_left == 1 else "in 2 days")
                    alert = await NotificationService.create_and_dispatch(
                        db=db,
                        title=f"Deadline Warning: {task.title}",
                        message=f"Task deadline is {day_str} ({task.due_date}). Verification required.",
                        severity="WARNING",
                        entity_type="TASK",
                        entity_id=task.id,
                    )
                    created_alerts.append(alert)

        # ── Projects ──────────────────────────────────────────────────── #
        proj_rows = (
            await db.execute(select(Project).where(Project.status == "ACTIVE"))
        ).scalars().all()

        for project in proj_rows:
            p_tasks = (
                await db.execute(select(Task).where(Task.project_id == project.id))
            ).scalars().all()
            overdue_count = sum(1 for t in p_tasks if t.is_overdue)
            blocked_count = sum(1 for t in p_tasks if t.is_blocked)

            # Update health
            if blocked_count > 0:
                project.health_status = "BLOCKED"
                project.health_reason = f"{blocked_count} critical blocker(s) impeding delivery"
                new_sev = "CRITICAL"
            elif overdue_count >= 2:
                project.health_status = "AT_RISK"
                project.health_reason = f"{overdue_count} tasks are overdue"
                new_sev = "URGENT"
            elif overdue_count == 1:
                project.health_status = "AT_RISK"
                project.health_reason = "1 task overdue"
                new_sev = "URGENT"
            else:
                project.health_status = "ON_TRACK"
                project.health_reason = "Milestones tracking on schedule"
                new_sev = None

            if new_sev:
                existing = (await db.execute(
                    select(Notification).where(
                        and_(
                            Notification.entity_type == "PROJECT",
                            Notification.entity_id == project.id,
                            Notification.is_read == False,
                        )
                    )
                )).scalars().first()
                if not existing:
                    alert = await NotificationService.create_and_dispatch(
                        db=db,
                        title=f"Project Health Alert: {project.name}",
                        message=(
                            f"Project health is now {project.health_status}: "
                            f"{project.health_reason}."
                        ),
                        severity=new_sev,
                        entity_type="PROJECT",
                        entity_id=project.id,
                    )
                    created_alerts.append(alert)

        await db.commit()
        return created_alerts

    # ------------------------------------------------------------------ #
    #  Google Chat Cards v2 Mirroring                                      #
    # ------------------------------------------------------------------ #
    @staticmethod
    async def _mirror_to_google_chat(
        db: AsyncSession, notification: Notification, webhook_url: str
    ):
        icon_map = {
            "INFO": "https://img.icons8.com/color/48/info--v1.png",
            "WARNING": "https://img.icons8.com/color/48/warning-shield.png",
            "URGENT": "https://img.icons8.com/color/48/alarm.png",
            "CRITICAL": "https://img.icons8.com/color/48/error--v1.png",
        }

        card_payload = {
            "cardsV2": [
                {
                    "cardId": f"admin-mirror-{notification.id}",
                    "card": {
                        "header": {
                            "title": f"[CIP ALERT] {notification.severity}: {notification.title}",
                            "subtitle": (
                                f"Category: {notification.entity_type} | "
                                f"{notification.created_at.strftime('%Y-%m-%d %H:%M UTC')}"
                            ),
                            "imageUrl": icon_map.get(notification.severity, icon_map["INFO"]),
                            "imageType": "CIRCLE",
                        },
                        "sections": [
                            {
                                "widgets": [
                                    {
                                        "decoratedText": {
                                            "topLabel": "Alert Details",
                                            "text": f"<b>{notification.message}</b>",
                                            "wrapText": True,
                                        }
                                    }
                                ]
                            }
                        ],
                    },
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(webhook_url, json=card_payload)
                delivery = NotificationDelivery(
                    notification_id=notification.id,
                    channel="GOOGLE_CHAT_ADMIN",
                    destination=webhook_url,
                    status="SENT" if res.status_code == 200 else "FAILED",
                    response_payload=res.text[:500],
                    delivered_at=datetime.now(timezone.utc) if res.status_code == 200 else None,
                )
                db.add(delivery)
        except Exception as exc:
            delivery = NotificationDelivery(
                notification_id=notification.id,
                channel="GOOGLE_CHAT_ADMIN",
                destination=webhook_url,
                status="FAILED",
                error_message=str(exc),
            )
            db.add(delivery)


notification_service = NotificationService()
