"""
Period analytics for the dashboard date-range selector (Last 7 / 30 / 90 days / All time).

Everything here is deterministic and computed from synchronized Redmine records,
notifications and email delivery logs — no fabricated activity.
"""
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationDelivery
from app.models.task import TaskJournal
from app.services.notification_service import categorize


def as_date(dt: datetime | None) -> date | None:
    if dt is None:
        return None
    if dt.tzinfo:
        dt = dt.astimezone(timezone.utc)
    return dt.date()


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def bucket_key(d: date, granularity: str) -> date:
    if granularity == "day":
        return d
    if granularity == "week":
        return week_start(d)
    return d.replace(day=1)


def time_ago(dt: datetime) -> str:
    sec = (datetime.now(timezone.utc) - _utc(dt)).total_seconds()
    if sec < 60:
        return "just now"
    if sec < 3600:
        return f"{int(sec // 60)} min ago"
    if sec < 86400:
        return f"{int(sec // 3600)} h ago"
    return f"{int(sec // 86400)} d ago"


def _emp_name(e) -> str:
    return f"{e.first_name} {e.last_name}".strip()


async def period_block(db: AsyncSession, days: int | None, today: date, tasks, all_tasks, projects,
                       employees: dict, notes, is_open) -> dict:
    if days:
        start = today - timedelta(days=days - 1)
    else:  # all time: from the earliest record we know about
        firsts = [as_date(t.created_at) for t in all_tasks] + [as_date(n.created_at) for n in notes]
        start = min([d for d in firsts if d] or [today])
    span = (today - start).days + 1
    granularity = "day" if span <= 31 else ("week" if span <= 183 else "month")

    def in_period(d: date | None) -> bool:
        return d is not None and start <= d <= today

    task_ids = {t.id for t in tasks}
    proj_name = {p.id: p.name.strip() for p in projects}
    t_by_id = {t.id: t for t in all_tasks}

    created = [t for t in tasks if in_period(as_date(t.created_at))]
    completed = [t for t in tasks if not is_open(t) and in_period(as_date(t.updated_at))]
    p_notes = [n for n in notes if in_period(as_date(n.created_at))]
    cats = Counter(categorize(n.severity, n.title) for n in p_notes)
    deliveries = (await db.execute(
        select(NotificationDelivery).where(NotificationDelivery.channel == "EMAIL_SMTP")
    )).scalars().all()
    note_ids = {n.id for n in notes}  # email stats follow the alerts this viewer may see
    deliveries = [d for d in deliveries if d.notification_id in note_ids]
    p_del = [d for d in deliveries if in_period(as_date(d.created_at))]
    journals = [j for j in (await db.execute(select(TaskJournal))).scalars().all()
                if j.task_id in task_ids and in_period(as_date(j.created_at))]

    all_journals = [j for j in (await db.execute(select(TaskJournal))).scalars().all() if j.task_id in task_ids]

    def range_stats(lo: date, hi: date) -> dict:
        def inr(d):
            return d is not None and lo <= d <= hi
        r_notes = [n for n in notes if inr(as_date(n.created_at))]
        r_cats = Counter(categorize(n.severity, n.title) for n in r_notes)
        r_del = [d for d in deliveries if inr(as_date(d.created_at))]
        return {
            "tasks_created": sum(1 for t in tasks if inr(as_date(t.created_at))),
            "tasks_completed": sum(1 for t in tasks if not is_open(t) and inr(as_date(t.updated_at))),
            "redmine_updates": sum(1 for j in all_journals if inr(as_date(j.created_at))),
            "alerts_total": len(r_notes),
            "alerts_critical": r_cats["critical"],
            "alerts_urgent": r_cats["urgent"],
            "alerts_completed": r_cats["completed"],
            "alerts_info": r_cats["info"],
            "emails_sent": sum(1 for d in r_del if d.status == "SENT"),
            "emails_failed": sum(1 for d in r_del if d.status == "FAILED"),
            "emails_not_sent": sum(1 for d in r_del if d.status in ("NOT_CONFIGURED", "DISABLED")),
        }

    stats = range_stats(start, today)
    # Same-length window immediately before the selected period (for "vs previous period" deltas)
    prev_stats = range_stats(start - timedelta(days=span), start - timedelta(days=1)) if days else None

    # ── timeline buckets ─────────────────────────────────────────────── #
    buckets: list[date] = []
    cur = bucket_key(start, granularity)
    while cur <= today:
        buckets.append(cur)
        if granularity == "day":
            cur += timedelta(days=1)
        elif granularity == "week":
            cur += timedelta(weeks=1)
        else:
            cur = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
    tl: dict[date, Counter] = {b: Counter() for b in buckets}

    def bump(d: date, key: str):
        tl.setdefault(bucket_key(d, granularity), Counter())[key] += 1

    for t in created:
        bump(as_date(t.created_at), "created")
    for t in completed:
        bump(as_date(t.updated_at), "completed")
    for j in journals:
        bump(as_date(j.created_at), "updates")
    for n in p_notes:
        bump(as_date(n.created_at), "alerts")
        bump(as_date(n.created_at), f"cat_{categorize(n.severity, n.title)}")
    timeline = [{
        "bucket": b.isoformat(), "created": c["created"], "completed": c["completed"], "updates": c["updates"],
        "alerts": c["alerts"], "critical": c["cat_critical"], "urgent": c["cat_urgent"],
        "completed_alerts": c["cat_completed"], "info": c["cat_info"],
    } for b, c in sorted(tl.items())]

    # ── real activity feed, newest first ─────────────────────────────── #
    events = []
    for j in journals:
        t = t_by_id.get(j.task_id)
        author = employees.get(j.author_id)
        changes = j.changes if isinstance(j.changes, list) else []
        what = ", ".join(f"{c.get('field') or c.get('name')} → {c.get('new_value')}"
                         for c in changes[:2] if isinstance(c, dict))
        events.append({
            "type": "redmine_update", "at": j.created_at,
            "title": f"{_emp_name(author) if author else 'Someone'} updated {t.title if t else 'a task'}",
            "subtitle": ((j.notes or "").strip() or what or "Issue updated in Redmine")[:140],
            "project": proj_name.get(t.project_id) if t else None,
        })
    for t in created:
        events.append({"type": "task_created", "at": t.created_at, "title": f"New task: {t.title}",
                       "subtitle": f"Priority {t.priority}" + (f" · due {t.due_date}" if t.due_date else ""),
                       "project": proj_name.get(t.project_id)})
    for t in completed:
        events.append({"type": "task_completed", "at": t.updated_at, "title": f"Completed: {t.title}",
                       "subtitle": f"Status {t.status}", "project": proj_name.get(t.project_id)})
    for n in p_notes:
        events.append({"type": f"alert_{categorize(n.severity, n.title)}", "at": n.created_at,
                       "title": n.title, "subtitle": n.message[:140], "project": None})
    events = [e for e in events if e["at"]]
    events.sort(key=lambda e: _utc(e["at"]), reverse=True)
    activity = [{**e, "at": _utc(e["at"]).strftime("%Y-%m-%d %H:%M UTC"), "ago": time_ago(e["at"])}
                for e in events[:25]]

    # ── deadlines: overdue + due within 14 days (current state) ──────── #
    horizon = today + timedelta(days=14)
    dl = sorted((t for t in tasks if is_open(t) and t.due_date and t.due_date <= horizon), key=lambda t: t.due_date)
    deadlines = [{
        "id": t.id, "title": t.title, "project": proj_name.get(t.project_id),
        "due_date": t.due_date.isoformat(), "days_left": (t.due_date - today).days,
        "assignee": _emp_name(employees[t.assigned_to_id]) if t.assigned_to_id in employees else None,
        "priority": t.priority,
    } for t in dl[:10]]

    return {
        "meta": {"days": days, "start": start.isoformat(), "end": today.isoformat(), "granularity": granularity,
                 "label": f"Last {days} days" if days else "All time"},
        "stats": stats, "prev_stats": prev_stats, "timeline": timeline, "activity": activity, "deadlines": deadlines,
        "people": await people_block(db, start, today, tasks, employees, all_journals, is_open, granularity),
    }


# ---------------------------------------------------------------------- #
#  People: availability today + contribution ranking for the period       #
# ---------------------------------------------------------------------- #
AVAILABILITY = [  # (label, min_open, max_open)
    ("Free", 0, 0),
    ("Light", 1, 2),
    ("Busy", 3, 5),
    ("Overloaded", 6, None),
]
SCORE_WEIGHTS = {"completed": 5, "updates": 2, "open_on_time": 1}


def _availability(open_tasks: int) -> str:
    for label, lo, hi in AVAILABILITY:
        if open_tasks >= lo and (hi is None or open_tasks <= hi):
            return label
    return "Overloaded"


async def people_block(db: AsyncSession, start: date, today: date, tasks, employees: dict, journals,
                       is_open, granularity: str) -> dict:
    """
    Only real Redmine users are ranked (platform login accounts without a Redmine
    user mapping are excluded). Score = 5×tasks completed + 2×Redmine updates
    authored + 1×open tasks still on time (overdue work is shown, not rewarded).
    """
    from app.models.redmine_sync import RedmineMapping

    redmine_users = {m.internal_id for m in (await db.execute(
        select(RedmineMapping).where(RedmineMapping.entity_type == "USER"))).scalars().all()}
    people_ids = [eid for eid in employees if eid in redmine_users and employees[eid].status == "ACTIVE"]

    # weekly activity trend (last 8 weeks) — independent of the selected period so growth is comparable
    weeks = [week_start(today) - timedelta(weeks=i) for i in range(7, -1, -1)]

    def in_period(d):
        return d is not None and start <= d <= today

    rows = []
    for eid in people_ids:
        e = employees[eid]
        mine = [t for t in tasks if t.assigned_to_id == eid]
        open_t = [t for t in mine if is_open(t)]
        overdue = [t for t in open_t if t.due_date and t.due_date < today]
        done_p = [t for t in mine if not is_open(t) and in_period(as_date(t.updated_at))]
        upd = [j for j in journals if j.author_id == eid]
        upd_p = [j for j in upd if in_period(as_date(j.created_at))]
        trend = Counter()
        for j in upd:
            d = as_date(j.created_at)
            if d:
                trend[week_start(d)] += 1
        for t in mine:
            if not is_open(t):
                d = as_date(t.updated_at)
                if d:
                    trend[week_start(d)] += 1
        on_time = len(open_t) - len(overdue)
        score = (SCORE_WEIGHTS["completed"] * len(done_p) + SCORE_WEIGHTS["updates"] * len(upd_p)
                 + SCORE_WEIGHTS["open_on_time"] * on_time)
        rows.append({
            "employee_id": eid,
            "name": _emp_name(e),
            "job_title": e.job_title,
            "open_tasks": len(open_t),
            "open_on_time": on_time,
            "overdue": len(overdue),
            "max_days_overdue": max(((today - t.due_date).days for t in overdue), default=0),
            "completed_in_period": len(done_p),
            "updates_in_period": len(upd_p),
            "completed_all_time": sum(1 for t in mine if not is_open(t)),
            "estimated_hours_open": round(sum(float(t.estimated_hours or 0) for t in open_t), 1),
            "availability": _availability(len(open_t)),
            "score": score,
            "weekly_activity": [{"week": w.isoformat(), "count": trend.get(w, 0)} for w in weeks],
        })
    rows.sort(key=lambda r: (-r["score"], -r["completed_in_period"], -r["open_tasks"], r["overdue"], r["name"].lower()))
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    counts = Counter(r["availability"] for r in rows)
    return {
        "employees": rows,
        "availability_counts": [{"label": lbl, "count": counts.get(lbl, 0),
                                 "range": f"{lo}" if lo == hi else (f"{lo}+" if hi is None else f"{lo}–{hi}")}
                                for lbl, lo, hi in AVAILABILITY],
        "free_today": [r["name"] for r in rows if r["availability"] == "Free"],
        "score_formula": "5 × tasks completed + 2 × Redmine updates + 1 × open tasks on time (selected period)",
    }
