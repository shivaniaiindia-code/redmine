from datetime import datetime, date, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.models.notification import Notification, NotificationDelivery
from app.models.alert_config import AlertRecipientConfig, AlertEmailRecipient
from app.models.task import Task
from app.models.project import Project
from app.core.config import settings
from app.models.employee import Employee
from app.models.redmine_sync import RedmineMapping
from app.services.email_service import email_service, REASON_LIST, REASON_ASSIGNEE, REASON_MANAGER
from app.services.alert_composer import alert_composer


# Redmine statuses (normalized by the sync engine) that mean "work is finished"
COMPLETED_TASK_STATUSES = ["DONE", "Resolved", "Closed", "Completed"]

# Title prefixes used by the automated engine (also drive deduplication)
PREFIX_OVERDUE = "Overdue Task"
PREFIX_BLOCKED = "Blocker Alert"
PREFIX_DEADLINE = "Deadline Warning"
PREFIX_PRIORITY = "Priority Escalation"
PREFIX_COMPLETED = "Task Completed"
PREFIX_PROJECT_HEALTH = "Project Health Alert"

# Email recipient scopes
SCOPE_ALL = "ALL"                          # same as the System Notification Bar
SCOPE_URGENT_CRITICAL = "URGENT_CRITICAL"  # only URGENT / CRITICAL
EMAIL_SCOPES = (SCOPE_ALL, SCOPE_URGENT_CRITICAL)

# Notification categories exposed to the UI filter pills
CATEGORIES = ("critical", "urgent", "completed", "info")

# A repeat alert for the same entity/rule is suppressed for this long even after
# it is marked read — prevents "Mark all read" from re-emailing every open issue.
REALERT_WINDOW = timedelta(hours=24)

# Completed-task alerts only for tasks closed recently (no flood of historical closures)
COMPLETION_LOOKBACK = timedelta(days=7)

# Failed emails (network / mail server trouble) are retried with these waits;
# after the last one the delivery is marked FAILED for good.
RETRY_DELAYS = (timedelta(minutes=2), timedelta(minutes=10), timedelta(minutes=30))
MAX_EMAIL_ATTEMPTS = 1 + len(RETRY_DELAYS)


def categorize(severity: str, title: str) -> str:
    """Deterministic category used by the notification filter pills."""
    if title.startswith(PREFIX_COMPLETED):
        return "completed"
    sev = (severity or "").upper()
    if sev == "CRITICAL":
        return "critical"
    if sev == "URGENT":
        return "urgent"
    return "info"


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class NotificationService:

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #
    @staticmethod
    async def _get_recipient_config(db: AsyncSession) -> AlertRecipientConfig | None:
        res = await db.execute(
            select(AlertRecipientConfig).where(AlertRecipientConfig.is_active == True).limit(1)
        )
        return res.scalars().first()

    @staticmethod
    async def email_recipients_for(db: AsyncSession, severity: str) -> list[AlertEmailRecipient]:
        """Active email recipients that should receive a notification of this severity."""
        rows = (await db.execute(
            select(AlertEmailRecipient)
            .where(AlertEmailRecipient.is_active == True)
            .order_by(AlertEmailRecipient.created_at)
        )).scalars().all()
        urgent = severity in email_service.alert_severities()
        return [r for r in rows if r.notify_scope == SCOPE_ALL or (r.notify_scope == SCOPE_URGENT_CRITICAL and urgent)]

    @staticmethod
    async def seed_email_recipients_if_empty(db: AsyncSession) -> None:
        """Fresh installs: the designated administrator becomes the first recipient (urgent & critical)."""
        exists = (await db.execute(select(AlertEmailRecipient.id).limit(1))).first()
        if exists:
            return
        config = await NotificationService._get_recipient_config(db)
        db.add(AlertEmailRecipient(
            email=(config.recipient_email if config else settings.DEFAULT_ALERT_EMAIL).lower(),
            name=config.recipient_name if config else settings.DEFAULT_ALERT_NAME,
            notify_scope=SCOPE_URGENT_CRITICAL,
            is_active=True,
        ))
        await db.commit()

    @staticmethod
    async def _alert_exists(
        db: AsyncSession,
        entity_type: str,
        entity_id: str,
        title_prefix: str | None,
        window: timedelta | None = REALERT_WINDOW,
    ) -> bool:
        """
        True when an equivalent alert should be suppressed:
          - an UNREAD alert for the same entity/rule exists, or
          - any alert for the same entity/rule was raised inside `window`
            (window=None means "ever" — used for one-shot completion alerts).
        """
        conditions = [Notification.entity_type == entity_type, Notification.entity_id == entity_id]
        if title_prefix:
            conditions.append(Notification.title.like(f"{title_prefix}%"))
        rows = (await db.execute(select(Notification).where(and_(*conditions)))).scalars().all()
        if not rows:
            return False
        if window is None:
            return True
        cutoff = datetime.now(timezone.utc) - window
        for n in rows:
            if not n.is_read:
                return True
            created = _as_utc(n.created_at)
            if created and created >= cutoff:
                return True
        return False

    @staticmethod
    def deep_link(notification: Notification) -> str:
        category = categorize(notification.severity, notification.title)
        base = settings.APP_BASE_URL.rstrip("/")
        return f"{base}/?notifications=open&category={category}&id={notification.id}"

    # ------------------------------------------------------------------ #
    #  Core dispatch: in-app bar + SMTP email (URGENT / CRITICAL)          #
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
        Creates a notification and delivers it:
          Channel 1 — In-App System Notification Bar (every notification)
          Channel 2 — SMTP email to every active recipient configured in
                      Administration: scope ALL gets every notification, scope
                      URGENT_CRITICAL only EMAIL_ALERT_SEVERITIES (URGENT, CRITICAL)
        Every delivery attempt is tracked in notification_deliveries.
        """
        severity = (severity or "INFO").upper()
        config = await NotificationService._get_recipient_config(db)
        recipient_email = config.recipient_email if config else settings.DEFAULT_ALERT_EMAIL

        notification = Notification(
            recipient_id=recipient_id,
            title=title,
            message=message,
            severity=severity,
            entity_type=entity_type,
            entity_id=entity_id,
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(notification)
        await db.flush()

        # Channel 1: In-App Notification Bar
        if config is None or config.in_app_enabled:
            db.add(NotificationDelivery(
                notification_id=notification.id,
                channel="IN_APP",
                destination=f"ADMIN_BAR:{recipient_email}",
                status="SENT",
                delivered_at=datetime.now(timezone.utc),
            ))

        # Channel 2: SMTP email — the recipient list (scope-matched) plus, when enabled
        # in Administration, the task assignee and project manager (urgent / critical only)
        targets = await NotificationService.email_targets_for(db, notification, config)
        email_enabled = config.email_enabled if config else True
        content = None
        if targets and email_enabled and email_service.is_configured():
            # One LLM-structured email per notification (template fallback inside)
            content = await alert_composer.compose(db, notification, categorize(severity, title))
        for email, name, reason in targets:
            if not email_enabled:
                db.add(NotificationDelivery(
                    notification_id=notification.id,
                    channel="EMAIL_SMTP",
                    destination=email,
                    status="DISABLED",
                    error_message="Email channel disabled in Admin Settings.",
                ))
                continue
            if content is None:  # SMTP not configured → recorded as NOT_CONFIGURED by send()
                result = await email_service.send_alert(
                    to_email=email, to_name=name, title=title, message=message, severity=severity,
                    entity_type=entity_type, created_at_label=notification.created_at.strftime("%Y-%m-%d %H:%M UTC"),
                    deep_link=NotificationService.deep_link(notification),
                )
            else:
                result = await email_service.send_structured(
                    email, name, content, NotificationService.deep_link(notification), reason
                )
            db.add(NotificationService._delivery_from_result(notification.id, email, result, attempt=1))

        await db.commit()
        await db.refresh(notification)
        return notification


    # ------------------------------------------------------------------ #
    #  Email routing                                                       #
    # ------------------------------------------------------------------ #
    @staticmethod
    async def _responsible_employee(db: AsyncSession, employee_id: str | None) -> Employee | None:
        """An active employee synced from Redmine with a usable email (never placeholder accounts)."""
        if not employee_id:
            return None
        emp = await db.get(Employee, employee_id)
        if not emp or emp.status != "ACTIVE" or "@" not in (emp.email or ""):
            return None
        mapped = (await db.execute(select(RedmineMapping.id).where(
            RedmineMapping.entity_type == "USER", RedmineMapping.internal_id == emp.id).limit(1))).first()
        return emp if mapped else None

    @staticmethod
    async def email_targets_for(db: AsyncSession, n: Notification,
                                config: AlertRecipientConfig | None) -> list[tuple[str, str, str]]:
        """(email, name, reason) for everyone who should get this notification by email, de-duplicated."""
        targets: dict[str, tuple[str, str, str]] = {}
        for r in await NotificationService.email_recipients_for(db, n.severity):
            targets.setdefault(r.email.lower(), (r.email, r.name, REASON_LIST))

        urgent = n.severity in email_service.alert_severities()
        if config is None or not urgent or not (config.notify_assignee or config.notify_project_manager):
            return list(targets.values())

        assignee_id = manager_id = None
        if n.entity_type == "TASK" and n.entity_id:
            task = await db.get(Task, n.entity_id)
            if task:
                assignee_id = task.assigned_to_id
                project = await db.get(Project, task.project_id) if task.project_id else None
                manager_id = project.project_manager_id if project else None
        elif n.entity_type == "PROJECT" and n.entity_id:
            project = await db.get(Project, n.entity_id)
            manager_id = project.project_manager_id if project else None

        people = []
        if config.notify_assignee:
            people.append((assignee_id, REASON_ASSIGNEE))
        if config.notify_project_manager:
            people.append((manager_id, REASON_MANAGER))
        for emp_id, reason in people:
            emp = await NotificationService._responsible_employee(db, emp_id)
            if emp:
                name = f"{emp.first_name} {emp.last_name}".strip().title()
                targets.setdefault(emp.email.lower(), (emp.email, name, reason))
        return list(targets.values())

    # ------------------------------------------------------------------ #
    #  Delivery bookkeeping & automatic retry                              #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _delivery_from_result(notification_id: str, email: str, result, attempt: int) -> NotificationDelivery:
        now = datetime.now(timezone.utc)
        status, next_retry = result.status, None
        error = None if result.success else result.detail
        if not result.success and result.retryable and attempt < MAX_EMAIL_ATTEMPTS:
            status, next_retry = "RETRYING", now + RETRY_DELAYS[attempt - 1]
            error = f"{result.detail} Will retry automatically."
        elif not result.success and result.retryable:
            error = f"{result.detail} Gave up after {attempt} attempts."
        return NotificationDelivery(
            notification_id=notification_id,
            channel="EMAIL_SMTP",
            destination=email,
            status=status,
            attempt_count=attempt,
            response_payload=result.detail if result.success else None,
            error_message=error,
            delivered_at=now if result.success else None,
            next_retry_at=next_retry,
        )

    @staticmethod
    async def _reason_and_name_for(db: AsyncSession, email: str, n: Notification) -> tuple[str, str]:
        r = (await db.execute(select(AlertEmailRecipient).where(
            AlertEmailRecipient.email == email.lower()))).scalars().first()
        if r:
            return REASON_LIST, r.name
        emp = (await db.execute(select(Employee).where(Employee.email == email))).scalars().first()
        name = f"{emp.first_name} {emp.last_name}".strip().title() if emp else ""
        return (REASON_ASSIGNEE if n.entity_type == "TASK" else REASON_MANAGER), name

    @staticmethod
    async def retry_pending_emails(db: AsyncSession) -> int:
        """Re-sends emails whose earlier attempt hit a temporary failure. Returns how many were delivered."""
        now = datetime.now(timezone.utc)
        rows = (await db.execute(select(NotificationDelivery).where(
            NotificationDelivery.channel == "EMAIL_SMTP",
            NotificationDelivery.status == "RETRYING",
        ))).scalars().all()
        due = [d for d in rows if (_as_utc(d.next_retry_at) or now) <= now]
        if not due or not email_service.is_configured():
            return 0
        delivered, contents = 0, {}
        for d in due:
            n = await db.get(Notification, d.notification_id)
            if n is None:
                d.status, d.next_retry_at = "FAILED", None
                continue
            if n.id not in contents:
                contents[n.id] = await alert_composer.compose(db, n, categorize(n.severity, n.title))
            reason, name = await NotificationService._reason_and_name_for(db, d.destination, n)
            result = await email_service.send_structured(
                d.destination, name, contents[n.id], NotificationService.deep_link(n), reason)
            attempt = (d.attempt_count or 1) + 1
            fresh = NotificationService._delivery_from_result(n.id, d.destination, result, attempt)
            d.status, d.attempt_count, d.next_retry_at = fresh.status, attempt, fresh.next_retry_at
            d.response_payload, d.delivered_at = fresh.response_payload, fresh.delivered_at
            d.error_message = fresh.error_message
            delivered += int(result.success)
        await db.commit()
        return delivered

    # ------------------------------------------------------------------ #
    #  Automated Alert Generation Engine                                   #
    # ------------------------------------------------------------------ #
    @staticmethod
    async def generate_automated_alerts(db: AsyncSession) -> list[Notification]:
        """
        Deterministic scan of synchronized Redmine data:
          - Overdue tasks (due_date < today)                 → URGENT (<3d) / CRITICAL (≥3d)
          - Blocked tasks                                    → CRITICAL
          - Open issues with Redmine priority Immediate/Urgent → CRITICAL / URGENT
          - Approaching deadlines (≤ 2 days)                 → WARNING
          - Tasks completed/closed in Redmine (last 7 days)  → INFO, category "completed"
          - Project health degradation                       → URGENT / CRITICAL
        Deduplication: one alert per entity+rule while unread, and at most once
        per 24h after being read (completion alerts: once ever).
        """
        today = date.today()
        created_alerts: list[Notification] = []

        async def raise_alert(prefix, entity_type, entity_id, title, message, severity, window=REALERT_WINDOW):
            if await NotificationService._alert_exists(db, entity_type, entity_id, prefix, window):
                return
            alert = await NotificationService.create_and_dispatch(
                db=db, title=title, message=message, severity=severity,
                entity_type=entity_type, entity_id=entity_id,
            )
            created_alerts.append(alert)

        # ── Open tasks ─────────────────────────────────────────────────── #
        open_tasks = (
            await db.execute(
                select(Task).where(
                    ~Task.status.in_(COMPLETED_TASK_STATUSES),
                    Task.progress_percentage < 100
                )
            )
        ).scalars().all()

        for task in open_tasks:
            # A — Overdue
            if task.due_date and task.due_date < today:
                task.is_overdue = True
                days_late = (today - task.due_date).days
                await raise_alert(
                    PREFIX_OVERDUE, "TASK", task.id,
                    f"{PREFIX_OVERDUE}: {task.title}",
                    f"Task was due on {task.due_date} ({days_late} day(s) late). "
                    f"Status: {task.status}. Priority: {task.priority}. Immediate review required.",
                    "CRITICAL" if days_late >= 3 else "URGENT",
                )

            # B — Blocked
            if task.is_blocked:
                reason = task.blocker_reason or "Blocked by upstream dependency"
                await raise_alert(
                    PREFIX_BLOCKED, "TASK", task.id,
                    f"{PREFIX_BLOCKED}: {task.title}",
                    f"Task is operationally blocked: '{reason}'. Progress stalled.",
                    "CRITICAL",
                )

            # C — Redmine priority escalation (Immediate / Urgent)
            prio = (task.priority or "").strip().lower()
            if prio in ("immediate", "urgent"):
                await raise_alert(
                    PREFIX_PRIORITY, "TASK", task.id,
                    f"{PREFIX_PRIORITY}: {task.title}",
                    f"Redmine issue is open with priority '{task.priority}'. Status: {task.status}."
                    + (f" Due {task.due_date}." if task.due_date else ""),
                    "CRITICAL" if prio == "immediate" else "URGENT",
                )

            # D — Approaching deadline (≤ 2 days)
            if task.due_date and 0 <= (task.due_date - today).days <= 2:
                days_left = (task.due_date - today).days
                day_str = "today" if days_left == 0 else ("tomorrow" if days_left == 1 else "in 2 days")
                await raise_alert(
                    PREFIX_DEADLINE, "TASK", task.id,
                    f"{PREFIX_DEADLINE}: {task.title}",
                    f"Task deadline is {day_str} ({task.due_date}). Verification required.",
                    "WARNING",
                )

        # ── Recently completed / closed tasks ─────────────────────────── #
        cutoff = datetime.now(timezone.utc) - COMPLETION_LOOKBACK
        done_tasks = (
            await db.execute(
                select(Task).where(
                    or_(
                        Task.status.in_(COMPLETED_TASK_STATUSES),
                        Task.progress_percentage >= 100
                    )
                )
            )
        ).scalars().all()
        for task in done_tasks:
            updated = _as_utc(task.updated_at)
            if task.is_overdue:
                task.is_overdue = False
            if updated is None or updated < cutoff:
                continue
            await raise_alert(
                PREFIX_COMPLETED, "TASK", task.id,
                f"{PREFIX_COMPLETED}: {task.title}",
                f"Redmine issue was completed/closed (status: {task.status}) on "
                f"{updated.strftime('%Y-%m-%d %H:%M UTC')}.",
                "INFO",
                window=None,
            )

        # ── Projects ──────────────────────────────────────────────────── #
        proj_rows = (
            await db.execute(select(Project).where(Project.status == "ACTIVE"))
        ).scalars().all()

        for project in proj_rows:
            p_tasks = (
                await db.execute(select(Task).where(Task.project_id == project.id))
            ).scalars().all()
            open_p = [t for t in p_tasks if t.status not in COMPLETED_TASK_STATUSES and (t.progress_percentage or 0) < 100]
            overdue_count = sum(1 for t in open_p if t.due_date and t.due_date < today)
            blocked_count = sum(1 for t in open_p if t.is_blocked)

            if blocked_count > 0:
                project.health_status = "BLOCKED"
                project.health_reason = f"{blocked_count} critical blocker(s) impeding delivery"
                new_sev = "CRITICAL"
            elif overdue_count >= 1:
                project.health_status = "AT_RISK"
                project.health_reason = f"{overdue_count} task(s) overdue" if overdue_count > 1 else "1 task overdue"
                new_sev = "URGENT"
            else:
                project.health_status = "ON_TRACK"
                project.health_reason = "Milestones tracking on schedule"
                new_sev = None

            if new_sev:
                await raise_alert(
                    PREFIX_PROJECT_HEALTH, "PROJECT", project.id,
                    f"{PREFIX_PROJECT_HEALTH}: {project.name}",
                    f"Project health is now {project.health_status}: {project.health_reason}.",
                    new_sev,
                )

        await db.commit()
        return created_alerts


notification_service = NotificationService()
