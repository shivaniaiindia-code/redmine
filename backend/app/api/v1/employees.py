from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.permissions import CurrentUser
from app.core.scope import Scope
from app.models.employee import Employee
from app.models.task import Task
from app.models.project import Project, ProjectMember
from app.models.user import User


async def _unapproved_employee_ids(db: AsyncSession) -> set[str]:
    """Employee records of sign-ups that are still pending or were declined."""
    rows = (await db.execute(select(Employee.id).join(User, User.id == Employee.user_id)
                             .where(User.approval_status != "APPROVED"))).scalars().all()
    return set(rows)

router = APIRouter(prefix="/employees", tags=["Employees"])

@router.get("/")
async def list_employees(
    current_user: CurrentUser,
    scope: Scope,
    db: AsyncSession = Depends(get_db)
):
    e_res = await db.execute(select(Employee).order_by(Employee.first_name))
    hidden = await _unapproved_employee_ids(db)
    employees = [e for e in e_res.scalars().all() if scope.can_see_employee(e.id) and e.id not in hidden]

    # Batch prefetch to eliminate 60+ sequential queries (only work on visible projects)
    all_tasks = scope.filter_tasks((await db.execute(select(Task))).scalars().all())
    emp_tasks_map = defaultdict(list)
    for t in all_tasks:
        if t.assigned_to_id:
            emp_tasks_map[t.assigned_to_id].append(t)

    all_pm_rows = (await db.execute(
        select(ProjectMember, Project)
        .join(Project, ProjectMember.project_id == Project.id)
        .where(Project.status != "INACTIVE")
    )).all()
    emp_pms_map = defaultdict(list)
    for pm, proj in all_pm_rows:
        if scope.can_see_project(proj.id):
            emp_pms_map[pm.employee_id].append((pm, proj))

    all_active_projects = {p.id: p for p in scope.filter_projects(
        (await db.execute(select(Project).where(Project.status != "INACTIVE"))).scalars().all())}

    response = []
    for emp in employees:
        emp_tasks = emp_tasks_map.get(emp.id, [])

        total_tasks = len(emp_tasks)
        overdue_tasks = sum(1 for t in emp_tasks if t.is_overdue and (t.progress_percentage or 0) < 100)
        completed_tasks = sum(1 for t in emp_tasks if t.status in ["DONE", "Resolved", "Closed", "Completed"] or (t.progress_percentage or 0) >= 100)

        pm_rows = emp_pms_map.get(emp.id, [])

        current_projects = []
        seen_pids = set()
        allocated_hours = 0.0

        for pm, proj in pm_rows:
            if proj.id not in seen_pids:
                seen_pids.add(proj.id)
                current_projects.append({
                    "id": proj.id,
                    "name": proj.name,
                    "code": proj.code,
                    "role": pm.role_in_project or "Contributor"
                })
                allocated_hours += float(pm.allocated_hours_per_week or 0.0)

        # Also inspect assigned tasks to include active projects from tasks if not already present
        for t in emp_tasks:
            if t.project_id and t.project_id not in seen_pids:
                proj = all_active_projects.get(t.project_id)
                if proj:
                    seen_pids.add(proj.id)
                    current_projects.append({
                        "id": proj.id,
                        "name": proj.name,
                        "code": proj.code,
                        "role": "Task Assignee"
                    })

        capacity = float(emp.weekly_capacity_hours or 40.0)
        active_tasks = [t for t in emp_tasks if t.status not in ["DONE", "Resolved", "Closed"]]

        if allocated_hours <= 0.0:
            task_hours = sum(float(t.estimated_hours or 0.0) for t in active_tasks)
            if task_hours > 0.0:
                allocated_hours = task_hours
            elif current_projects:
                allocated_hours = min(float(len(current_projects) * 20.0), capacity)
            elif active_tasks:
                allocated_hours = min(float(len(active_tasks) * 8.0), capacity)

        num_projects = len(current_projects)
        if num_projects == 0 and allocated_hours == 0.0:
            workload_score = 0.0
        else:
            context_mult = 1.0 + 0.15 * max(0, num_projects - 1)
            workload_score = (allocated_hours / capacity) * context_mult

        response.append({
            "id": emp.id,
            "name": f"{emp.first_name} {emp.last_name}".strip(),
            "email": emp.email,
            "job_title": emp.job_title,
            "department": emp.department,
            "status": emp.status,
            "weekly_capacity_hours": capacity,
            "total_tasks": total_tasks,
            "overdue_tasks": overdue_tasks,
            "completed_tasks": completed_tasks,
            "current_projects": current_projects,
            "allocated_hours": round(allocated_hours, 1),
            "workload_score": round(workload_score, 2)
        })

    return response



# ---------------------------------------------------------------------- #
#  Employee profile (360 view) — computed from synced Redmine records      #
# ---------------------------------------------------------------------- #
@router.get("/{employee_id}/profile")
async def employee_profile(employee_id: str, current_user: CurrentUser, scope: Scope,
                           db: AsyncSession = Depends(get_db)):
    from collections import Counter
    from datetime import date, timedelta
    from fastapi import HTTPException
    from app.models.task import TaskJournal
    from app.api.v1.reports import reports_overview
    from app.services.period_analytics import as_date, week_start

    emp = await db.get(Employee, employee_id)
    if emp is None or not scope.can_see_employee(emp.id) or emp.id in await _unapproved_employee_ids(db):
        raise HTTPException(status_code=404, detail="Employee not found.")

    done_statuses = {"DONE", "Resolved", "Closed", "Completed"}
    today = date.today()
    projects = {p.id: p for p in scope.filter_projects((await db.execute(select(Project))).scalars().all())}
    mine = scope.filter_tasks((await db.execute(select(Task).where(Task.assigned_to_id == emp.id))).scalars().all())
    tasks_by_id = {t.id: t for t in scope.filter_tasks((await db.execute(select(Task))).scalars().all())}
    journals = [j for j in (await db.execute(select(TaskJournal).where(TaskJournal.author_id == emp.id)
                                             .order_by(TaskJournal.created_at.desc()))).scalars().all()
                if j.task_id in tasks_by_id]

    def is_open(t):
        return t.status not in done_statuses

    def pname(pid):
        p = projects.get(pid)
        return p.name.strip() if p else None

    open_t = [t for t in mine if is_open(t)]
    done_t = [t for t in mine if not is_open(t)]
    overdue_t = [t for t in open_t if t.due_date and t.due_date < today]
    with_due = [t for t in done_t if t.due_date and as_date(t.updated_at)]
    on_time = [t for t in with_due if as_date(t.updated_at) <= t.due_date]
    cycle_days = [(as_date(t.updated_at) - as_date(t.created_at)).days for t in done_t
                  if as_date(t.updated_at) and as_date(t.created_at)]
    last_30 = today - timedelta(days=29)

    # Growth: weekly score (5 x completed + 2 x updates) for 12 weeks, monthly counts for 12 months
    weeks = [week_start(today) - timedelta(weeks=i) for i in range(11, -1, -1)]
    wk_done = Counter(week_start(as_date(t.updated_at)) for t in done_t if as_date(t.updated_at))
    wk_upd = Counter(week_start(as_date(j.created_at)) for j in journals if as_date(j.created_at))
    weekly = [{"week": w.isoformat(), "completed": wk_done.get(w, 0), "updates": wk_upd.get(w, 0),
               "score": 5 * wk_done.get(w, 0) + 2 * wk_upd.get(w, 0)} for w in weeks]
    months = []
    m = today.replace(day=1)
    for _ in range(12):
        months.append(m)
        m = (m - timedelta(days=1)).replace(day=1)
    months.reverse()
    mo_done = Counter(as_date(t.updated_at).replace(day=1) for t in done_t if as_date(t.updated_at))
    mo_upd = Counter(as_date(j.created_at).replace(day=1) for j in journals if as_date(j.created_at))
    monthly = [{"month": mm.isoformat(), "completed": mo_done.get(mm, 0), "updates": mo_upd.get(mm, 0)}
               for mm in months]

    # Ranking among Redmine users (same formula as the dashboard), last 30 days
    report = await reports_overview(current_user=current_user, scope=scope, db=db, weeks=8,
                                    include_inactive=False, days=30)
    ranked = report["people"]["employees"]
    me = next((r for r in ranked if r["employee_id"] == emp.id), None)

    # Projects worked on (current + historical, preserved from task history)
    def blank_project(pid):
        p = projects.get(pid)
        return {"id": pid, "name": pname(pid), "status": p.status if p else None, "total": 0, "completed": 0,
                "open": 0, "overdue": 0, "last_activity": None, "is_manager": bool(p and p.project_manager_id == emp.id)}

    per_project: dict[str, dict] = {}
    for t in mine:
        row = per_project.setdefault(t.project_id, blank_project(t.project_id))
        row["total"] += 1
        row["open" if is_open(t) else "completed"] += 1
        row["overdue"] += int(t in overdue_t)
        d = as_date(t.updated_at)
        if d and (row["last_activity"] is None or d.isoformat() > row["last_activity"]):
            row["last_activity"] = d.isoformat()
    for p in projects.values():
        if p.project_manager_id == emp.id:
            per_project.setdefault(p.id, blank_project(p.id))

    def task_row(t):
        due = t.due_date
        done_on = as_date(t.updated_at) if not is_open(t) else None
        return {"id": t.id, "title": t.title, "project": pname(t.project_id), "status": t.status,
                "priority": t.priority, "due_date": due.isoformat() if due else None,
                "days_overdue": (today - due).days if (due and is_open(t) and due < today) else 0,
                "days_left": (due - today).days if (due and is_open(t) and due >= today) else None,
                "is_blocked": t.is_blocked, "completed_on": done_on.isoformat() if done_on else None}

    activity = []
    for j in journals[:15]:
        t = tasks_by_id.get(j.task_id)
        changes = j.changes if isinstance(j.changes, list) else []
        activity.append({
            "date": j.created_at.isoformat() if j.created_at else None,
            "task": t.title if t else "Task",
            "project": pname(t.project_id) if t else None,
            "note": (j.notes or "").strip()[:240] or None,
            "changes": [f"{c.get('field')}: {c.get('old_value') or '-'} -> {c.get('new_value') or '-'}"
                        for c in changes if isinstance(c, dict)][:3],
        })

    def in_last_30(d):
        return d is not None and d >= last_30

    return {
        "employee": {"id": emp.id, "name": f"{emp.first_name} {emp.last_name}".strip().title(), "email": emp.email,
                     "job_title": emp.job_title, "department": emp.department, "status": emp.status,
                     "hire_date": emp.hire_date.isoformat() if emp.hire_date else None,
                     "weekly_capacity_hours": float(emp.weekly_capacity_hours or 40)},
        "stats": {
            "open_tasks": len(open_t),
            "overdue_tasks": len(overdue_t),
            "blocked_tasks": sum(1 for t in open_t if t.is_blocked),
            "completed_all_time": len(done_t),
            "completed_last_30_days": sum(1 for t in done_t if in_last_30(as_date(t.updated_at))),
            "updates_last_30_days": sum(1 for j in journals if in_last_30(as_date(j.created_at))),
            "on_time_rate": round(100 * len(on_time) / len(with_due)) if with_due else None,
            "avg_cycle_days": round(sum(cycle_days) / len(cycle_days), 1) if cycle_days else None,
            "estimated_hours_open": round(sum(float(t.estimated_hours or 0) for t in open_t), 1),
            "spent_hours_total": round(sum(float(t.spent_hours or 0) for t in mine), 1),
            "projects_count": len(per_project),
        },
        "ranking": None if me is None else {
            "rank": me["rank"], "of": len(ranked), "score": me["score"], "availability": me["availability"],
            "period": "last 30 days", "formula": report["people"]["score_formula"],
        },
        "weekly": weekly,
        "monthly": monthly,
        "open_tasks": [task_row(t) for t in sorted(open_t, key=lambda t: (t.due_date or date.max))],
        "completed_tasks": [task_row(t) for t in sorted(done_t, key=lambda t: t.updated_at or t.created_at,
                                                         reverse=True)[:15]],
        "projects": sorted(per_project.values(), key=lambda r: (-r["open"], -r["total"], r["name"] or "")),
        "activity": activity,
        "as_of": today.isoformat(),
    }
