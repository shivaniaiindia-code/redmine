"""
Reports & Analytics — every figure is computed deterministically from the
synchronized Redmine data in the database (Dual-Intelligence Principle).
"""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import CurrentUser
from app.core.scope import Scope
from app.models.employee import Employee
from app.models.notification import Notification
from app.models.project import Project, ProjectMember
from app.models.task import Task
from app.services.notification_service import categorize
from app.services.period_analytics import period_block

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])

COMPLETED = {"DONE", "Resolved", "Closed", "Completed"}
AGING_BUCKETS = [("1–7 days", 1, 7), ("8–14 days", 8, 14), ("15–30 days", 15, 30), ("31+ days", 31, None)]
PRIORITY_ORDER = ["Immediate", "Urgent", "High", "Normal", "Low"]


def _as_date(dt: datetime | None) -> date | None:
    if dt is None:
        return None
    if dt.tzinfo:
        dt = dt.astimezone(timezone.utc)
    return dt.date()


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


@router.get("/overview")
async def reports_overview(
    current_user: CurrentUser,
    scope: Scope,
    db: AsyncSession = Depends(get_db),
    weeks: int = Query(12, ge=4, le=52, description="Weeks of history for trend charts"),
    include_inactive: bool = Query(False, description="Include INACTIVE (archived) Redmine projects"),
    days: int | None = Query(None, ge=1, le=3650, description="Reporting period in days (omit = all time)"),
):
    today = date.today()
    projects = scope.filter_projects((await db.execute(select(Project).order_by(Project.name))).scalars().all())
    if not include_inactive:
        projects = [p for p in projects if p.status != "INACTIVE"]
    project_ids = {p.id for p in projects}
    all_tasks = scope.filter_tasks((await db.execute(select(Task))).scalars().all())
    tasks = [t for t in all_tasks if t.project_id in project_ids]
    employees = {e.id: e for e in (await db.execute(select(Employee))).scalars().all() if scope.can_see_employee(e.id)}
    members = [m for m in (await db.execute(select(ProjectMember))).scalars().all() if m.project_id in project_ids]

    def is_open(t: Task) -> bool:
        return t.status not in COMPLETED

    def overdue_days(t: Task) -> int:
        return (today - t.due_date).days if (is_open(t) and t.due_date and t.due_date < today) else 0

    open_tasks = [t for t in tasks if is_open(t)]
    overdue = [t for t in open_tasks if overdue_days(t) > 0]
    blocked = [t for t in open_tasks if t.is_blocked]
    completed = [t for t in tasks if not is_open(t)]

    # ── KPIs ─────────────────────────────────────────────────────────── #
    kpis = {
        "projects": len(projects),
        "active_projects": sum(1 for p in projects if p.status == "ACTIVE"),
        "at_risk_projects": sum(1 for p in projects if p.health_status in ("AT_RISK", "BLOCKED", "OFF_TRACK")),
        "total_tasks": len(tasks),
        "open_tasks": len(open_tasks),
        "overdue_tasks": len(overdue),
        "blocked_tasks": len(blocked),
        "completed_tasks": len(completed),
        "unassigned_open_tasks": sum(1 for t in open_tasks if not t.assigned_to_id),
        "completion_rate": round(100 * len(completed) / len(tasks), 1) if tasks else 0.0,
        "overdue_rate": round(100 * len(overdue) / len(open_tasks), 1) if open_tasks else 0.0,
        "avg_days_overdue": round(sum(overdue_days(t) for t in overdue) / len(overdue), 1) if overdue else 0.0,
        "estimated_hours_open": round(sum(float(t.estimated_hours or 0) for t in open_tasks), 1),
        "spent_hours": round(sum(float(t.spent_hours or 0) for t in tasks), 1),
    }

    # ── Per-project breakdown ────────────────────────────────────────── #
    by_project = defaultdict(list)
    for t in tasks:
        by_project[t.project_id].append(t)
    team_size = Counter(m.project_id for m in {(m.project_id, m.employee_id): m for m in members}.values())
    project_rows = []
    for p in projects:
        pt = by_project.get(p.id, [])
        p_open = [t for t in pt if is_open(t)]
        p_over = [t for t in p_open if overdue_days(t) > 0]
        project_rows.append({
            "id": p.id,
            "name": p.name.strip(),
            "code": p.code,
            "status": p.status,
            "health_status": p.health_status,
            "health_reason": p.health_reason,
            "progress_percentage": float(p.progress_percentage or 0),
            "total_tasks": len(pt),
            "completed_tasks": len(pt) - len(p_open),
            "open_on_time": len(p_open) - len(p_over),
            "overdue_tasks": len(p_over),
            "blocked_tasks": sum(1 for t in p_open if t.is_blocked),
            "unassigned_open_tasks": sum(1 for t in p_open if not t.assigned_to_id),
            "max_days_overdue": max((overdue_days(t) for t in p_over), default=0),
            "team_size": team_size.get(p.id, 0),
            "estimated_hours": round(sum(float(t.estimated_hours or 0) for t in pt), 1),
            "spent_hours": round(sum(float(t.spent_hours or 0) for t in pt), 1),
        })

    # ── Distributions ────────────────────────────────────────────────── #
    status_counts = Counter(t.status for t in tasks)
    task_status = [{"status": s, "count": c} for s, c in status_counts.most_common()]

    prio_counts = Counter((t.priority or "Normal") for t in open_tasks)
    priorities = [{"priority": p, "count": prio_counts.get(p, 0)} for p in PRIORITY_ORDER]
    priorities += [{"priority": p, "count": c} for p, c in prio_counts.items() if p not in PRIORITY_ORDER]

    aging = []
    for label, lo, hi in AGING_BUCKETS:
        aging.append({"bucket": label, "count": sum(1 for t in overdue
                                                     if overdue_days(t) >= lo and (hi is None or overdue_days(t) <= hi))})

    health_counts = Counter(p.health_status for p in projects)
    health = [{"health": h, "count": health_counts.get(h, 0)} for h in ("ON_TRACK", "AT_RISK", "BLOCKED", "OFF_TRACK")
              if health_counts.get(h, 0) or h in ("ON_TRACK", "AT_RISK", "BLOCKED")]

    # ── Workload by employee (open work) ─────────────────────────────── #
    emp_projects = defaultdict(set)
    for m in members:
        emp_projects[m.employee_id].add(m.project_id)
    workload = []
    emp_ids = {t.assigned_to_id for t in open_tasks if t.assigned_to_id} | set(emp_projects)
    for eid in emp_ids:
        e = employees.get(eid)
        if not e:
            continue
        et = [t for t in open_tasks if t.assigned_to_id == eid]
        e_over = sum(1 for t in et if overdue_days(t) > 0)
        workload.append({
            "employee_id": eid,
            "name": f"{e.first_name} {e.last_name}".strip(),
            "open_on_time": len(et) - e_over,
            "overdue": e_over,
            "open_tasks": len(et),
            "projects": len(emp_projects.get(eid, set()) | {t.project_id for t in et}),
            "estimated_hours": round(sum(float(t.estimated_hours or 0) for t in et), 1),
        })
    workload.sort(key=lambda w: (-w["open_tasks"], -w["projects"], w["name"].lower()))

    # ── Weekly trend: created vs completed ───────────────────────────── #
    first_week = _week_start(today) - timedelta(weeks=weeks - 1)
    created_w, completed_w = Counter(), Counter()
    for t in tasks:
        c = _as_date(t.created_at)
        if c and c >= first_week:
            created_w[_week_start(c)] += 1
        if not is_open(t):
            u = _as_date(t.updated_at)
            if u and u >= first_week:
                completed_w[_week_start(u)] += 1
    trend = []
    for i in range(weeks):
        wk = first_week + timedelta(weeks=i)
        trend.append({"week": wk.isoformat(), "created": created_w.get(wk, 0), "completed": completed_w.get(wk, 0)})

    # ── Alerts by category per day (last 14 days) ────────────────────── #
    since = datetime.now(timezone.utc) - timedelta(days=13)
    task_project = {t.id: t.project_id for t in all_tasks}
    notes = [n for n in (await db.execute(select(Notification))).scalars().all()
             if scope.can_see_notification(n, task_project)]
    per_day = defaultdict(Counter)
    for n in notes:
        d = _as_date(n.created_at)
        if d and d >= since.date():
            per_day[d][categorize(n.severity, n.title)] += 1
    alerts_daily = []
    for i in range(14):
        d = since.date() + timedelta(days=i)
        c = per_day.get(d, Counter())
        alerts_daily.append({"date": d.isoformat(), "critical": c["critical"], "urgent": c["urgent"],
                             "completed": c["completed"], "info": c["info"]})

    # ── Top overdue tasks ────────────────────────────────────────────── #
    proj_name = {p.id: p.name.strip() for p in projects}
    top_overdue = [{
        "id": t.id, "title": t.title, "project": proj_name.get(t.project_id),
        "assignee": (f"{employees[t.assigned_to_id].first_name} {employees[t.assigned_to_id].last_name}".strip()
                     if t.assigned_to_id in employees else None),
        "priority": t.priority, "due_date": t.due_date.isoformat() if t.due_date else None,
        "days_overdue": overdue_days(t), "status": t.status,
    } for t in sorted(overdue, key=overdue_days, reverse=True)[:10]]

    period = await period_block(db, days, today, tasks, all_tasks, projects, employees, notes, is_open)

    return {
        "period": period["meta"],
        "period_stats": period["stats"],
        "timeline": period["timeline"],
        "activity": period["activity"],
        "upcoming_deadlines": period["deadlines"],
        "prev_period_stats": period["prev_stats"],
        "people": period["people"],
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "as_of": today.isoformat(),
        "scope": "all projects" if include_inactive else "active projects (INACTIVE excluded)",
        "visibility": "company" if scope.is_global else "assigned_projects",
        "kpis": kpis,
        "projects": project_rows,
        "task_status": task_status,
        "priorities": priorities,
        "overdue_aging": aging,
        "project_health": health,
        "workload": workload,
        "weekly_trend": trend,
        "alerts_daily": alerts_daily,
        "top_overdue": top_overdue,
    }
