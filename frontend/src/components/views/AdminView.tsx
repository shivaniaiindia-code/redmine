"use client";

import React, { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import {
  Sliders,
  RefreshCw,
  Bot,
  BellRing,
  Mail,
  Save,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  PlugZap,
  Send,
  KeyRound,
} from "lucide-react";
import { EmailRecipientsCard, type EmailRecipient } from "./EmailRecipientsCard";
import { ActiveUsersCard } from "./ActiveUsersCard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface Recipient {
  id: string;
  label: string;
  recipient_email: string;
  recipient_name: string;
  in_app_enabled: boolean;
  email_enabled: boolean;
  is_active: boolean;
}

interface Integrations {
  redmine: {
    url: string;
    api_key_configured: boolean;
    api_key_hint: string | null;
    sync_interval_minutes: number;
    last_synced_at: string | null;
    records_synced: number;
    sync_status: string;
  };
  smtp: {
    configured: boolean;
    host: string;
    port: number;
    username: string;
    from_email: string;
    from_name: string;
    security: string;
    password_set: boolean;
    alert_severities: string[];
  };
  openrouter: {
    configured: boolean;
    api_key_hint: string | null;
    base_url: string;
    default_model: string;
    fallback_model: string;
  };
  recipient: Recipient;
  email_recipients: EmailRecipient[];
  config_source: string;
}

type Result = { ok: boolean; text: string } | null;

const StatusBadge: React.FC<{ ok: boolean; okText: string; badText: string }> = ({ ok, okText, badText }) => (
  <span
    className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
      ok ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-amber-50 text-amber-700 border-amber-200"
    }`}
  >
    {ok ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
    {ok ? okText : badText}
  </span>
);

const Row: React.FC<{ label: string; value: React.ReactNode; mono?: boolean }> = ({ label, value, mono }) => (
  <div className="flex justify-between gap-3">
    <span className="text-slate-500 shrink-0">{label}</span>
    <span className={`font-semibold text-slate-800 text-right min-w-0 ${mono ? "font-mono break-all" : "break-words"}`}>{value}</span>
  </div>
);

const ResultLine: React.FC<{ result: Result }> = ({ result }) =>
  result ? (
    <div
      className={`p-2.5 rounded-lg text-xs font-medium border ${
        result.ok ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-red-50 border-red-200 text-red-700"
      }`}
    >
      {result.text}
    </div>
  ) : null;

const btn =
  "inline-flex items-center justify-center gap-2 py-2 px-4 rounded-lg text-xs font-semibold shadow-xs transition-all disabled:opacity-60";

export const AdminView: React.FC<{ onOpenSignUp?: () => void; isSuperAdmin?: boolean }> = ({ onOpenSignUp, isSuperAdmin = false }) => {
  const [data, setData] = useState<Integrations | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const [redmineResult, setRedmineResult] = useState<Result>(null);
  const [smtpResult, setSmtpResult] = useState<Result>(null);
  const [recipientResult, setRecipientResult] = useState<Result>(null);
  const [aiResult, setAiResult] = useState<Result>(null);

  const [inAppToggle, setInAppToggle] = useState(true);
  const [emailToggle, setEmailToggle] = useState(true);

  const load = useCallback(async () => {
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("cip_token") : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await apiFetch(`${API_BASE_URL}/admin/integrations`, { headers });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const d: Integrations = await res.json();
      setData(d);
      setLoadError(null);
      setInAppToggle(d.recipient.in_app_enabled);
      setEmailToggle(d.recipient.email_enabled);
    } catch {
      setLoadError("Couldn't load administration settings. Please try again in a moment.");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key);
    try {
      await fn();
    } finally {
      setBusy(null);
    }
  };

  const postJson = async (path: string) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("cip_token") : null;
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await apiFetch(`${API_BASE_URL}${path}`, { method: "POST", headers });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  };

  const testRedmine = () =>
    run("redmine-test", async () => {
      try {
        const r = await postJson("/admin/redmine/test");
        setRedmineResult(
          r.success
            ? { ok: true, text: `Connected to ${r.base_url} in ${r.elapsed_ms} ms.` }
            : { ok: false, text: `Connection failed: ${r.error || `HTTP ${r.status_code}`}` }
        );
      } catch (e) {
        setRedmineResult({ ok: false, text: `Request failed: ${(e as Error).message}` });
      }
    });

  const syncRedmine = () =>
    run("redmine-sync", async () => {
      setRedmineResult({ ok: true, text: "Synchronizing projects, memberships and issues from Redmine..." });
      try {
        const r = await postJson("/redmine/sync/trigger");
        const s = r.summary || {};
        setRedmineResult({
          ok: true,
          text: `Sync complete: ${s.projects_synced ?? 0} projects, ${s.tasks_synced ?? 0} tasks synchronized.`,
        });
        await load();
      } catch (e) {
        setRedmineResult({ ok: false, text: `Sync failed: ${(e as Error).message}` });
      }
    });

  const testSmtp = () =>
    run("smtp-test", async () => {
      try {
        const r = await postJson("/admin/smtp/test");
        setSmtpResult(
          r.success
            ? { ok: true, text: `Test email accepted for ${r.results.length} recipient(s): ${r.results.map((x: { recipient: string }) => x.recipient).join(", ")}.` }
            : { ok: false, text: r.detail }
        );
      } catch (e) {
        setSmtpResult({ ok: false, text: `Request failed: ${(e as Error).message}` });
      }
    });

  const testAi = () =>
    run("ai-test", async () => {
      try {
        const r = await postJson("/admin/openrouter/test");
        setAiResult(r.success ? { ok: true, text: `Assistant is working (replied in ${r.elapsed_ms} ms).` } : { ok: false, text: r.detail });
      } catch (e) {
        setAiResult({ ok: false, text: `Request failed: ${(e as Error).message}` });
      }
    });

  const scanAlerts = () =>
    run("scan", async () => {
      try {
        const r = await postJson("/notifications/generate-alerts");
        setRecipientResult({ ok: true, text: `Alert scan complete: ${r.alerts_generated} new alert(s) generated.` });
      } catch (e) {
        setRecipientResult({ ok: false, text: `Alert scan failed: ${(e as Error).message}` });
      }
    });

  const saveRecipient = (e: React.FormEvent) => {
    e.preventDefault();
    run("save", async () => {
      try {
        const token = typeof window !== "undefined" ? localStorage.getItem("cip_token") : null;
        const headers: Record<string, string> = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await apiFetch(`${API_BASE_URL}/admin/recipient-config`, {
          method: "PUT",
          headers,
          body: JSON.stringify({
            in_app_enabled: inAppToggle,
            email_enabled: emailToggle,
          }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setRecipientResult({ ok: true, text: "Channel settings saved." });
        await load();
      } catch (err) {
        setRecipientResult({ ok: false, text: `Save failed: ${(err as Error).message}` });
      }
    });
  };

  return (
    <div className="space-y-4 sm:space-y-6 max-w-5xl mx-auto">
      <div className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200/80 shadow-xs">
        <h1 className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">
          <Sliders className="w-5 h-5 sm:w-6 sm:h-6 text-indigo-600 shrink-0" />
          Administration & Integrations
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Redmine sync, email alerts, alert routing and the AI assistant. Sign-in details are kept securely on the server and are never shown here.
        </p>
      </div>

      {loadError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 font-medium flex items-center justify-between gap-3">
          {loadError}
          <button onClick={load} className={`${btn} bg-white border border-red-200 text-red-700 shadow-none`}>
            Retry
          </button>
        </div>
      )}

      {data && <ActiveUsersCard onOpenSignUp={onOpenSignUp} isSuperAdmin={isSuperAdmin} />}

      {data && <EmailRecipientsCard onChanged={load} />}

      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
          {/* Card 1 — Redmine */}
          <section className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-4 flex flex-col">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <RefreshCw className="w-5 h-5 text-indigo-600" /> Redmine Sync
              </h2>
              <StatusBadge ok={data.redmine.api_key_configured && !!data.redmine.url} okText="Connected" badText="Not connected" />
            </div>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 space-y-1.5 text-xs">
              <Row label="Instance" value={data.redmine.url || "not set"} mono />
              <Row label="Auto-sync" value={`Every ${data.redmine.sync_interval_minutes} min`} />
              <Row label="Last sync" value={data.redmine.last_synced_at ?? "Never"} />
              <Row label="Records in last sync" value={`${data.redmine.records_synced}`} />
            </div>
            <ResultLine result={redmineResult} />
            <div className="grid grid-cols-2 gap-2 mt-auto">
              <button onClick={testRedmine} disabled={!!busy} className={`${btn} bg-white border border-slate-200 text-slate-700 hover:bg-slate-50`}>
                {busy === "redmine-test" ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlugZap className="w-4 h-4" />}
                Test Connection
              </button>
              <button onClick={syncRedmine} disabled={!!busy} className={`${btn} bg-indigo-600 hover:bg-indigo-700 text-white`}>
                <RefreshCw className={`w-4 h-4 ${busy === "redmine-sync" ? "animate-spin" : ""}`} />
                Sync Now
              </button>
            </div>
          </section>

          {/* Card 2 — SMTP */}
          <section className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-4 flex flex-col">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Mail className="w-5 h-5 text-indigo-600" /> Email Alerts
              </h2>
              <StatusBadge ok={data.smtp.configured} okText="Ready" badText="Not set up" />
            </div>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 space-y-1.5 text-xs">
              <Row label="Sends from" value={data.smtp.username || "not set up"} />
              <Row label="Emails sent for" value="Urgent + critical alerts (more per recipient)" />
              <Row label="Recipients" value={`${data.email_recipients.filter((r) => r.is_active).length} active (see Email Recipients)`} />
            </div>
            {!data.smtp.configured && (
              <div className="p-3 rounded-lg border border-amber-200 bg-amber-50 text-[11px] text-amber-900 space-y-1">
                <p className="font-semibold flex items-center gap-1">
                  <KeyRound className="w-3.5 h-3.5" /> Email sending isn&apos;t set up yet.
                </p>
                <p>Ask your technical administrator to connect the sender email account. Alerts still appear in the notification bar meanwhile.</p>
              </div>
            )}
            <ResultLine result={smtpResult} />
            <button onClick={testSmtp} disabled={!!busy} className={`${btn} mt-auto bg-indigo-600 hover:bg-indigo-700 text-white`}>
              {busy === "smtp-test" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Send Test Email to All
            </button>
          </section>

          {/* Card 3 — Recipient & routing */}
          <section className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-4 flex flex-col">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <BellRing className="w-5 h-5 text-amber-500" /> Alert Channels
              </h2>
            </div>
            <form onSubmit={saveRecipient} className="space-y-3">
              <div className="flex flex-col gap-2 text-xs text-slate-700">
                <label className="flex flex-wrap items-center gap-x-2 gap-y-0.5 py-1 cursor-pointer">
                  <input type="checkbox" checked={inAppToggle} onChange={(e) => setInAppToggle(e.target.checked)} className="rounded text-indigo-600" />
                  <span className="font-semibold">In-app notification bar</span>
                  <span className="text-slate-400">(all alerts)</span>
                </label>
                <label className="flex flex-wrap items-center gap-x-2 gap-y-0.5 py-1 cursor-pointer">
                  <input type="checkbox" checked={emailToggle} onChange={(e) => setEmailToggle(e.target.checked)} className="rounded text-indigo-600" />
                  <span className="font-semibold">Email</span>
                  <span className="text-slate-400">(to the recipients below)</span>
                </label>
              </div>
              <ResultLine result={recipientResult} />
              <div className="grid grid-cols-2 gap-2">
                <button type="button" onClick={scanAlerts} disabled={!!busy} className={`${btn} bg-white border border-slate-200 text-slate-700 hover:bg-slate-50`}>
                  {busy === "scan" ? <Loader2 className="w-4 h-4 animate-spin" /> : <BellRing className="w-4 h-4" />}
                  Scan Alerts
                </button>
                <button type="submit" disabled={!!busy} className={`${btn} bg-indigo-600 hover:bg-indigo-700 text-white`}>
                  {busy === "save" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  Save
                </button>
              </div>
            </form>
          </section>

          {/* Card 4 — OpenRouter */}
          <section className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-4 flex flex-col">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Bot className="w-5 h-5 text-indigo-600" /> AI Assistant
              </h2>
              <StatusBadge ok={data.openrouter.configured} okText="Ready" badText="Not set up" />
            </div>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 space-y-1.5 text-xs">
              <Row label="Answers from" value="Live project data" />
              <Row label="Also writes" value="Alert email summaries" />
            </div>
            <p className="text-[11px] text-slate-500">
              Questions about assignments and project status are answered straight from your live project data. If the assistant is ever unavailable, it shows the key figures instead.
            </p>
            <ResultLine result={aiResult} />
            <button onClick={testAi} disabled={!!busy} className={`${btn} mt-auto bg-indigo-600 hover:bg-indigo-700 text-white`}>
              {busy === "ai-test" ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlugZap className="w-4 h-4" />}
              Test Assistant
            </button>
          </section>
        </div>
      )}
    </div>
  );
};
