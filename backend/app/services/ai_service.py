"""
Grounded AI Assistant.

Dual-Intelligence Principle:
  * Operational facts (assignments, project status, overdue/blocked counts) are
    computed deterministically in Python by the tool functions below.
  * Questions that map cleanly onto a tool ("Which projects is X working on?",
    "What is the status of project Y?") are answered directly from those tool
    results — no LLM involved, so there is nothing to hallucinate.
  * Open-ended management questions go to OpenRouter with the tool results as
    the only allowed ground truth. If OpenRouter is unreachable, the assistant
    falls back to a deterministic summary instead of failing.
"""
import json
import re
from datetime import date
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.models.project import Project, ProjectMember
from app.models.task import Task
from app.models.employee import Employee
from app.models.notification import Notification
from app.core.scope import AccessScope, ACCESS_DENIED_PROJECTS

COMPLETED_STATUSES = {"DONE", "Resolved", "Closed", "Completed"}

# Words that are too generic to identify a project by themselves
_PROJECT_STOPWORDS = {
    "project", "projects", "system", "systems", "automatic", "automation", "management",
    "generation", "detection", "recognition", "number", "plate", "the", "and", "for",
    "with", "status", "team", "app", "application",
}

_ASSIGNMENT_WORDS = (
    "working on", "work on", "works on", "assigned", "assignment", "allocat", "involved",
    "projects", "project", "member of", "part of", "tasks", "task", "workload", "doing",
)
_ROSTER_PATTERNS = (
    "who is working on what", "who works on what", "all assignments", "everyone working",
    "team assignments", "project assignments", "who is on which project", "which employee",
    "employees and their projects", "who is working on which",
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower())).strip()


def _has_word(haystack_norm: str, needle_norm: str) -> bool:
    return bool(needle_norm) and re.search(rf"(?<![a-z0-9]){re.escape(needle_norm)}(?![a-z0-9])", haystack_norm) is not None


class AIService:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_DEFAULT_MODEL
        self.fallback_model = settings.OPENROUTER_FALLBACK_MODEL
        self.api_url = f"{settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"

    # ================================================================== #
    #  Snapshot loader (one consistent read of the operational data)      #
    # ================================================================== #
    async def _load_snapshot(self, db: AsyncSession) -> dict:
        projects = (await db.execute(select(Project).order_by(Project.name))).scalars().all()
        tasks = (await db.execute(select(Task))).scalars().all()
        from app.models.user import User
        unapproved = set((await db.execute(select(Employee.id).join(User, User.id == Employee.user_id)
                                           .where(User.approval_status != "APPROVED"))).scalars().all())
        employees = [e for e in (await db.execute(select(Employee).order_by(Employee.first_name))).scalars().all()
                     if e.id not in unapproved]
        memberships = (await db.execute(select(ProjectMember))).scalars().all()
        return {
            "projects": {p.id: p for p in projects},
            "tasks": list(tasks),
            "employees": {e.id: e for e in employees},
            "memberships": list(memberships),
            "today": date.today(),
        }

    # ================================================================== #
    #  RBAC guardrail (runs before any tool or LLM call)                   #
    # ================================================================== #
    def _out_of_scope_reference(self, prompt: str, snap: dict, scope: AccessScope) -> str | None:
        """
        Name of a project or person outside the user's scope that the prompt explicitly
        names (full project name / code / acronym, or a full person name), else None.
        Only unambiguous references count, so ordinary words never trigger a denial.
        """
        p_norm = _norm(prompt)

        def project_named(p: Project) -> bool:
            name_n, code_n = _norm(p.name), _norm(p.code)
            acronyms = [a.lower() for a in re.findall(r"\(([A-Za-z0-9]{3,})\)", p.name)]
            return (_has_word(p_norm, name_n) or (len(code_n) >= 4 and _has_word(p_norm, code_n))
                    or any(_has_word(p_norm, a) for a in acronyms))

        named = [p for p in snap["projects"].values() if project_named(p)]
        if named and not any(scope.can_see_project(p.id) for p in named):
            return named[0].name.strip()

        people = [e for e in snap["employees"].values()
                  if len(_norm(self._emp_name(e)).split()) >= 2 and _has_word(p_norm, _norm(self._emp_name(e)))]
        if people and not any(scope.can_see_employee(e.id) for e in people):
            return self._emp_name(people[0])
        return None

    @staticmethod
    def _restrict_snapshot(snap: dict, scope: AccessScope) -> dict:
        """The only data a scoped user's question may be answered from."""
        return {
            "projects": {pid: p for pid, p in snap["projects"].items() if scope.can_see_project(pid)},
            "tasks": [t for t in snap["tasks"] if scope.can_see_project(t.project_id)],
            "employees": {eid: e for eid, e in snap["employees"].items() if scope.can_see_employee(eid)},
            "memberships": [m for m in snap["memberships"] if scope.can_see_project(m.project_id)],
            "today": snap["today"],
        }

    @staticmethod
    def _emp_name(e: Employee) -> str:
        return f"{e.first_name} {e.last_name}".strip()

    @staticmethod
    def _task_open(t: Task) -> bool:
        return t.status not in COMPLETED_STATUSES and (t.progress_percentage or 0) < 100

    @staticmethod
    def _task_overdue(t: Task, today: date) -> bool:
        return bool(t.due_date and t.due_date < today and t.status not in COMPLETED_STATUSES and (t.progress_percentage or 0) < 100)

    def _task_fact(self, t: Task, snap: dict) -> dict:
        today = snap["today"]
        proj = snap["projects"].get(t.project_id)
        assignee = snap["employees"].get(t.assigned_to_id) if t.assigned_to_id else None
        overdue = self._task_overdue(t, today)
        return {
            "id": t.id,
            "title": t.title,
            "project": proj.name if proj else None,
            "status": t.status,
            "priority": t.priority,
            "due_date": str(t.due_date) if t.due_date else None,
            "is_overdue": overdue,
            "days_overdue": (today - t.due_date).days if overdue else 0,
            "is_blocked": bool(t.is_blocked),
            "blocker_reason": t.blocker_reason,
            "assignee": self._emp_name(assignee) if assignee else None,
            "progress_percentage": int(t.progress_percentage or 0),
        }

    # ================================================================== #
    #  Deterministic tools                                                #
    # ================================================================== #
    def tool_get_project_status(self, project: Project, snap: dict) -> dict:
        today = snap["today"]
        p_tasks = [t for t in snap["tasks"] if t.project_id == project.id]
        open_tasks = [t for t in p_tasks if self._task_open(t)]
        overdue = [t for t in open_tasks if self._task_overdue(t, today)]
        blocked = [t for t in open_tasks if t.is_blocked]
        members = []
        seen = set()
        for m in snap["memberships"]:
            if m.project_id != project.id or m.employee_id in seen:
                continue
            emp = snap["employees"].get(m.employee_id)
            if emp:
                seen.add(m.employee_id)
                members.append({"name": self._emp_name(emp), "role": m.role_in_project or "Contributor"})
        return {
            "id": project.id,
            "name": project.name.strip(),
            "code": project.code,
            "status": project.status,
            "health_status": project.health_status,
            "health_reason": project.health_reason,
            "progress_percentage": float(project.progress_percentage or 0.0),
            "target_completion_date": str(project.target_completion_date) if project.target_completion_date else None,
            "total_tasks": len(p_tasks),
            "open_tasks": len(open_tasks),
            "completed_tasks": len(p_tasks) - len(open_tasks),
            "overdue_tasks": len(overdue),
            "blocked_tasks": len(blocked),
            "members": members,
            "overdue_task_list": [self._task_fact(t, snap) for t in sorted(overdue, key=lambda t: t.due_date)][:10],
            "blocked_task_list": [self._task_fact(t, snap) for t in blocked][:10],
        }

    def tool_get_employee_assignments(self, employee: Employee, snap: dict) -> dict:
        today = snap["today"]
        projects: dict[str, dict] = {}
        for m in snap["memberships"]:
            if m.employee_id != employee.id:
                continue
            p = snap["projects"].get(m.project_id)
            if p:
                projects[p.id] = {"name": p.name.strip(), "code": p.code, "status": p.status,
                                  "health_status": p.health_status,
                                  "role": m.role_in_project or "Contributor", "source": "Redmine membership"}
        e_tasks = [t for t in snap["tasks"] if t.assigned_to_id == employee.id]
        for t in e_tasks:
            p = snap["projects"].get(t.project_id)
            if p and p.id not in projects:
                projects[p.id] = {"name": p.name.strip(), "code": p.code, "status": p.status,
                                  "health_status": p.health_status,
                                  "role": "Task assignee", "source": "Assigned Redmine issue"}
        open_tasks = [t for t in e_tasks if self._task_open(t)]
        return {
            "id": employee.id,
            "name": self._emp_name(employee),
            "email": employee.email,
            "job_title": employee.job_title,
            "status": employee.status,
            "projects": sorted(projects.values(), key=lambda x: (x["status"] != "ACTIVE", x["name"].lower())),
            "total_tasks": len(e_tasks),
            "open_tasks": len(open_tasks),
            "overdue_tasks": sum(1 for t in open_tasks if self._task_overdue(t, today)),
            "open_task_list": [self._task_fact(t, snap) for t in open_tasks][:15],
        }

    def tool_get_projects_overview(self, snap: dict) -> list[dict]:
        return [self.tool_get_project_status(p, snap) for p in snap["projects"].values()]

    def tool_get_assignment_roster(self, snap: dict) -> list[dict]:
        roster = []
        for e in snap["employees"].values():
            a = self.tool_get_employee_assignments(e, snap)
            if a["projects"]:
                roster.append({"name": a["name"], "projects": [f'{p["name"]} ({p["role"]})' for p in a["projects"]],
                               "open_tasks": a["open_tasks"], "overdue_tasks": a["overdue_tasks"]})
        return roster

    # ================================================================== #
    #  Entity resolution                                                  #
    # ================================================================== #
    def _match_employees(self, prompt_norm: str, snap: dict) -> list[Employee]:
        full, first = [], {}
        for e in snap["employees"].values():
            name_n = _norm(self._emp_name(e))
            if _has_word(prompt_norm, name_n):
                full.append(e)
            else:
                fn = _norm(e.first_name)
                if len(fn) >= 3:
                    first.setdefault(fn, []).append(e)
        if full:
            return full
        hits: list[Employee] = []
        for fn, emps in first.items():
            if _has_word(prompt_norm, fn):
                hits.extend(emps)
        return hits

    def _match_projects(self, prompt_norm: str, snap: dict) -> list[Project]:
        exact, partial = [], []
        for p in snap["projects"].values():
            name_n, code_n = _norm(p.name), _norm(p.code)
            if _has_word(prompt_norm, name_n) or (code_n and _has_word(prompt_norm, code_n)):
                exact.append(p)
                continue
            tokens = [t for t in name_n.split() if len(t) >= 4 and t not in _PROJECT_STOPWORDS]
            # also match acronyms in parentheses, e.g. "(ANPR)"
            tokens += [a.lower() for a in re.findall(r"\(([A-Za-z0-9]{2,})\)", p.name)]
            if any(_has_word(prompt_norm, t) for t in tokens):
                partial.append(p)
        return exact or partial

    # ================================================================== #
    #  Deterministic answer renderers                                     #
    # ================================================================== #
    @staticmethod
    def _render_assignments(a: dict) -> str:
        lines = [f"### {a['name']} — current project assignments"]
        if not a["projects"]:
            lines.append(f"No project memberships or assigned Redmine issues are recorded for **{a['name']}**.")
        else:
            active = [p for p in a["projects"] if p["status"] == "ACTIVE"]
            lines.append(f"**{len(active)} active project(s)**"
                         + (f", {len(a['projects']) - len(active)} inactive" if len(active) != len(a["projects"]) else "") + ":")
            for p in a["projects"]:
                lines.append(f"- **{p['name']}** (`{p['code']}`) — role: {p['role']}; project {p['status']}, health {p['health_status']}")
        lines.append(f"\n**Tasks:** {a['open_tasks']} open, {a['overdue_tasks']} overdue, {a['total_tasks']} total assigned.")
        for t in a["open_task_list"][:8]:
            flag = " ⚠️ overdue" if t["is_overdue"] else (" ⛔ blocked" if t["is_blocked"] else "")
            due = f", due {t['due_date']}" if t["due_date"] else ""
            lines.append(f"- {t['title']} — {t['project']} ({t['status']}{due}){flag}")
        return "\n".join(lines)

    @staticmethod
    def _render_project(s: dict) -> str:
        lines = [
            f"### {s['name']} (`{s['code']}`)",
            f"- **Status:** {s['status']} · **Health:** {s['health_status']}"
            + (f" — {s['health_reason']}" if s["health_reason"] else ""),
            f"- **Progress:** {s['progress_percentage']:.0f}%"
            + (f" · target {s['target_completion_date']}" if s["target_completion_date"] else ""),
            f"- **Tasks:** {s['open_tasks']} open, {s['completed_tasks']} completed, "
            f"**{s['overdue_tasks']} overdue**, **{s['blocked_tasks']} blocked** ({s['total_tasks']} total)",
        ]
        if s["members"]:
            lines.append("- **Team:** " + ", ".join(f"{m['name']} ({m['role']})" for m in s["members"]))
        else:
            lines.append("- **Team:** no Redmine memberships recorded")
        if s["overdue_task_list"]:
            lines.append("\n**Overdue tasks:**")
            for t in s["overdue_task_list"][:6]:
                lines.append(f"- {t['title']} — due {t['due_date']} ({t['days_overdue']} day(s) late), "
                             f"assignee: {t['assignee'] or 'unassigned'}")
        if s["blocked_task_list"]:
            lines.append("\n**Blocked tasks:**")
            for t in s["blocked_task_list"][:6]:
                lines.append(f"- {t['title']} — {t['blocker_reason'] or 'blocked'}")
        return "\n".join(lines)

    def _render_overview(self, snap: dict) -> str:
        overview = self.tool_get_projects_overview(snap)
        active = [p for p in overview if p["status"] == "ACTIVE"]
        lines = [f"### Portfolio overview ({snap['today']})",
                 f"**{len(active)} active** of {len(overview)} synchronized projects."]
        for p in sorted(active, key=lambda x: (-x["overdue_tasks"] - x["blocked_tasks"], x["name"])):
            lines.append(f"- **{p['name']}** — health {p['health_status']}; {p['open_tasks']} open, "
                         f"{p['overdue_tasks']} overdue, {p['blocked_tasks']} blocked; team of {len(p['members'])}")
        return "\n".join(lines)

    # ================================================================== #
    #  Legacy context (kept for callers/tests) — now membership-aware     #
    # ================================================================== #
    async def get_grounded_context(self, db: AsyncSession) -> dict:
        snap = await self._load_snapshot(db)
        project_list = [
            {"id": p.id, "name": p.name, "code": p.code, "status": p.status,
             "health_status": p.health_status, "health_reason": p.health_reason,
             "progress_percentage": float(p.progress_percentage or 0.0)}
            for p in snap["projects"].values()
        ]
        tasks_summary = [self._task_fact(t, snap) | {"project_id": t.project_id, "assignee_id": t.assigned_to_id}
                         for t in sorted(snap["tasks"], key=lambda t: (t.due_date is None, t.due_date or date.max))]
        emp_list = [
            {"id": e.id, "name": self._emp_name(e), "email": e.email, "department": e.department,
             "job_title": e.job_title,
             "projects": [p["name"] for p in self.tool_get_employee_assignments(e, snap)["projects"]]}
            for e in snap["employees"].values()
        ]
        n_res = await db.execute(
            select(Notification).where(Notification.is_read == False)
            .order_by(Notification.created_at.desc()).limit(10)
        )
        alerts = [{"id": n.id, "severity": n.severity, "title": n.title, "message": n.message,
                   "entity_type": n.entity_type} for n in n_res.scalars().all()]
        return {
            "projects": project_list,
            "tasks": tasks_summary,
            "employees": emp_list,
            "memberships": [
                {"project": snap["projects"][m.project_id].name if m.project_id in snap["projects"] else None,
                 "employee": self._emp_name(snap["employees"][m.employee_id]) if m.employee_id in snap["employees"] else None,
                 "role": m.role_in_project}
                for m in snap["memberships"]
            ],
            "active_alerts": alerts,
            "current_date": str(snap["today"]),
        }

    # ================================================================== #
    #  Query routing                                                      #
    # ================================================================== #
    def _route_deterministic(self, prompt: str, snap: dict) -> dict | None:
        """Returns a fully deterministic answer when the question maps onto a tool."""
        p_norm = _norm(prompt)
        p_low = prompt.lower()
        employees = self._match_employees(p_norm, snap)
        projects = self._match_projects(p_norm, snap)

        # Roster: "who is working on what?"
        if not employees and not projects and any(k in p_low for k in _ROSTER_PATTERNS):
            roster = self.tool_get_assignment_roster(snap)
            lines = ["### Current project assignments (from Redmine memberships & issue assignees)"]
            for r in roster:
                lines.append(f"- **{r['name']}** — {', '.join(r['projects'])} · {r['open_tasks']} open task(s)"
                             + (f", {r['overdue_tasks']} overdue" if r["overdue_tasks"] else ""))
            if not roster:
                lines.append("No project memberships are recorded yet. Run a Redmine sync first.")
            return {"response": "\n".join(lines), "tools": ["get_assignment_roster"], "facts": {"assignments": roster},
                    "sources": [{"type": "employee", "id": None, "label": f"{len(roster)} employees"}]}

        # Employee assignment questions ("Which projects is X working on?")
        if employees and (not projects or any(k in p_low for k in _ASSIGNMENT_WORDS)):
            answers = [self.tool_get_employee_assignments(e, snap) for e in employees[:3]]
            # Same person can exist twice (platform login + Redmine user): prefer records with real data
            with_data = [a for a in answers if a["projects"] or a["total_tasks"]]
            hidden = len(answers) - len(with_data) if with_data else 0
            if with_data:
                answers = with_data
            text = "\n\n".join(self._render_assignments(a) for a in answers)
            if len(answers) > 1:
                text = f"{len(answers)} employee records match this name; showing each separately.\n\n" + text
            if hidden:
                text += (f"\n\n_{hidden} other record(s) with this name have no project memberships "
                         f"or assigned issues (e.g. a platform login account)._")
            return {"response": text, "tools": ["get_employee_assignments"], "facts": {"employees": answers},
                    "sources": [{"type": "employee", "id": a["id"], "label": a["name"]} for a in answers]}

        # Project status questions ("What is the status of project Y?")
        if projects:
            statuses = [self.tool_get_project_status(p, snap) for p in projects[:3]]
            return {"response": "\n\n".join(self._render_project(s) for s in statuses),
                    "tools": ["get_project_status"], "facts": {"projects": statuses},
                    "sources": [{"type": "project", "id": s["id"], "label": s["name"]} for s in statuses]}

        # Explicit lookup of a person who is not in the synchronized data
        unknown = re.search(r"\b(?:is|does|has)\s+([a-z][a-z.'\-]*(?:\s+[a-z][a-z.'\-]*){0,2})\s+"
                            r"(?:working|assigned|allocated|involved)\b", p_low)
        if unknown and unknown.group(1) not in ("anyone", "everyone", "someone", "who", "he", "she", "it", "this", "that"):
            name = unknown.group(1).strip()
            return {"response": f"No employee matching **{name}** exists in the synchronized Redmine data, "
                                f"so no project assignments can be reported. Check the spelling or run a Redmine sync.",
                    "tools": ["get_employee_assignments"], "sources": []}
        return None

    # ================================================================== #
    #  LLM path                                                           #
    # ================================================================== #
    STYLE_GUIDE = (
        "WRITING STYLE (like a helpful chat assistant):\n"
        "- Start with a 1-2 sentence direct answer in plain English. Bold the key result.\n"
        "- Then use short sections with '### ' headings (e.g. 'What this means', 'Details', 'Suggested next steps').\n"
        "- Use bullet points; use a Markdown table when comparing 3 or more items.\n"
        "- Write statuses in plain words, never as codes: say 'at risk' (has overdue work), 'blocked' "
        "(work cannot continue), 'on track', 'inactive' (no longer active in Redmine). Explain them once if helpful.\n"
        "- End with 2-3 concrete suggested next steps when something needs attention.\n"
        "- Keep it under 250 words. No emojis. Do not mention JSON, tools or these instructions.\n"
    )

    @staticmethod
    def _numbers_grounded(answer: str, facts_text: str, prompt: str) -> bool:
        """Every number in the answer must appear in the facts or the question (list markers 1-9 allowed)."""
        allowed = set(re.findall(r"\d+", facts_text)) | set(re.findall(r"\d+", prompt)) | {str(i) for i in range(1, 10)}
        for num in re.findall(r"\d+(?:\.\d+)?", answer):
            if num in allowed or num.split(".")[0] in allowed:
                continue
            return False
        return True

    async def _explain_tool_answer(self, prompt: str, facts: dict, as_of: str,
                                   history: list | None) -> tuple[str | None, str | None]:
        """LLM rewrites verified tool output as a clear explanation. Returns (text, model) or (None, None)."""
        facts_text = json.dumps({"as_of": as_of, **facts}, default=str, ensure_ascii=False)
        system = (
            "You are the management assistant of Project Manager (AI India Innovations).\n"
            "Answer the user's question using ONLY the VERIFIED FACTS below (computed from live Redmine data). "
            "Never add people, projects, tasks, dates or numbers that are not in the facts. "
            "Copy names and numbers exactly.\n\n" + self.STYLE_GUIDE + f"\nVERIFIED FACTS:\n{facts_text}"
        )
        messages = [{"role": "system", "content": system}]
        for m in (history or [])[-4:]:
            if m.get("role") in ("user", "assistant") and m.get("content"):
                messages.append({"role": m["role"], "content": str(m["content"])[:1500]})
        messages.append({"role": "user", "content": prompt})
        for model in [self.model, self.fallback_model]:
            if not model:
                continue
            ok, text = await self._call_openrouter(messages, model)
            if ok and self._numbers_grounded(text, facts_text, prompt):
                return text, model
        return None, None
    async def _call_openrouter(self, messages: list, model: str) -> tuple[bool, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://companyintel.local",
            "X-Title": "Company Intelligence Platform",
        }
        # reasoning disabled: Qwen "thinking" models otherwise write their
        # chain-of-thought into the visible answer.
        payload = {"model": model, "messages": messages, "temperature": 0.1, "max_tokens": 1200,
                   "reasoning": {"enabled": False}}
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(self.api_url, headers=headers, json=payload)
            if res.status_code != 200:
                return False, f"HTTP {res.status_code}: {res.text[:200]}"
            text = (res.json()["choices"][0]["message"].get("content") or "").strip()
            if "</think>" in text:
                text = text.split("</think>")[-1].strip()
            if text.lower().startswith(("thinking process", "<think>")):
                return False, "model returned its reasoning instead of an answer"
            return (bool(text), text or "empty completion")
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"

    async def answer_management_query(self, db: AsyncSession, prompt: str, conversation_history: list = None,
                                      scope: AccessScope | None = None) -> dict:
        snap = await self._load_snapshot(db)
        scoped = scope is not None and not scope.is_global

        # 0. RBAC guardrail: a question that names another project / person is refused
        #    deterministically, and everything below only ever sees the user's own projects.
        if scoped:
            blocked = self._out_of_scope_reference(prompt, snap, scope)
            if blocked:
                return {
                    "model": "deterministic-guardrail",
                    "mode": "access_denied",
                    "response": ACCESS_DENIED_PROJECTS,
                    "grounded": True,
                    "access_denied": True,
                    "tools_used": [],
                    "sources": [],
                    "citations_count": 0,
                    "as_of": str(snap["today"]),
                }
            snap = self._restrict_snapshot(snap, scope)

        # 1. Deterministic tool answer (zero LLM involvement)
        routed = self._route_deterministic(prompt, snap)
        if routed and routed.get("facts") and settings.AI_EXPLAIN_TOOL_ANSWERS and self.api_key:
            text, model = await self._explain_tool_answer(prompt, routed["facts"], str(snap["today"]),
                                                          conversation_history)
            if text:
                return {
                    "model": model,
                    "mode": "tools_explained",
                    "response": text,
                    "grounded": True,
                    "tools_used": routed["tools"],
                    "sources": routed["sources"],
                    "citations_count": len(routed["sources"]),
                    "as_of": str(snap["today"]),
                }
        if routed:
            return {
                "model": "deterministic-tools",
                "mode": "deterministic",
                "response": routed["response"],
                "grounded": True,
                "tools_used": routed["tools"],
                "sources": routed["sources"],
                "citations_count": len(routed["sources"]),
                "as_of": str(snap["today"]),
            }

        # 2. LLM synthesis over verified tool output
        overview = self.tool_get_projects_overview(snap)
        roster = self.tool_get_assignment_roster(snap)
        today = snap["today"]
        open_tasks = [self._task_fact(t, snap) for t in snap["tasks"] if self._task_open(t)]
        facts = {
            "as_of": str(today),
            "projects": [{k: v for k, v in p.items() if k not in ("overdue_task_list", "blocked_task_list", "id")} for p in overview],
            "employee_assignments": roster,
            "open_tasks": [{k: v for k, v in t.items() if k != "id"} for t in open_tasks],
            "unassigned_open_tasks": sum(1 for t in open_tasks if not t["assignee"]),
            "employees_without_projects": [self._emp_name(e) for e in snap["employees"].values()
                                           if self._emp_name(e) not in {r["name"] for r in roster}],
        }
        system_instruction = (
            "You are the management assistant of Project Manager, AI India Innovations "
            + ("(team member view: only the user's assigned projects are included).\n" if scoped
               else "(administrator view).\n")
            + "RULES (mandatory):\n"
            "1. Use ONLY the VERIFIED FACTS JSON below. It is computed deterministically from live Redmine data.\n"
            "2. Never invent projects, people, tasks, dates or numbers. If the facts do not contain the answer, "
            "say plainly that no matching record exists in the synchronized Redmine data.\n"
            "3. Quote counts exactly as given. Highlight overdue/blocked work and AT_RISK/BLOCKED projects.\n\n"
            + self.STYLE_GUIDE + "\n"
            f"VERIFIED FACTS:\n{json.dumps(facts, default=str, ensure_ascii=False)}"
        )
        messages = [{"role": "system", "content": system_instruction}]
        for m in (conversation_history or [])[-6:]:
            if m.get("role") in ("user", "assistant") and m.get("content"):
                messages.append({"role": m["role"], "content": str(m["content"])[:2000]})
        messages.append({"role": "user", "content": prompt})

        sources = [{"type": "project", "id": p["id"], "label": p["name"]} for p in overview if p["status"] == "ACTIVE"]
        if self.api_key:
            for model in [self.model, self.fallback_model]:
                if not model:
                    continue
                ok, text = await self._call_openrouter(messages, model)
                if ok:
                    return {
                        "model": model,
                        "mode": "llm_grounded",
                        "response": text,
                        "grounded": True,
                        "tools_used": ["get_projects_overview", "get_assignment_roster", "get_open_tasks"],
                        "sources": sources,
                        "citations_count": len(overview) + len(open_tasks),
                        "as_of": str(today),
                    }
                print(f"[AI] {model} unavailable: {text[:200]}")  # server log only

        # 3. Deterministic fallback — still grounded, never an invented answer
        return {
            "model": "deterministic-tools",
            "mode": "deterministic_fallback",
            "response": self._render_overview(snap)
            + "\n\n_The AI summary is temporarily unavailable, so only the key figures are shown._",
            "grounded": True,
            "tools_used": ["get_projects_overview"],
            "sources": sources,
            "citations_count": len(overview),
            "as_of": str(today),
        }


ai_service = AIService()
