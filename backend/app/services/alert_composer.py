"""
Alert email composer.

When a notification is raised, this service turns it into a structured,
professional email:

  * FACTS (deterministic) — the alert plus the live records behind it (task,
    project, assignee, recent Redmine journal notes, project-level counts) are
    read from the database. The "Key details" table in the email is filled
    from these facts directly, so dates, counts and names are always exact.
  * NARRATIVE (LLM) — OpenRouter writes the headline, summary, context, impact
    and recommended next steps from those facts only.
  * FALLBACK (template) — if the LLM is disabled, slow, or returns anything
    malformed, a deterministic narrative is used. An alert email is never lost
    because of the LLM.
"""
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.employee import Employee
from app.models.notification import Notification
from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskJournal

COMPLETED = {"DONE", "Resolved", "Closed", "Completed"}


@dataclass
class AlertEmailContent:
    subject: str
    severity: str
    category: str
    entity_type: str
    headline: str
    summary: str
    details: list[tuple[str, str]] = field(default_factory=list)   # deterministic facts table
    context: list[str] = field(default_factory=list)
    impact: str = ""
    actions: list[str] = field(default_factory=list)
    raised_at: str = ""
    source: str = "template"                                      # "llm" | "template"


def _name(e: Employee | None) -> str | None:
    return f"{e.first_name} {e.last_name}".strip() if e else None


def _fmt_date(d) -> str | None:
    return d.isoformat() if d else None


class AlertComposer:
    # ------------------------------------------------------------------ #
    #  Facts                                                               #
    # ------------------------------------------------------------------ #
    async def gather_facts(self, db: AsyncSession, n: Notification) -> dict:
        today = date.today()
        facts: dict = {
            "alert": {
                "title": n.title,
                "message": n.message,
                "severity": n.severity,
                "entity_type": n.entity_type,
                "raised_at": (n.created_at or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M UTC"),
            },
            "today": today.isoformat(),
        }
        project: Project | None = None

        if n.entity_type == "TASK" and n.entity_id:
            t = (await db.execute(select(Task).where(Task.id == n.entity_id))).scalars().first()
            if t:
                project = (await db.execute(select(Project).where(Project.id == t.project_id))).scalars().first()
                assignee = (await db.execute(select(Employee).where(Employee.id == t.assigned_to_id))).scalars().first() \
                    if t.assigned_to_id else None
                overdue_days = (today - t.due_date).days if (t.due_date and t.due_date < today and t.status not in COMPLETED) else 0
                notes = (await db.execute(
                    select(TaskJournal).where(TaskJournal.task_id == t.id, TaskJournal.notes.isnot(None))
                    .order_by(TaskJournal.created_at.desc()).limit(3)
                )).scalars().all()
                facts["task"] = {
                    "title": t.title,
                    "status": t.status,
                    "priority": t.priority,
                    "tracker": t.tracker,
                    "assignee": _name(assignee),
                    "start_date": _fmt_date(t.start_date),
                    "due_date": _fmt_date(t.due_date),
                    "days_overdue": overdue_days,
                    "progress_percentage": int(t.progress_percentage or 0),
                    "estimated_hours": float(t.estimated_hours or 0),
                    "spent_hours": float(t.spent_hours or 0),
                    "is_blocked": bool(t.is_blocked),
                    "blocker_reason": t.blocker_reason,
                    "created_in_redmine": t.created_at.strftime("%Y-%m-%d") if t.created_at else None,
                    "last_updated_in_redmine": t.updated_at.strftime("%Y-%m-%d") if t.updated_at else None,
                    "recent_redmine_notes": [j.notes.strip()[:300] for j in notes if j.notes and j.notes.strip()],
                }
        elif n.entity_type == "PROJECT" and n.entity_id:
            project = (await db.execute(select(Project).where(Project.id == n.entity_id))).scalars().first()

        if project:
            p_tasks = (await db.execute(select(Task).where(Task.project_id == project.id))).scalars().all()
            open_t = [t for t in p_tasks if t.status not in COMPLETED]
            members = (await db.execute(
                select(Employee, ProjectMember.role_in_project)
                .join(ProjectMember, ProjectMember.employee_id == Employee.id)
                .where(ProjectMember.project_id == project.id)
            )).all()
            pm = (await db.execute(select(Employee).where(Employee.id == project.project_manager_id))).scalars().first() \
                if project.project_manager_id else None
            facts["project"] = {
                "name": project.name.strip(),
                "code": project.code,
                "status": project.status,
                "health_status": project.health_status,
                "health_reason": project.health_reason,
                "progress_percentage": float(project.progress_percentage or 0),
                "project_manager": _name(pm),
                "target_completion_date": _fmt_date(project.target_completion_date),
                "total_tasks": len(p_tasks),
                "open_tasks": len(open_t),
                "overdue_tasks": sum(1 for t in open_t if t.due_date and t.due_date < today),
                "blocked_tasks": sum(1 for t in open_t if t.is_blocked),
                "unassigned_open_tasks": sum(1 for t in open_t if not t.assigned_to_id),
                "team": [f"{_name(e)} ({role})" for e, role in members],
            }
        return facts

    # ------------------------------------------------------------------ #
    #  Deterministic parts                                                 #
    # ------------------------------------------------------------------ #
    @staticmethod
    def details_table(facts: dict) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        t, p = facts.get("task"), facts.get("project")
        if t:
            rows.append(("Task", t["title"]))
            rows.append(("Status / priority", f'{t["status"]} · {t["priority"]}'))
            rows.append(("Assignee", t["assignee"] or "Unassigned"))
            if t["due_date"]:
                late = f' ({t["days_overdue"]} day(s) overdue)' if t["days_overdue"] else ""
                rows.append(("Due date", f'{t["due_date"]}{late}'))
            if t["is_blocked"]:
                rows.append(("Blocker", t["blocker_reason"] or "Blocked"))
            rows.append(("Progress", f'{t["progress_percentage"]}%'))
        if p:
            rows.append(("Project", f'{p["name"]} ({p["code"]})'))
            rows.append(("Project health", p["health_status"] + (f' — {p["health_reason"]}' if p["health_reason"] else "")))
            rows.append(("Project workload", f'{p["open_tasks"]} open · {p["overdue_tasks"]} overdue · {p["blocked_tasks"]} blocked'))
            if p["team"]:
                rows.append(("Team", ", ".join(p["team"][:8])))
        rows.append(("Raised", facts["alert"]["raised_at"]))
        return rows

    @staticmethod
    def template_narrative(facts: dict) -> dict:
        a, t, p = facts["alert"], facts.get("task"), facts.get("project")
        title = a["title"]
        context, actions = [], []
        if title.startswith("Overdue Task") and t:
            headline = f'"{t["title"]}" is {t["days_overdue"]} day(s) past its due date'
            summary = (f'This Redmine issue was due on {t["due_date"]} and is still "{t["status"]}". '
                       + (f'It is assigned to {t["assignee"]}.' if t["assignee"] else "It has no assignee."))
            impact = ("Overdue work delays the project timeline and may push dependent tasks back."
                      + (f' The project currently has {p["overdue_tasks"]} overdue task(s).' if p else ""))
            actions = ["Confirm the real status with the assignee and update the issue in Redmine.",
                       "Agree a new realistic due date, or re-scope the task."]
            if t and not t["assignee"]:
                actions.insert(0, "Assign an owner — nobody is currently responsible for this task.")
        elif title.startswith("Blocker Alert") and t:
            headline = f'"{t["title"]}" is blocked'
            summary = f'Progress on this task has stopped: {t["blocker_reason"] or "a dependency is blocking it"}.'
            impact = "Blocked work cannot progress until the blocker is removed."
            actions = ["Identify who can remove the blocker and contact them today.", "Record the resolution in Redmine."]
        elif title.startswith("Priority Escalation") and t:
            headline = f'High-priority issue open: "{t["title"]}"'
            summary = f'This issue is marked "{t["priority"]}" in Redmine and is still "{t["status"]}".'
            impact = "Issues at this priority usually need attention within the day."
            actions = ["Confirm someone is actively working on it.", "Share an ETA with stakeholders."]
        elif title.startswith("Deadline Warning") and t:
            headline = f'"{t["title"]}" is due on {t["due_date"]}'
            summary = f'The deadline is close and the task is "{t["status"]}" at {t["progress_percentage"]}% progress.'
            impact = "Acting now avoids the task becoming overdue."
            actions = ["Check with the assignee that the deadline is still achievable."]
        elif title.startswith("Task Completed") and t:
            headline = f'"{t["title"]}" has been completed'
            summary = f'The issue was closed in Redmine (status "{t["status"]}").'
            impact = "No action is required; this is for your information."
        elif title.startswith("Project Health Alert") and p:
            headline = f'{p["name"]} is now {p["health_status"]}'
            summary = f'{p["health_reason"] or "Project health changed"}.'
            impact = f'{p["overdue_tasks"]} overdue and {p["blocked_tasks"]} blocked task(s) out of {p["open_tasks"]} open.'
            actions = ["Review the overdue and blocked tasks with the project team."]
            if p["unassigned_open_tasks"]:
                actions.append(f'Assign owners to the {p["unassigned_open_tasks"]} unassigned open task(s).')
        else:
            headline, summary, impact = a["title"], a["message"], ""
        if t and t.get("recent_redmine_notes"):
            context.append(f'Latest Redmine note: "{t["recent_redmine_notes"][0]}"')
        return {"headline": headline, "summary": summary, "context": context, "impact": impact, "actions": actions}

    # ------------------------------------------------------------------ #
    #  LLM narrative                                                       #
    # ------------------------------------------------------------------ #
    async def llm_narrative(self, facts: dict) -> dict | None:
        if not (settings.EMAIL_AI_COMPOSE and settings.OPENROUTER_API_KEY):
            return None
        system = (
            "You write short, professional alert emails for a company's project management dashboard. "
            "The reader is a busy manager who will skim on a phone.\n"
            "RULES: Use ONLY the facts in the JSON. Never invent people, dates, numbers, causes or history; "
            "if something is unknown, leave it out. Plain business English. No markdown, no emojis, no ALL-CAPS words, "
            "no brackets or tags like [ALERT].\n"
            "A 'Key details' table with the raw fields (status, priority, assignee, dates, project) is already in the "
            "email, so do NOT repeat those fields as a list — explain what they mean instead.\n"
            "Return ONLY a JSON object with these keys:\n"
            '  "subject": email subject line, max 10 words, starts with what needs attention and names the task '
            'or project (e.g. "Task #12 is 5 days overdue - Website redesign"),\n'
            '  "headline": one sentence (max 15 words) saying what happened,\n'
            '  "summary": 2-3 short sentences explaining the situation and its current state,\n'
            '  "context": array of 0-2 short sentences of useful background NOT already in the key details '
            '(e.g. other overdue work in the same project, latest Redmine note),\n'
            '  "impact": one sentence on why it matters for delivery,\n'
            '  "actions": array of 2-3 concrete next steps, imperative, naming the owner when known.'
        )
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(facts, default=str)}]
        for model in [settings.OPENROUTER_DEFAULT_MODEL, settings.OPENROUTER_FALLBACK_MODEL]:
            if not model:
                continue
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 700,
                "reasoning": {"enabled": False},
                "response_format": {"type": "json_object"},
            }
            try:
                async with httpx.AsyncClient(timeout=settings.EMAIL_AI_TIMEOUT_SECONDS) as client:
                    res = await client.post(
                        f"{settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions",
                        headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                                 "Content-Type": "application/json", "X-Title": "Project Manager"},
                        json=payload,
                    )
                if res.status_code != 200:
                    print(f"[AlertEmail] {model} HTTP {res.status_code}: {res.text[:160]}")
                    continue
                text = (res.json()["choices"][0]["message"].get("content") or "").strip()
            except Exception as exc:
                print(f"[AlertEmail] {model} unavailable: {type(exc).__name__}: {exc}")
                continue
            parsed = self.parse_narrative(text)
            if parsed:
                return parsed
        return None

    @staticmethod
    def parse_narrative(text: str) -> dict | None:
        m = re.search(r"\{.*\}", text or "", re.S)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None
        headline, summary = data.get("headline"), data.get("summary")
        if not (isinstance(headline, str) and headline.strip() and isinstance(summary, str) and summary.strip()):
            return None

        def str_list(v, limit):
            return [s.strip()[:300] for s in v if isinstance(s, str) and s.strip()][:limit] if isinstance(v, list) else []

        subject = data.get("subject")
        subject = re.sub(r"^\s*\[[^\]]*\]\s*", "", subject).strip() if isinstance(subject, str) else ""
        impact = data.get("impact") if isinstance(data.get("impact"), str) else ""
        h = AlertComposer.humanize
        return {
            "subject": h(subject)[:150],
            "headline": h(headline.strip())[:200],
            "summary": h(summary.strip())[:900],
            "context": [h(x) for x in str_list(data.get("context"), 3)],
            "impact": h(impact.strip())[:400],
            "actions": [h(x) for x in str_list(data.get("actions"), 4)],
        }

    _CODES = {"AT_RISK": "at risk", "ON_TRACK": "on track", "OFF_TRACK": "off track", "BLOCKED": "blocked",
              "INACTIVE": "inactive", "ACTIVE": "active", "DONE": "done"}

    @staticmethod
    def humanize(text: str) -> str:
        """Turn internal status codes the model may echo (AT_RISK, ON_TRACK…) into plain words."""
        return re.sub(r"\b(AT_RISK|ON_TRACK|OFF_TRACK|BLOCKED|INACTIVE|ACTIVE|DONE)\b",
                      lambda m: AlertComposer._CODES[m.group(1)], text or "")

    @staticmethod
    def template_subject(n: Notification, headline: str) -> str:
        """Readable subject when the LLM is unavailable, e.g. 'Action needed: "Deploy" is 6 day(s) past its due date'."""
        prefix = {"CRITICAL": "Action needed", "URGENT": "Attention", "WARNING": "Heads-up"}.get(n.severity, "Update")
        if n.title.startswith("Task Completed"):
            prefix = "Completed"
        return f"{prefix}: {headline}"

    # ------------------------------------------------------------------ #
    #  Public                                                              #
    # ------------------------------------------------------------------ #
    async def compose(self, db: AsyncSession, n: Notification, category: str) -> AlertEmailContent:
        facts = await self.gather_facts(db, n)
        narrative = await self.llm_narrative(facts)
        source = "llm" if narrative else "template"
        narrative = narrative or self.template_narrative(facts)
        return AlertEmailContent(
            subject=(narrative.get("subject") or self.template_subject(n, narrative["headline"]))[:250],
            severity=n.severity,
            category=category,
            entity_type=n.entity_type,
            headline=narrative["headline"],
            summary=narrative["summary"],
            details=self.details_table(facts),
            context=narrative["context"],
            impact=narrative["impact"],
            actions=narrative["actions"],
            raised_at=facts["alert"]["raised_at"],
            source=source,
        )


alert_composer = AlertComposer()
