from datetime import datetime, date, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from app.models.project import Project
from app.models.task import Task
from app.models.employee import Employee
from app.models.team import Team
from app.models.notification import Notification
from app.models.redmine_sync import RedmineSyncState
from app.core.config import settings
from app.services.email_service import email_service
from app.schemas.company import (
    CompanyDashboardData, KPICard, ProjectStatusOverview, DonutSegment,
    TaskDistributionItem, TeamWorkloadItem, DeadlineItem, ActivityItem,
    SystemNotificationBarItem, IntegrationStatus
)

class AnalyticsService:
    @staticmethod
    async def get_dashboard_metrics(db: AsyncSession) -> CompanyDashboardData:
        today = date.today()

        # 1. Project status metrics
        active_projects_count = (await db.execute(select(func.count(Project.id)).where(Project.status == "ACTIVE"))).scalar() or 0
        at_risk_count = (await db.execute(select(func.count(Project.id)).where(Project.health_status.in_(["AT_RISK", "BLOCKED"])))).scalar() or 0
        on_track_count = (await db.execute(select(func.count(Project.id)).where(Project.health_status == "ON_TRACK"))).scalar() or 0
        completed_projects_count = (await db.execute(select(func.count(Project.id)).where(Project.status == "COMPLETED"))).scalar() or 0
        
        # 2. Task metrics
        total_open_tasks = (await db.execute(select(func.count(Task.id)).where(~Task.status.in_(["Resolved", "Closed", "DONE", "Completed"]), Task.progress_percentage < 100))).scalar() or 0
        completed_tasks = (await db.execute(select(func.count(Task.id)).where(or_(Task.status.in_(["Resolved", "Closed", "DONE", "Completed"]), Task.progress_percentage >= 100)))).scalar() or 0
        overdue_tasks = (await db.execute(select(func.count(Task.id)).where(Task.is_overdue == True, Task.progress_percentage < 100))).scalar() or 0
        blocked_tasks = (await db.execute(select(func.count(Task.id)).where(Task.is_blocked == True))).scalar() or 0
        in_progress_tasks = (await db.execute(select(func.count(Task.id)).where(Task.status == "In Progress"))).scalar() or 0
        pending_tasks = (await db.execute(select(func.count(Task.id)).where(Task.status == "New"))).scalar() or 0

        total_tasks_all = total_open_tasks + completed_tasks
        completion_pct = round((completed_tasks / total_tasks_all * 100), 1) if total_tasks_all > 0 else 0.0

        # 3. Employee and Team counts
        employee_count = (await db.execute(select(func.count(Employee.id)).where(Employee.status == "ACTIVE"))).scalar() or 0
        teams_count = (await db.execute(select(func.count(Team.id)).where(Team.is_active == True))).scalar() or 0

        # Live Display values
        display_active_proj = active_projects_count
        display_open_tasks = total_open_tasks
        display_at_risk = at_risk_count
        display_employees = employee_count
        display_teams = teams_count if teams_count > 0 else 1
        display_completion = f"{int(completion_pct)}%"

        kpis = [
            KPICard(id="active_projects", label="Active Projects", value=str(display_active_proj), trend="Live from Redmine", trend_type="up", icon="folder"),
            KPICard(id="open_tasks", label="Open Tasks", value=str(display_open_tasks), trend=f"{overdue_tasks} overdue", trend_type="danger" if overdue_tasks > 0 else "neutral", icon="check_square"),
            KPICard(id="projects_at_risk", label="Projects at Risk", value=str(display_at_risk), trend=f"{blocked_tasks} blocked tasks", trend_type="danger" if display_at_risk > 0 else "neutral", icon="alert_triangle"),
            KPICard(id="total_employees", label="Total Employees", value=str(display_employees), trend="Synced members", trend_type="neutral", icon="users"),
            KPICard(id="teams", label="Teams", value=str(display_teams), trend="Active units", trend_type="neutral", icon="layers"),
            KPICard(id="task_completion", label="Task Completion", value=display_completion, trend=f"{completed_tasks} completed", trend_type="up", icon="check_circle")
        ]

        # Donut Chart: Project Status
        total_p = display_active_proj if display_active_proj > 0 else 1
        on_track_pct = round(on_track_count / total_p * 100, 1)
        at_risk_pct = round(at_risk_count / total_p * 100, 1)
        completed_pct = round(completed_projects_count / total_p * 100, 1)
        other_pct = max(0.0, 100.0 - (on_track_pct + at_risk_pct + completed_pct))

        donut = ProjectStatusOverview(
            total_projects=display_active_proj,
            segments=[
                DonutSegment(name="On Track", count=on_track_count, percentage=on_track_pct, color="#10B981"),
                DonutSegment(name="At Risk", count=at_risk_count, percentage=at_risk_pct, color="#EF4444"),
                DonutSegment(name="In Progress", count=max(0, display_active_proj - on_track_count - at_risk_count), percentage=other_pct, color="#3B82F6"),
                DonutSegment(name="Completed", count=completed_projects_count, percentage=completed_pct, color="#8B5CF6")
            ]
        )

        # Bar Chart: Task Distribution
        task_dist = [
            TaskDistributionItem(status="In Progress", count=in_progress_tasks, color="#8B5CF6"),
            TaskDistributionItem(status="New", count=pending_tasks, color="#3B82F6"),
            TaskDistributionItem(status="Overdue", count=overdue_tasks, color="#EF4444"),
            TaskDistributionItem(status="Blocked", count=blocked_tasks, color="#F59E0B"),
            TaskDistributionItem(status="Completed", count=completed_tasks, color="#10B981")
        ]

        # Stacked Bar Chart: Team / Assignee Workload
        emp_res = await db.execute(select(Employee).limit(6))
        employees = emp_res.scalars().all()
        team_workload = []
        for emp in employees:
            t_res = await db.execute(select(Task).where(Task.assigned_to_id == emp.id))
            e_tasks = t_res.scalars().all()
            c_cnt = sum(1 for t in e_tasks if t.status in ["DONE", "Resolved", "Closed", "Completed"] or (t.progress_percentage or 0) >= 100)
            p_cnt = sum(1 for t in e_tasks if t.status == "In Progress" and (t.progress_percentage or 0) < 100)
            o_cnt = sum(1 for t in e_tasks if t.is_overdue and (t.progress_percentage or 0) < 100)
            team_workload.append(
                TeamWorkloadItem(
                    team_name=f"{emp.first_name} {emp.last_name[:1]}.",
                    completed=c_cnt,
                    in_progress=p_cnt,
                    overdue=o_cnt,
                    total_tasks=len(e_tasks)
                )
            )

        # Live Upcoming / Overdue Deadlines from real tasks
        deadlines_query = select(Task).where(Task.due_date.isnot(None)).order_by(Task.due_date.asc()).limit(5)
        d_tasks = (await db.execute(deadlines_query)).scalars().all()
        deadlines = []
        for dt in d_tasks:
            p_res = await db.execute(select(Project).where(Project.id == dt.project_id))
            proj = p_res.scalars().first()
            p_name = proj.name if proj else "Project"
            days_diff = (dt.due_date - today).days

            if days_diff < 0:
                s_pill = "Overdue"
                s_type = "critical"
                d_text = f"Overdue by {abs(days_diff)}d ({dt.due_date})"
            elif days_diff == 0:
                s_pill = "Due Today"
                s_type = "critical"
                d_text = f"Due Today ({dt.due_date})"
            elif days_diff <= 2:
                s_pill = "Imminent"
                s_type = "warning"
                d_text = f"Due in {days_diff} days ({dt.due_date})"
            else:
                s_pill = "Upcoming"
                s_type = "upcoming"
                d_text = f"Due in {days_diff} days ({dt.due_date})"

            deadlines.append(
                DeadlineItem(
                    id=dt.id,
                    project_name=p_name,
                    team_name=dt.tracker,
                    deadline_text=f"{dt.title[:28]}... • {d_text}",
                    severity_pill=s_pill,
                    severity_type=s_type
                )
            )

        # Recent activities: the latest real Redmine updates (task journals), newest first
        from app.models.task import TaskJournal
        from app.services.period_analytics import time_ago as _ago
        journal_rows = (await db.execute(
            select(TaskJournal, Task, Employee)
            .join(Task, TaskJournal.task_id == Task.id)
            .outerjoin(Employee, TaskJournal.author_id == Employee.id)
            .order_by(desc(TaskJournal.created_at)).limit(5)
        )).all()
        activities = []
        for j, t, author in journal_rows:
            changes = j.changes if isinstance(j.changes, list) else []
            status_change = next((c for c in changes if isinstance(c, dict) and c.get("field") == "status"), None)
            who = f"{author.first_name} {author.last_name}".strip().title() if author else "Redmine"
            activities.append(ActivityItem(
                id=j.id,
                title=(f"Status changed: {t.title}" if status_change else f"Updated: {t.title}")[:120],
                subtitle=f"by {who}",
                time_ago=_ago(j.created_at),
                activity_type="status_updated" if status_change else "task_assigned",
            ))

        # Real Live Notifications from DB (sorted newest first)
        notif_res = await db.execute(
            select(Notification).order_by(desc(Notification.created_at)).limit(6)
        )
        db_notifs = notif_res.scalars().all()
        notifications = []
        now_utc = datetime.now(timezone.utc)
        for n in db_notifs:
            n_created = n.created_at.replace(tzinfo=timezone.utc) if n.created_at.tzinfo is None else n.created_at
            delta = now_utc - n_created
            if delta.total_seconds() < 60:
                time_ago = "Just now"
            elif delta.total_seconds() < 3600:
                time_ago = f"{int(delta.total_seconds() // 60)} min ago"
            else:
                time_ago = f"{int(delta.total_seconds() // 3600)} hour(s) ago"

            notifications.append(
                SystemNotificationBarItem(
                    id=n.id,
                    title=n.title,
                    subtitle=n.message[:65] + ("..." if len(n.message) > 65 else ""),
                    time_ago=time_ago,
                    severity=n.severity,
                    deep_link="/notifications"
                )
            )

        # Integration status
        state_res = await db.execute(select(RedmineSyncState).where(RedmineSyncState.entity_type == "ISSUES"))
        r_state = state_res.scalars().first()
        r_sync_time = r_state.last_sync_timestamp.strftime("%H:%M UTC") if r_state else "Pending"

        integrations = [
            IntegrationStatus(name="Redmine", status="Connected" if settings.REDMINE_URL else "Configured", is_healthy=True, last_synced_at=f"Synced ({r_sync_time})"),
            IntegrationStatus(
                name="Email Alerts",
                status="Configured" if email_service.is_configured() else "Not Configured",
                is_healthy=email_service.is_configured(),
                last_synced_at="Urgent and critical alerts",
            )
        ]

        return CompanyDashboardData(
            kpis=kpis,
            project_status=donut,
            task_distribution=task_dist,
            team_workload=team_workload,
            upcoming_deadlines=deadlines,
            recent_activities=activities,
            notifications=notifications,
            integrations=integrations
        )

analytics_service = AnalyticsService()
