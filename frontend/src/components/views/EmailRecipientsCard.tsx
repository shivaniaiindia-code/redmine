"use client";

import React, { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Users, UserPlus, Trash2, Send, Loader2, Pause, Play, CheckCircle2, AlertTriangle } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export type NotifyScope = "ALL" | "URGENT_CRITICAL";

export interface EmailRecipient {
  id: string;
  email: string;
  name: string;
  notify_scope: NotifyScope;
  is_active: boolean;
}

const SCOPE_LABEL: Record<NotifyScope, string> = {
  ALL: "All notifications",
  URGENT_CRITICAL: "Urgent & critical only",
};

type Result = { ok: boolean; text: string } | null;

const errorText = async (res: Response) => {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return body.detail[0]?.msg?.replace("value is not a valid email address: ", "") ?? `HTTP ${res.status}`;
  } catch {
    /* fall through */
  }
  return `HTTP ${res.status}`;
};

export const EmailRecipientsCard: React.FC<{ onChanged?: () => void }> = ({ onChanged }) => {
  const [recipients, setRecipients] = useState<EmailRecipient[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [result, setResult] = useState<Result>(null);

  const [newEmail, setNewEmail] = useState("");
  const [newName, setNewName] = useState("");
  const [newScope, setNewScope] = useState<NotifyScope>("ALL");

  const load = useCallback(async () => {
    try {
      const res = await apiFetch(`${API_BASE_URL}/admin/email-recipients`);
      if (!res.ok) throw new Error(await errorText(res));
      setRecipients(await res.json());
    } catch (e) {
      setResult({ ok: false, text: `Could not load recipients: ${(e as Error).message}` });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const act = async (id: string, fn: () => Promise<void>) => {
    setBusyId(id);
    try {
      await fn();
    } finally {
      setBusyId(null);
    }
  };

  const changed = async () => {
    await load();
    onChanged?.();
  };

  const addRecipient = (e: React.FormEvent) => {
    e.preventDefault();
    act("new", async () => {
      const res = await apiFetch(`${API_BASE_URL}/admin/email-recipients`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: newEmail.trim(), name: newName.trim(), notify_scope: newScope }),
      });
      if (!res.ok) {
        setResult({ ok: false, text: await errorText(res) });
        return;
      }
      const r: EmailRecipient = await res.json();
      setResult({ ok: true, text: `${r.email} added — will receive ${SCOPE_LABEL[r.notify_scope].toLowerCase()}.` });
      setNewEmail("");
      setNewName("");
      setNewScope("ALL");
      await changed();
    });
  };

  const patch = (r: EmailRecipient, body: Partial<Pick<EmailRecipient, "notify_scope" | "is_active">>) =>
    act(r.id, async () => {
      const res = await apiFetch(`${API_BASE_URL}/admin/email-recipients/${r.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setResult(res.ok ? { ok: true, text: `${r.email} updated.` } : { ok: false, text: await errorText(res) });
      await changed();
    });

  const remove = (r: EmailRecipient) => {
    if (!window.confirm(`Remove ${r.email} from email notifications?`)) return;
    act(r.id, async () => {
      const res = await apiFetch(`${API_BASE_URL}/admin/email-recipients/${r.id}`, { method: "DELETE" });
      setResult(res.ok ? { ok: true, text: `${r.email} removed.` } : { ok: false, text: await errorText(res) });
      await changed();
    });
  };

  const sendTest = (r: EmailRecipient) =>
    act(r.id, async () => {
      const res = await apiFetch(`${API_BASE_URL}/admin/email-recipients/${r.id}/test`, { method: "POST" });
      if (!res.ok) {
        setResult({ ok: false, text: await errorText(res) });
        return;
      }
      const d = await res.json();
      setResult(d.success ? { ok: true, text: `Test email accepted for ${r.email}. Ask them to check their inbox.` } : { ok: false, text: d.detail });
    });

  const activeCount = recipients.filter((r) => r.is_active).length;

  return (
    <section className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Users className="w-5 h-5 text-indigo-600" /> Email Recipients
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Everyone listed here receives platform notifications by email — choose all notifications (same as the notification bar) or
            only urgent &amp; critical alerts.
          </p>
        </div>
        <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-2.5 py-1 rounded-full whitespace-nowrap">
          {activeCount} active
        </span>
      </div>

      {/* Add form */}
      <form onSubmit={addRecipient} className="grid grid-cols-1 md:grid-cols-[2fr_1.5fr_1.5fr_auto] gap-2">
        <input
          type="email"
          required
          aria-label="Email address"
          placeholder="name@company.com"
          value={newEmail}
          onChange={(e) => setNewEmail(e.target.value)}
          className="text-xs border border-slate-300 rounded-lg px-3 py-2.5 md:py-2 bg-slate-50 focus:bg-white focus:outline-hidden focus:border-indigo-500"
        />
        <input
          type="text"
          aria-label="Name"
          placeholder="Name (optional)"
          maxLength={150}
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          className="text-xs border border-slate-300 rounded-lg px-3 py-2 bg-slate-50 focus:bg-white focus:outline-hidden focus:border-indigo-500"
        />
        <select
          aria-label="Notifications to receive"
          value={newScope}
          onChange={(e) => setNewScope(e.target.value as NotifyScope)}
          className="text-xs border border-slate-300 rounded-lg px-2.5 py-2 bg-slate-50"
        >
          <option value="ALL">{SCOPE_LABEL.ALL}</option>
          <option value="URGENT_CRITICAL">{SCOPE_LABEL.URGENT_CRITICAL}</option>
        </select>
        <button
          type="submit"
          disabled={busyId !== null || !newEmail.trim()}
          className="inline-flex items-center justify-center gap-1.5 py-2.5 md:py-2 px-4 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-60"
        >
          {busyId === "new" ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
          Add
        </button>
      </form>

      {result && (
        <div
          className={`p-2.5 rounded-lg text-xs font-medium border flex items-center gap-2 ${
            result.ok ? "bg-emerald-50 border-emerald-200 text-emerald-800" : "bg-red-50 border-red-200 text-red-700"
          }`}
        >
          {result.ok ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertTriangle className="w-4 h-4 shrink-0" />}
          {result.text}
        </div>
      )}

      {/* List */}
      <div className="divide-y divide-slate-100 border border-slate-200 rounded-lg">
        {loading ? (
          <div className="p-4 text-xs text-slate-400 text-center">Loading recipients...</div>
        ) : recipients.length === 0 ? (
          <div className="p-4 text-xs text-slate-400 text-center">No email recipients yet. Add one above.</div>
        ) : (
          recipients.map((r) => (
            <div key={r.id} className={`p-3 flex flex-col md:flex-row md:items-center gap-2 md:gap-3 ${r.is_active ? "" : "opacity-60"}`}>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-slate-900 truncate">
                  {r.name}
                  {!r.is_active && <span className="ml-2 text-[10px] font-bold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">PAUSED</span>}
                </p>
                <p className="text-[11px] text-slate-500 font-mono truncate">{r.email}</p>
              </div>
              <select
                aria-label={`Notifications for ${r.email}`}
                value={r.notify_scope}
                disabled={busyId !== null}
                onChange={(e) => patch(r, { notify_scope: e.target.value as NotifyScope })}
                className="w-full md:w-auto text-xs border border-slate-200 rounded-lg px-2 py-2 md:py-1.5 bg-white"
              >
                <option value="ALL">{SCOPE_LABEL.ALL}</option>
                <option value="URGENT_CRITICAL">{SCOPE_LABEL.URGENT_CRITICAL}</option>
              </select>
              <div className="grid grid-cols-[1fr_1fr_auto] md:flex items-center gap-1.5">
                <button
                  onClick={() => sendTest(r)}
                  disabled={busyId !== null || !r.is_active}
                  title="Send a test email"
                  className="inline-flex items-center justify-center gap-1 px-2.5 py-2 md:py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  {busyId === r.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  Test
                </button>
                <button
                  onClick={() => patch(r, { is_active: !r.is_active })}
                  disabled={busyId !== null}
                  title={r.is_active ? "Pause emails" : "Resume emails"}
                  className="inline-flex items-center justify-center gap-1 px-2.5 py-2 md:py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  {r.is_active ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                  {r.is_active ? "Pause" : "Resume"}
                </button>
                <button
                  onClick={() => remove(r)}
                  disabled={busyId !== null}
                  title="Remove recipient"
                  aria-label={`Remove ${r.email}`}
                  className="inline-flex items-center justify-center px-3 md:px-2 py-2 md:py-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-50"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
};
