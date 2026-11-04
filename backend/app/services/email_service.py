"""
SMTP Email Alerting Service.

URGENT and CRITICAL alerts are delivered to the designated administrator
(default: anil.aiindia@gmail.com) by SMTP email. Credentials come from
backend/.env only (never stored in the database, never returned by the API).
"""
import asyncio
import html
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, make_msgid, formatdate

from app.core.config import settings
from app.services.alert_composer import AlertEmailContent


@dataclass
class EmailResult:
    success: bool
    status: str              # SENT | FAILED | NOT_CONFIGURED
    detail: str = ""
    retryable: bool = False  # temporary failure (network, server busy) — worth another attempt


# Footer line explaining why this person got the email
REASON_LIST = "You receive this because you are on the platform's email recipient list (Administration → Email Recipients)."
REASON_ASSIGNEE = "You receive this because this task is assigned to you in Redmine."
REASON_MANAGER = "You receive this because you are the project manager for this project."

SEVERITY_COLORS = {
    "CRITICAL": "#dc2626",
    "URGENT": "#d97706",
    "WARNING": "#ca8a04",
    "INFO": "#2563eb",
}


class EmailService:
    # ------------------------------------------------------------------ #
    #  Configuration                                                       #
    # ------------------------------------------------------------------ #
    @staticmethod
    def from_address() -> str:
        return settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME

    @staticmethod
    def is_configured() -> bool:
        return bool(settings.SMTP_HOST and settings.SMTP_USERNAME and settings.SMTP_PASSWORD)

    @staticmethod
    def alert_severities() -> set[str]:
        return {s.strip().upper() for s in settings.EMAIL_ALERT_SEVERITIES.split(",") if s.strip()}

    @staticmethod
    def config_summary() -> dict:
        """Safe, secret-free view of the SMTP configuration for the Admin UI."""
        mode = "SSL" if settings.SMTP_USE_SSL else ("STARTTLS" if settings.SMTP_USE_STARTTLS else "PLAIN")
        return {
            "configured": EmailService.is_configured(),
            "host": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "username": settings.SMTP_USERNAME,
            "from_email": EmailService.from_address(),
            "from_name": settings.SMTP_FROM_NAME,
            "security": mode,
            "password_set": bool(settings.SMTP_PASSWORD),
            "alert_severities": sorted(EmailService.alert_severities()),
        }

    # ------------------------------------------------------------------ #
    #  Message construction                                                #
    # ------------------------------------------------------------------ #
    @staticmethod
    def build_alert_message(
        to_email: str,
        to_name: str,
        title: str,
        message: str,
        severity: str,
        entity_type: str,
        created_at_label: str,
        deep_link: str,
    ) -> EmailMessage:
        """Simple message (test emails, programmatic calls) rendered with the structured template."""
        content = AlertEmailContent(
            subject=title[:250], severity=severity, category="info",
            entity_type=entity_type, headline=title, summary=message, raised_at=created_at_label,
            details=[("Raised", created_at_label)],
        )
        return EmailService.build_structured_message(to_email, to_name, content, deep_link)

    @staticmethod
    def build_structured_message(to_email: str, to_name: str, c: AlertEmailContent, deep_link: str,
                                 reason: str = REASON_LIST) -> EmailMessage:
        msg = EmailMessage()
        msg["Subject"] = c.subject
        msg["From"] = formataddr((settings.SMTP_FROM_NAME, EmailService.from_address()))
        msg["To"] = formataddr((to_name, to_email)) if to_name else to_email
        msg["Date"] = formatdate(localtime=False, usegmt=True)
        msg["Message-ID"] = make_msgid(domain="company-intel.local")
        msg["X-Priority"] = "1" if c.severity == "CRITICAL" else ("2" if c.severity == "URGENT" else "3")

        label = "COMPLETED" if c.category == "completed" else c.severity
        # ---------- plain text ----------
        lines = [f"{label} — {c.headline}", "", c.summary, ""]
        if c.details:
            lines.append("KEY DETAILS")
            lines += [f"  {k}: {v}" for k, v in c.details]
            lines.append("")
        if c.context:
            lines.append("CONTEXT")
            lines += [f"  - {x}" for x in c.context]
            lines.append("")
        if c.impact:
            lines += ["WHY IT MATTERS", f"  {c.impact}", ""]
        if c.actions:
            lines.append("RECOMMENDED NEXT STEPS")
            lines += [f"  {i}. {x}" for i, x in enumerate(c.actions, 1)]
            lines.append("")
        lines += [f"Open in dashboard: {deep_link}", "",
                  "— Project Manager · AI India Innovations · automated alert from live project data", reason]
        msg.set_content("\n".join(lines))

        # ---------- HTML ----------
        e = html.escape
        color = "#059669" if c.category == "completed" else SEVERITY_COLORS.get(c.severity, SEVERITY_COLORS["INFO"])
        greeting = f"Hi {e(to_name.split(' (')[0])}," if to_name else "Hello,"

        def section(title: str, body: str) -> str:
            return (f'<tr><td style="padding:0 28px 18px;">'
                    f'<div style="font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#64748b;margin-bottom:8px;">{e(title)}</div>'
                    f'{body}</td></tr>')

        details_html = ""
        if c.details:
            rows = "".join(
                f'<tr><td style="padding:8px 12px;border-bottom:1px solid #eef2f7;color:#64748b;font-size:13px;width:38%;vertical-align:top;">{e(k)}</td>'
                f'<td style="padding:8px 12px;border-bottom:1px solid #eef2f7;color:#0f172a;font-size:13px;font-weight:600;">{e(v)}</td></tr>'
                for k, v in c.details)
            details_html = section("Key details",
                f'<table role="presentation" width="100%" cellspacing="0" style="border:1px solid #e2e8f0;border-radius:8px;border-collapse:separate;">{rows}</table>')
        context_html = section("Context", '<ul style="margin:0;padding-left:20px;color:#334155;font-size:14px;line-height:1.6;">'
                               + "".join(f"<li>{e(x)}</li>" for x in c.context) + "</ul>") if c.context else ""
        impact_html = section("Why it matters",
            f'<p style="margin:0;padding:12px 14px;background:#f8fafc;border-left:3px solid {color};color:#334155;font-size:14px;line-height:1.6;">{e(c.impact)}</p>') if c.impact else ""
        actions_html = section("Recommended next steps", '<ol style="margin:0;padding-left:20px;color:#334155;font-size:14px;line-height:1.7;">'
                               + "".join(f"<li>{e(x)}</li>" for x in c.actions) + "</ol>") if c.actions else ""
        ai_note = " Summary written by AI from verified Redmine records; key details are exact system values." if c.source == "llm" else ""

        html_body = f"""<!doctype html>
<html><body style="margin:0;padding:24px 12px;background:#f1f5f9;font-family:'Segoe UI',Arial,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" style="max-width:620px;margin:auto;background:#ffffff;border-radius:14px;border:1px solid #e2e8f0;overflow:hidden;">
    <tr><td style="background:{color};padding:10px 28px;color:#ffffff;font-size:12px;font-weight:700;letter-spacing:.05em;">
      {e(label)} ALERT &nbsp;·&nbsp; {e(c.entity_type)}
    </td></tr>
    <tr><td style="padding:24px 28px 8px;">
      <div style="font-size:13px;color:#64748b;margin-bottom:10px;">{greeting}</div>
      <h1 style="margin:0 0 12px;font-size:20px;line-height:1.35;color:#0f172a;">{e(c.headline)}</h1>
      <p style="margin:0 0 18px;font-size:14px;line-height:1.65;color:#334155;">{e(c.summary)}</p>
    </td></tr>
    {details_html}{context_html}{impact_html}{actions_html}
    <tr><td style="padding:4px 28px 26px;">
      <a href="{e(deep_link, quote=True)}" style="display:inline-block;padding:11px 20px;background:#4f46e5;color:#ffffff;text-decoration:none;border-radius:8px;font-size:13px;font-weight:600;">Open in Dashboard</a>
    </td></tr>
    <tr><td style="padding:14px 28px;background:#f8fafc;border-top:1px solid #e2e8f0;font-size:11px;line-height:1.5;color:#94a3b8;">
      Project Manager · AI India Innovations · raised {e(c.raised_at)}.{ai_note}<br>
      {e(reason)}
    </td></tr>
  </table>
</body></html>"""
        msg.add_alternative(html_body, subtype="html")
        return msg

    # ------------------------------------------------------------------ #
    #  Transport                                                           #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _send_sync(msg: EmailMessage) -> None:
        host, port, timeout = settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_TIMEOUT_SECONDS
        context = ssl.create_default_context()
        if settings.SMTP_USE_SSL:
            server: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=timeout, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=timeout)
        try:
            server.ehlo()
            if settings.SMTP_USE_STARTTLS and not settings.SMTP_USE_SSL:
                server.starttls(context=context)
                server.ehlo()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        finally:
            try:
                server.quit()
            except Exception:
                pass

    async def send(self, msg: EmailMessage) -> EmailResult:
        """Sends a prepared message without blocking the event loop."""
        # User-facing details stay plain English; technical causes go to the server log only.
        if not self.is_configured():
            return EmailResult(False, "NOT_CONFIGURED",
                               "Email sending is not set up yet. Ask your technical administrator to connect the sender account.")
        try:
            await asyncio.to_thread(self._send_sync, msg)
            return EmailResult(True, "SENT", "Email delivered to the mail server.")
        except smtplib.SMTPAuthenticationError as exc:
            print(f"[Email] authentication failed: {exc.smtp_code} {exc.smtp_error!r}")
            return EmailResult(False, "FAILED", "The sender email account rejected the sign-in. Its password may have changed.",
                               retryable=True)
        except smtplib.SMTPRecipientsRefused as exc:
            print(f"[Email] recipient refused: {exc!r}")
            return EmailResult(False, "FAILED", "The recipient address was rejected. Check that it is spelled correctly.")
        except Exception as exc:  # network errors, TLS errors
            print(f"[Email] send failed: {type(exc).__name__}: {exc}")
            return EmailResult(False, "FAILED", "Could not reach the mail server.", retryable=True)

    async def send_structured(self, to_email: str, to_name: str, content: AlertEmailContent, deep_link: str,
                              reason: str = REASON_LIST) -> EmailResult:
        return await self.send(self.build_structured_message(to_email, to_name, content, deep_link, reason))

    async def send_alert(
        self,
        to_email: str,
        to_name: str,
        title: str,
        message: str,
        severity: str,
        entity_type: str,
        created_at_label: str,
        deep_link: str,
    ) -> EmailResult:
        msg = self.build_alert_message(
            to_email, to_name, title, message, severity, entity_type, created_at_label, deep_link
        )
        return await self.send(msg)


email_service = EmailService()
