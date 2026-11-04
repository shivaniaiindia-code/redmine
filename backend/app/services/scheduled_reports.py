"""
Scheduled emails to the Administration recipient list:

  * Daily digest  — every morning (Mon–Sat): what needs attention today.
  * Weekly report — once a week: the past 7 days vs the week before, with a PDF.

All figures come from the deterministic Reports engine (live Redmine data).
The AI only writes a short summary paragraph, and that paragraph is rejected
if it contains a number that is not in the facts (template sentence instead).
Each send is recorded in scheduled_email_runs, so a restart never re-sends.
"""
import html
import json
import re
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.alert_config import AlertEmailRecipient, AlertRecipientConfig, ScheduledEmailRun
from app.services.email_service import email_service

KIND_DAILY = "DAILY_DIGEST"
KIND_WEEKLY = "WEEKLY_REPORT"
SEND_WINDOW_HOURS = 6          # a digest missed (server off) is still sent up to 6 h after its time
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
REASON = ("You receive this because you are on the platform's email recipient list "
          "(Administration → Email Recipients).")


def local_now() -> datetime:
    try:
        return datetime.now(ZoneInfo(settings.APP_TIMEZONE))
    except Exception:
        return datetime.now().astimezone()


def humanize(text: str) -> str:
    from app.services.alert_composer import AlertComposer
    return AlertComposer.humanize(text or "")


async def _overview(db: AsyncSession, days: int) -> dict:
    from app.api.v1.reports import reports_overview
    from app.core.scope import AccessScope
    # Scheduled digests go to the admin-managed recipient list: company-wide figures
    return await reports_overview(current_user=None, scope=AccessScope(is_global=True), db=db, weeks=8,
                                  include_inactive=False, days=days)


# ---------------------------------------------------------------------- #
#  Facts                                                                  #
# ---------------------------------------------------------------------- #
def _who(name: str | None) -> str:
    return name.title() if name else "Unassigned"


def _attention_projects(r: dict) -> list[dict]:
    return [{"name": p["name"], "health": humanize(p["health_status"]), "reason": p["health_reason"] or "",
             "overdue": p["overdue_tasks"], "blocked": p["blocked_tasks"]}
            for p in r["projects"] if p["status"] == "ACTIVE" and p["health_status"] != "ON_TRACK"]


def daily_facts(r: dict) -> dict:
    people = r["people"]["employees"]
    k = r["kpis"]
    return {
        "right_now": {"open_tasks": k["open_tasks"], "overdue_tasks": k["overdue_tasks"],
                      "blocked_tasks": k["blocked_tasks"], "unassigned_open_tasks": k["unassigned_open_tasks"],
                      "projects_needing_attention": k["at_risk_projects"]},
        "since_yesterday": {"tasks_completed": r["period_stats"]["tasks_completed"],
                            "tasks_created": r["period_stats"]["tasks_created"],
                            "redmine_updates": r["period_stats"]["redmine_updates"],
                            "critical_alerts": r["period_stats"]["alerts_critical"],
                            "urgent_alerts": r["period_stats"]["alerts_urgent"]},
        "overdue": [{"task": t["title"], "project": t["project"], "assignee": _who(t["assignee"]),
                     "days_overdue": t["days_overdue"]} for t in r["top_overdue"][:8]],
        "due_soon": [{"task": d["title"], "project": d["project"], "assignee": _who(d["assignee"]),
                      "due": "today" if d["days_left"] == 0 else ("tomorrow" if d["days_left"] == 1 else f'in {d["days_left"]} days')}
                     for d in r["upcoming_deadlines"] if 0 <= d["days_left"] <= 3][:8],
        "projects_needing_attention": _attention_projects(r),
        "free_today": [p["name"].title() for p in people if p["availability"] == "Free"],
        "overloaded": [{"name": p["name"].title(), "open_tasks": p["open_tasks"]} for p in people if p["availability"] == "Overloaded"],
    }


def _delta(cur: int, prev: int | None) -> str:
    if prev is None:
        return ""
    d = cur - prev
    return "same as last week" if d == 0 else (f"{d:+d} vs last week")


def weekly_facts(r: dict) -> dict:
    s, p = r["period_stats"], r["prev_period_stats"] or {}
    k = r["kpis"]
    return {
        "week": {"tasks_completed": s["tasks_completed"], "tasks_created": s["tasks_created"],
                 "redmine_updates": s["redmine_updates"], "critical_alerts": s["alerts_critical"],
                 "urgent_alerts": s["alerts_urgent"]},
        "previous_week": {"tasks_completed": p.get("tasks_completed"), "tasks_created": p.get("tasks_created"),
                          "redmine_updates": p.get("redmine_updates"), "critical_alerts": p.get("alerts_critical")},
        "right_now": {"open_tasks": k["open_tasks"], "overdue_tasks": k["overdue_tasks"], "blocked_tasks": k["blocked_tasks"],
                      "unassigned_open_tasks": k["unassigned_open_tasks"], "completion_rate_percent": k["completion_rate"],
                      "active_projects": k["active_projects"], "projects_needing_attention": k["at_risk_projects"]},
        "projects": [{"name": x["name"], "health": humanize(x["health_status"]), "open": x["total_tasks"] - x["completed_tasks"],
                      "completed": x["completed_tasks"], "overdue": x["overdue_tasks"], "blocked": x["blocked_tasks"],
                      "progress_percent": round(x["progress_percentage"])}
                     for x in r["projects"] if x["status"] == "ACTIVE"],
        "top_contributors": [{"rank": e["rank"], "name": e["name"].title(), "completed": e["completed_in_period"],
                              "updates": e["updates_in_period"], "open": e["open_tasks"], "overdue": e["overdue"],
                              "score": e["score"]} for e in r["people"]["employees"]
                             if e["score"] or e["completed_in_period"] or e["updates_in_period"]][:5],
        "overdue": [{"task": t["title"], "project": t["project"], "assignee": _who(t["assignee"]),
                     "days_overdue": t["days_overdue"]} for t in r["top_overdue"][:8]],
    }


# ---------------------------------------------------------------------- #
#  AI summary paragraph (number-guarded)                                  #
# ---------------------------------------------------------------------- #
def numbers_grounded(text: str, facts_text: str) -> bool:
    allowed = set(re.findall(r"\d+", facts_text)) | {str(i) for i in range(0, 10)}
    return all(n.split(".")[0] in allowed for n in re.findall(r"\d+(?:\.\d+)?", text))


async def ai_summary(kind: str, facts: dict) -> str | None:
    if not (settings.EMAIL_AI_COMPOSE and settings.OPENROUTER_API_KEY):
        return None
    focus = ("what the manager should focus on today" if kind == KIND_DAILY
             else "how the week went compared with the previous week and what to focus on next week")
    system = (
        "You write the opening paragraph of a management email for a company's project dashboard. "
        f"In 2-3 short sentences (under 70 words in total), explain {focus}. Use ONLY the facts in the JSON; "
        "copy names exactly; never invent causes, people or numbers. Write every number as digits (2, not two) and "
        "mention at most 4 numbers. Name the most important tasks or projects rather than listing everything. "
        "'Unassigned' means nobody owns the task, so say 'has no owner'. Plain business English, no markdown, "
        "no emojis, no lists, no greeting, no sign-off. Return only the paragraph."
    )
    facts_text = json.dumps(facts, default=str)
    for model in [settings.OPENROUTER_DEFAULT_MODEL, settings.OPENROUTER_FALLBACK_MODEL]:
        if not model:
            continue
        try:
            async with httpx.AsyncClient(timeout=settings.EMAIL_AI_TIMEOUT_SECONDS) as client:
                res = await client.post(
                    f"{settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                             "Content-Type": "application/json", "X-Title": "Project Manager"},
                    json={"model": model, "temperature": 0.2, "max_tokens": 300, "reasoning": {"enabled": False},
                          "messages": [{"role": "system", "content": system},
                                       {"role": "user", "content": facts_text}]},
                )
            if res.status_code != 200:
                print(f"[Digest] {model} HTTP {res.status_code}")
                continue
            text = (res.json()["choices"][0]["message"].get("content") or "").strip()
        except Exception as exc:
            print(f"[Digest] {model} unavailable: {type(exc).__name__}")
            continue
        text = re.sub(r"[*_#`]", "", text).strip()
        spelled = re.search(r"\b(two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|zero)\b", text, re.I)
        if 40 <= len(text) <= 600 and not spelled and "thinking" not in text.lower() and numbers_grounded(text, facts_text):
            return humanize(text)
    return None


def template_summary(kind: str, f: dict) -> str:
    n = f["right_now"]
    if kind == KIND_DAILY:
        y = f["since_yesterday"]
        parts = [f'{n["overdue_tasks"]} of {n["open_tasks"]} open tasks are overdue'
                 + (f' and {n["blocked_tasks"]} blocked' if n["blocked_tasks"] else "") + "."]
        parts.append(f'{y["tasks_completed"]} task(s) were completed since yesterday.')
        if f["due_soon"]:
            parts.append(f'{len(f["due_soon"])} task(s) are due in the next 3 days.')
        return " ".join(parts)
    w = f["week"]
    return (f'This week the team completed {w["tasks_completed"]} task(s) and made {w["redmine_updates"]} Redmine update(s). '
            f'{n["overdue_tasks"]} open task(s) are overdue and {n["projects_needing_attention"]} project(s) need attention.')


# ---------------------------------------------------------------------- #
#  Email rendering                                                        #
# ---------------------------------------------------------------------- #
E = html.escape
BRAND = "#4f46e5"


def _section(title: str, body: str) -> str:
    return (f'<tr><td style="padding:0 28px 20px;">'
            f'<div style="font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#64748b;margin-bottom:8px;">{E(title)}</div>'
            f'{body}</td></tr>')


def _tiles(items: list[tuple[str, object, str]]) -> str:
    cells = "".join(
        f'<td style="padding:10px 8px;border:1px solid #e2e8f0;border-radius:8px;text-align:center;width:{100 // len(items)}%;">'
        f'<div style="font-size:22px;font-weight:700;color:{color};">{E(str(v))}</div>'
        f'<div style="font-size:11px;color:#64748b;margin-top:2px;">{E(label)}</div></td>'
        for label, v, color in items)
    return f'<table role="presentation" width="100%" cellspacing="6" style="border-collapse:separate;"><tr>{cells}</tr></table>'


def _table(headers: list[str], rows: list[list[object]], empty: str) -> str:
    if not rows:
        return f'<p style="margin:0;color:#64748b;font-size:13px;">{E(empty)}</p>'
    head = "".join(f'<th style="text-align:left;padding:7px 10px;font-size:11px;color:#64748b;border-bottom:1px solid #e2e8f0;">{E(h)}</th>' for h in headers)
    body = "".join("<tr>" + "".join(
        f'<td style="padding:7px 10px;font-size:13px;color:#0f172a;border-bottom:1px solid #f1f5f9;vertical-align:top;">{E(str(c))}</td>'
        for c in r) + "</tr>" for r in rows)
    head_row = f"<tr>{head}</tr>" if any(headers) else ""
    return f'<table role="presentation" width="100%" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:8px;border-collapse:separate;">{head_row}{body}</table>'


def _page(banner: str, greeting: str, heading: str, summary: str, sections: str, link: str, link_label: str) -> str:
    return f"""<!doctype html>
<html><body style="margin:0;padding:24px 12px;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" style="max-width:640px;margin:auto;background:#ffffff;border-radius:14px;border:1px solid #e2e8f0;overflow:hidden;">
    <tr><td style="background:{BRAND};padding:10px 28px;color:#ffffff;font-size:12px;font-weight:700;letter-spacing:.05em;">{E(banner)}</td></tr>
    <tr><td style="padding:24px 28px 8px;">
      <div style="font-size:13px;color:#64748b;margin-bottom:10px;">{E(greeting)}</div>
      <h1 style="margin:0 0 12px;font-size:20px;line-height:1.35;color:#0f172a;">{E(heading)}</h1>
      <p style="margin:0 0 18px;font-size:14px;line-height:1.65;color:#334155;">{E(summary)}</p>
    </td></tr>
    {sections}
    <tr><td style="padding:4px 28px 26px;">
      <a href="{E(link, quote=True)}" style="display:inline-block;padding:11px 20px;background:{BRAND};color:#ffffff;text-decoration:none;border-radius:8px;font-size:13px;font-weight:600;">{E(link_label)}</a>
    </td></tr>
    <tr><td style="padding:14px 28px;background:#f8fafc;border-top:1px solid #e2e8f0;font-size:11px;line-height:1.5;color:#94a3b8;">
      Project Manager · AI India Innovations · figures computed from live Redmine data.<br>{E(REASON)}
    </td></tr>
  </table>
</body></html>"""


def render_daily(f: dict, summary: str, greeting: str, date_label: str) -> tuple[str, str, str]:
    n = f["right_now"]
    subject = (f'Daily digest {date_label}: {n["overdue_tasks"]} overdue, '
               f'{len(f["due_soon"])} due soon, {f["since_yesterday"]["tasks_completed"]} completed')
    tiles = _tiles([("Open tasks", n["open_tasks"], "#0f172a"), ("Overdue", n["overdue_tasks"], "#d03b3b"),
                    ("Blocked", n["blocked_tasks"], "#ec835a"), ("Unassigned", n["unassigned_open_tasks"], "#b7791f")])
    y = f["since_yesterday"]
    yesterday = _table(["Since yesterday", ""], [["Tasks completed", y["tasks_completed"]], ["Tasks created", y["tasks_created"]],
                                                 ["Redmine updates", y["redmine_updates"]],
                                                 ["Critical / urgent alerts", f'{y["critical_alerts"]} / {y["urgent_alerts"]}']], "")
    overdue = _table(["Task", "Owner", "Late"], [[t["task"], t["assignee"], f'{t["days_overdue"]} days'] for t in f["overdue"]],
                     "Nothing is overdue.")
    due = _table(["Task", "Owner", "Due"], [[t["task"], t["assignee"], t["due"]] for t in f["due_soon"]],
                 "Nothing is due in the next 3 days.")
    projects = _table(["Project", "Health", "Why"], [[p["name"], p["health"], p["reason"]] for p in f["projects_needing_attention"]],
                      "All active projects are on track.")
    team_rows = [["Free today", ", ".join(f["free_today"]) or "Nobody"],
                 ["Overloaded (6+ open tasks)", ", ".join(f'{p["name"]} ({p["open_tasks"]})' for p in f["overloaded"]) or "Nobody"]]
    sections = (_section("Right now", tiles) + _section("Overdue — oldest first", overdue)
                + _section("Due in the next 3 days", due) + _section("Projects needing attention", projects)
                + _section("Team", _table(["", ""], team_rows, "")) + _section("Activity", yesterday))
    link = f'{settings.APP_BASE_URL.rstrip("/")}/?view=dashboard'
    body = _page(f"DAILY DIGEST  ·  {date_label.upper()}", greeting, "Here is what needs attention today", summary,
                 sections, link, "Open Dashboard")
    text = "\n".join([f"DAILY DIGEST — {date_label}", "", summary, "",
                      f'Open {n["open_tasks"]} · Overdue {n["overdue_tasks"]} · Blocked {n["blocked_tasks"]} · Unassigned {n["unassigned_open_tasks"]}',
                      "", "OVERDUE"] + [f'  - {t["task"]} ({t["assignee"]}, {t["days_overdue"]} d late)' for t in f["overdue"]]
                     + ["", "DUE IN THE NEXT 3 DAYS"] + [f'  - {t["task"]} ({t["assignee"]}, due {t["due"]})' for t in f["due_soon"]]
                     + ["", f"Open dashboard: {link}", "", REASON])
    return subject, body, text


def render_weekly(f: dict, summary: str, greeting: str, range_label: str) -> tuple[str, str, str]:
    w, p, n = f["week"], f["previous_week"], f["right_now"]
    subject = f'Weekly report {range_label}: {w["tasks_completed"]} completed, {n["overdue_tasks"]} overdue'
    tiles = _tiles([("Completed", w["tasks_completed"], "#0ca30c"), ("Created", w["tasks_created"], "#2a78d6"),
                    ("Redmine updates", w["redmine_updates"], "#0f172a"), ("Critical alerts", w["critical_alerts"], "#d03b3b")])
    compare = _table(["This week", "Value", "Change"], [
        ["Tasks completed", w["tasks_completed"], _delta(w["tasks_completed"], p.get("tasks_completed"))],
        ["Tasks created", w["tasks_created"], _delta(w["tasks_created"], p.get("tasks_created"))],
        ["Redmine updates", w["redmine_updates"], _delta(w["redmine_updates"], p.get("redmine_updates"))],
        ["Critical alerts", w["critical_alerts"], _delta(w["critical_alerts"], p.get("critical_alerts"))],
    ], "")
    projects = _table(["Project", "Health", "Open", "Overdue", "Progress"],
                      [[x["name"], x["health"], x["open"], x["overdue"], f'{x["progress_percent"]}%'] for x in f["projects"]],
                      "No active projects.")
    people = _table(["#", "Person", "Done", "Updates", "Open", "Overdue"],
                    [[e["rank"], e["name"], e["completed"], e["updates"], e["open"], e["overdue"]] for e in f["top_contributors"]],
                    "No activity this week.")
    overdue = _table(["Task", "Owner", "Late"], [[t["task"], t["assignee"], f'{t["days_overdue"]} days'] for t in f["overdue"]],
                     "Nothing is overdue.")
    sections = (_section("The week in numbers", tiles) + _section("Compared with the previous week", compare)
                + _section("Active projects", projects) + _section("Top contributors this week", people)
                + _section("Overdue work", overdue)
                + _section("Attachment", '<p style="margin:0;font-size:13px;color:#334155;">The full report is attached as a PDF.</p>'))
    link = f'{settings.APP_BASE_URL.rstrip("/")}/?view=reports'
    body = _page(f"WEEKLY REPORT  ·  {range_label.upper()}", greeting, "How the week went", summary, sections, link, "Open Reports")
    text = "\n".join([f"WEEKLY REPORT — {range_label}", "", summary, "",
                      f'Completed {w["tasks_completed"]} · Created {w["tasks_created"]} · Updates {w["redmine_updates"]}',
                      f'Overdue now {n["overdue_tasks"]} · Blocked {n["blocked_tasks"]}', "",
                      "The full report is attached as a PDF.", f"Open reports: {link}", "", REASON])
    return subject, body, text


# ---------------------------------------------------------------------- #
#  PDF (weekly report attachment)                                         #
# ---------------------------------------------------------------------- #
def _latin(text: object) -> str:
    s = (str(text)
         .replace("—", "-")
         .replace("–", "-")
         .replace("·", "-")
         .replace("→", "->")
         .replace("’", "'")
         .replace("‘", "'")
         .replace("“", '"')
         .replace("”", '"')
         .replace("…", "...")
         .replace("•", "*"))
    return s.encode("latin-1", "replace").decode("latin-1")


def weekly_pdf(f: dict, summary: str, range_label: str, generated: str) -> bytes:
    from fpdf import FPDF

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_fill_color(79, 70, 229)
    pdf.rect(0, 0, 210, 22, style="F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_xy(12, 6)
    pdf.cell(0, 10, _latin(f"Weekly Report - {range_label}"))
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(15, 23, 42)
    pdf.set_xy(12, 28)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5, _latin(f"Project Manager - AI India Innovations - generated {generated} from live Redmine data"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Helvetica", "", 10.5)
    pdf.multi_cell(0, 5.5, _latin(summary), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    def heading(t: str):
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(79, 70, 229)
        pdf.cell(0, 7, _latin(t), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(15, 23, 42)

    def table(headers: list[str], rows: list[list], widths: list[float]):
        if not rows:
            pdf.set_font("Helvetica", "I", 9.5)
            pdf.cell(0, 6, "None.", new_x="LMARGIN", new_y="NEXT")
            return
        from fpdf.fonts import FontFace
        pdf.set_font("Helvetica", "", 9)
        heading_style = FontFace(emphasis="BOLD", color=(71, 85, 105), fill_color=(241, 245, 249))
        with pdf.table(col_widths=widths, text_align="LEFT", line_height=5.5,
                       headings_style=heading_style, borders_layout="HORIZONTAL_LINES") as t:
            hr = t.row()
            for h in headers:
                hr.cell(_latin(h))
            for r in rows:
                row = t.row()
                for c in r:
                    row.cell(_latin(c))

    w, p, n = f["week"], f["previous_week"], f["right_now"]
    heading("The week in numbers")
    table(["Measure", "This week", "Previous week"], [
        ["Tasks completed", w["tasks_completed"], p.get("tasks_completed", "-")],
        ["Tasks created", w["tasks_created"], p.get("tasks_created", "-")],
        ["Redmine updates", w["redmine_updates"], p.get("redmine_updates", "-")],
        ["Critical alerts", w["critical_alerts"], p.get("critical_alerts", "-")],
        ["Urgent alerts", w["urgent_alerts"], "-"],
    ], [80, 50, 50])
    heading("Current state")
    table(["Measure", "Value"], [
        ["Open tasks", n["open_tasks"]], ["Overdue tasks", n["overdue_tasks"]], ["Blocked tasks", n["blocked_tasks"]],
        ["Unassigned open tasks", n["unassigned_open_tasks"]], ["Completion rate", f'{n["completion_rate_percent"]}%'],
        ["Active projects", n["active_projects"]], ["Projects needing attention", n["projects_needing_attention"]],
    ], [100, 80])
    heading("Active projects")
    table(["Project", "Health", "Open", "Done", "Overdue", "Blocked", "Progress"],
          [[x["name"], x["health"], x["open"], x["completed"], x["overdue"], x["blocked"], f'{x["progress_percent"]}%'] for x in f["projects"]],
          [62, 24, 16, 16, 20, 18, 22])
    heading("Top contributors this week")
    table(["Rank", "Person", "Completed", "Updates", "Open", "Overdue", "Score"],
          [[e["rank"], e["name"], e["completed"], e["updates"], e["open"], e["overdue"], e["score"]] for e in f["top_contributors"]],
          [14, 56, 24, 22, 18, 22, 22])
    heading("Overdue work")
    table(["Task", "Project", "Owner", "Days late"],
          [[t["task"], t["project"], t["assignee"], t["days_overdue"]] for t in f["overdue"]], [72, 52, 36, 20])
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(148, 163, 184)
    pdf.multi_cell(0, 4.5, "Ranking score = 5 x tasks completed + 2 x Redmine updates + 1 x open tasks on time.")
    return bytes(pdf.output())


# ---------------------------------------------------------------------- #
#  Sending                                                                #
# ---------------------------------------------------------------------- #
async def _recipients(db: AsyncSession) -> list[AlertEmailRecipient]:
    return (await db.execute(select(AlertEmailRecipient).where(AlertEmailRecipient.is_active == True)
                             .order_by(AlertEmailRecipient.created_at))).scalars().all()


def _message(to_email: str, to_name: str, subject: str, html_body: str, text: str,
             attachment: tuple[str, bytes] | None) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.SMTP_FROM_NAME, email_service.from_address()))
    msg["To"] = formataddr((to_name, to_email)) if to_name else to_email
    msg["Date"] = formatdate(localtime=False, usegmt=True)
    msg["Message-ID"] = make_msgid(domain="company-intel.local")
    msg.set_content(text)
    msg.add_alternative(html_body, subtype="html")
    if attachment:
        msg.add_attachment(attachment[1], maintype="application", subtype="pdf", filename=attachment[0])
    return msg


async def build(db: AsyncSession, kind: str) -> dict:
    """Everything needed to send one scheduled email (shared by all recipients)."""
    now = local_now()
    if kind == KIND_DAILY:
        r = await _overview(db, days=2)  # yesterday + today
        facts = daily_facts(r)
        label = now.strftime("%a %d %b")
    else:
        r = await _overview(db, days=7)
        facts = weekly_facts(r)
        start = (now - timedelta(days=6)).date()
        label = f"{start.strftime('%d %b')} - {now.strftime('%d %b %Y')}"
    summary = await ai_summary(kind, facts) or template_summary(kind, facts)
    out = {"kind": kind, "facts": facts, "summary": summary, "label": label, "attachment": None}
    if kind == KIND_WEEKLY:
        pdf = weekly_pdf(facts, summary, label, now.strftime("%d %b %Y %H:%M"))
        out["attachment"] = (f"weekly-report-{now.strftime('%Y-%m-%d')}.pdf", pdf)
    return out


async def send(db: AsyncSession, kind: str, period_key: str, only_email: str | None = None) -> ScheduledEmailRun:
    """Builds and sends the email to every active recipient (or one address), then records the run."""
    recipients = await _recipients(db)
    if only_email:
        recipients = [r for r in recipients if r.email.lower() == only_email.lower()]
    run = ScheduledEmailRun(kind=kind, period_key=period_key, status="NO_RECIPIENTS", recipient_count=len(recipients))
    if recipients:
        content = await build(db, kind)
        sent, problems = 0, []
        for r in recipients:
            greeting = f"Hi {r.name.split(' (')[0]}," if r.name else "Hello,"
            render = render_daily if kind == KIND_DAILY else render_weekly
            subject, body, text = render(content["facts"], content["summary"], greeting, content["label"])
            result = await email_service.send(_message(r.email, r.name, subject, body, text, content["attachment"]))
            if result.success:
                sent += 1
            else:
                problems.append(f"{r.email}: {result.detail}")
        run.sent_count = sent
        run.status = "SENT" if sent == len(recipients) else ("PARTIAL" if sent else "FAILED")
        run.detail = "; ".join(problems) or None
    db.add(run)
    await db.commit()
    return run


def period_key(kind: str, now: datetime) -> str:
    if kind == KIND_DAILY:
        return now.date().isoformat()
    y, w, _ = now.isocalendar()
    return f"{y}-W{w:02d}"


def is_due(kind: str, config: AlertRecipientConfig, now: datetime) -> bool:
    if not config.email_enabled:
        return False
    start = now.replace(hour=config.digest_hour, minute=0, second=0, microsecond=0)
    if not (start <= now < start + timedelta(hours=SEND_WINDOW_HOURS)):
        return False
    if kind == KIND_DAILY:
        return config.daily_digest_enabled and now.weekday() != 6  # no digest on Sunday
    return config.weekly_report_enabled and now.weekday() == config.weekly_report_weekday


async def run_due(db: AsyncSession) -> list[str]:
    """Called by the background loop every minute. Sends whatever is due and not yet sent."""
    if not email_service.is_configured():
        return []
    config = (await db.execute(select(AlertRecipientConfig).where(AlertRecipientConfig.is_active == True)
                               .limit(1))).scalars().first()
    if config is None:
        return []
    now, done = local_now(), []
    for kind in (KIND_DAILY, KIND_WEEKLY):
        if not is_due(kind, config, now):
            continue
        key = period_key(kind, now)
        exists = (await db.execute(select(ScheduledEmailRun.id).where(
            ScheduledEmailRun.kind == kind, ScheduledEmailRun.period_key == key))).first()
        if exists:
            continue
        run = await send(db, kind, key)
        done.append(f"{kind} {key}: {run.status} ({run.sent_count}/{run.recipient_count})")
    return done


async def last_runs(db: AsyncSession) -> dict:
    out = {}
    for kind in (KIND_DAILY, KIND_WEEKLY):
        run = (await db.execute(select(ScheduledEmailRun).where(ScheduledEmailRun.kind == kind)
                                .order_by(ScheduledEmailRun.created_at.desc()).limit(1))).scalars().first()
        out[kind] = None if run is None else {
            "status": run.status, "sent_count": run.sent_count, "recipient_count": run.recipient_count,
            "at": run.created_at.replace(tzinfo=run.created_at.tzinfo or timezone.utc).isoformat(),
            "manual": run.period_key.startswith("manual"),
        }
    return out
