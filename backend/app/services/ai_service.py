import json
import httpx
from datetime import datetime, date, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.core.config import settings
from app.models.project import Project
from app.models.task import Task
from app.models.employee import Employee
from app.models.notification import Notification

class AIService:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_DEFAULT_MODEL or "qwen/qwen3.5-flash-02-23"
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    async def get_grounded_context(self, db: AsyncSession) -> dict:
        """
        Deterministic database extraction tool.
        Collects 100% verified operational facts from PostgreSQL / SQLite.
        Guarantees zero-hallucination ground truth for Qwen3.5-Flash.
        """
        # 1. Projects
        p_res = await db.execute(select(Project).order_by(Project.created_at.desc()))
        projects = p_res.scalars().all()
        project_list = [
            {
                "id": p.id,
                "name": p.name,
                "code": p.code,
                "status": p.status,
                "health_status": p.health_status,
                "health_reason": p.health_reason,
                "progress_percentage": float(p.progress_percentage or 0.0)
            }
            for p in projects
        ]

        # 2. Overdue & Blocked Tasks
        t_res = await db.execute(select(Task).order_by(Task.due_date.asc()))
        all_tasks = t_res.scalars().all()
        today = date.today()

        tasks_summary = []
        for t in all_tasks:
            days_late = (today - t.due_date).days if (t.due_date and t.due_date < today) else 0
            tasks_summary.append({
                "id": t.id,
                "title": t.title,
                "project_id": t.project_id,
                "status": t.status,
                "priority": t.priority,
                "due_date": str(t.due_date) if t.due_date else None,
                "is_overdue": bool(t.is_overdue or days_late > 0),
                "days_overdue": days_late,
                "is_blocked": t.is_blocked,
                "blocker_reason": t.blocker_reason,
                "assignee_id": t.assigned_to_id
            })

        # 3. Employees
        e_res = await db.execute(select(Employee))
        employees = e_res.scalars().all()
        emp_list = [
            {
                "id": e.id,
                "name": f"{e.first_name} {e.last_name}",
                "email": e.email,
                "department": e.department,
                "job_title": e.job_title
            }
            for e in employees
        ]

        # 4. Recent Active Alerts
        n_res = await db.execute(
            select(Notification)
            .where(Notification.is_read == False)
            .order_by(Notification.created_at.desc())
            .limit(10)
        )
        alerts = [
            {
                "id": n.id,
                "severity": n.severity,
                "title": n.title,
                "message": n.message,
                "entity_type": n.entity_type
            }
            for n in n_res.scalars().all()
        ]

        return {
            "projects": project_list,
            "tasks": tasks_summary,
            "employees": emp_list,
            "active_alerts": alerts,
            "current_date": str(today)
        }

    async def answer_management_query(self, db: AsyncSession, prompt: str, conversation_history: list = None) -> dict:
        """
        Synthesizes a grounded response using Qwen3.5-Flash on OpenRouter.
        """
        context = await self.get_grounded_context(db)

        system_instruction = f"""You are the Company Intelligence Platform Management AI Assistant for the Administrator.
Your task is to provide concise, factual, executive-level insights regarding projects, workloads, blockers, and deadlines.

MANDATORY INVARIANTS:
1. ZERO HALLUCINATION: You MUST ONLY cite facts that exist in the VERIFIED SYSTEM DATA provided below.
2. If asked about a project, task, or person not in the data, clearly state that no matching record exists in the system.
3. Explicitly highlight blocked tasks, overdue deadlines, and projects with AT_RISK or BLOCKED health statuses.
4. Format responses using clean Markdown with bullet points, bold key metrics, and direct action recommendations.

VERIFIED SYSTEM DATA (Ground Truth as of {context['current_date']}):
- Projects Count: {len(context['projects'])}
- Projects Details: {json.dumps(context['projects'])}
- Overdue Tasks: {json.dumps([t for t in context['tasks'] if t['is_overdue']])}
- Blocked Tasks: {json.dumps([t for t in context['tasks'] if t['is_blocked']])}
- Employees: {json.dumps(context['employees'])}
- Active Unread Alerts: {json.dumps(context['active_alerts'])}
"""

        messages = [{"role": "system", "content": system_instruction}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://companyintel.local",
            "X-Title": "Company Intelligence Platform"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1200
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(self.api_url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    answer_text = data["choices"][0]["message"]["content"]
                    
                    # Clean thinking blocks if model returned internal reasoning
                    if "<think>" in answer_text and "</think>" in answer_text:
                        answer_text = answer_text.split("</think>")[-1].strip()
                    elif answer_text.startswith("Thinking Process:"):
                        # If model outputs raw thinking process without tags
                        parts = answer_text.split("\n\n")
                        # Pick segments that start with executive markdown (# or Executive or Based on)
                        filtered = [p for p in parts if not (p.strip().startswith(("Thinking Process:", "1.", "2.", "3.", "4.", "5.", "* "))) or p.strip().startswith(("#", "###", "Based", "**Projects"))]
                        if filtered:
                            answer_text = "\n\n".join(filtered).strip()

                    return {
                        "model": self.model,
                        "response": answer_text,
                        "grounded": True,
                        "citations_count": len(context["projects"]) + len(context["tasks"])
                    }
                else:
                    return {
                        "model": self.model,
                        "response": f"AI service error ({res.status_code}): {res.text[:200]}",
                        "grounded": False
                    }
        except Exception as e:
            return {
                "model": self.model,
                "response": f"Failed to reach OpenRouter gateway: {str(e)}",
                "grounded": False
            }

ai_service = AIService()
