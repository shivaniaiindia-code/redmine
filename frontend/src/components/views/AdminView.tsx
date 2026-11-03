"use client";

import React, { useState, useEffect } from "react";
import {
  Sliders,
  RefreshCw,
  Bot,
  BellRing,
  MessageSquare,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Mail,
  User,
  ExternalLink,
  Save,
  Check,
} from "lucide-react";

interface RecipientConfig {
  id: string;
  label: string;
  recipient_email: string;
  recipient_name: string;
  google_chat_webhook_url: string | null;
  in_app_enabled: boolean;
  google_chat_enabled: boolean;
  email_enabled: boolean;
  is_active: boolean;
}

export const AdminView: React.FC = () => {
  const [redmineStatus, setRedmineStatus] = useState<any>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isScanningAlerts, setIsScanningAlerts] = useState(false);
  const [statusNotice, setStatusNotice] = useState<string | null>(null);

  // Recipient config state
  const [recipientConfig, setRecipientConfig] = useState<RecipientConfig | null>(null);
  const [emailInput, setEmailInput] = useState("");
  const [nameInput, setNameInput] = useState("");
  const [webhookInput, setWebhookInput] = useState("");
  const [inAppToggle, setInAppToggle] = useState(true);
  const [googleChatToggle, setGoogleChatToggle] = useState(true);
  const [emailToggle, setEmailToggle] = useState(true);
  const [isSavingConfig, setIsSavingConfig] = useState(false);
  const [configSuccessMsg, setConfigSuccessMsg] = useState<string | null>(null);

  const fetchRedmineStatus = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/redmine/status");
      if (res.ok) {
        const data = await res.json();
        setRedmineStatus(data);
      }
    } catch (err) {
      console.error("Failed to fetch redmine status", err);
    }
  };

  const fetchRecipientConfig = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/admin/recipient-config");
      if (res.ok) {
        const data: RecipientConfig = await res.json();
        setRecipientConfig(data);
        setEmailInput(data.recipient_email || "anil.aiindia@gmail.com");
        setNameInput(data.recipient_name || "Anil (Administrator)");
        setWebhookInput(data.google_chat_webhook_url || "");
        setInAppToggle(data.in_app_enabled ?? true);
        setGoogleChatToggle(data.google_chat_enabled ?? true);
        setEmailToggle(data.email_enabled ?? true);
      }
    } catch (err) {
      console.error("Failed to fetch recipient config", err);
    }
  };

  useEffect(() => {
    fetchRedmineStatus();
    fetchRecipientConfig();
  }, []);

  const handleSaveRecipientConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingConfig(true);
    setConfigSuccessMsg(null);

    try {
      const res = await fetch("http://localhost:8000/api/v1/admin/recipient-config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          recipient_email: emailInput.trim(),
          recipient_name: nameInput.trim(),
          google_chat_webhook_url: webhookInput.trim() || null,
          in_app_enabled: inAppToggle,
          google_chat_enabled: googleChatToggle,
          email_enabled: emailToggle,
        }),
      });

      if (res.ok) {
        const updated = await res.json();
        setRecipientConfig(updated);
        setConfigSuccessMsg("Default recipient and channel settings updated successfully!");
        setTimeout(() => setConfigSuccessMsg(null), 5000);
      } else {
        setStatusNotice("Failed to update recipient settings.");
      }
    } catch (err) {
      setStatusNotice("Error connecting to server to save settings.");
    } finally {
      setIsSavingConfig(false);
    }
  };

  const handleSyncRedmine = async () => {
    setIsSyncing(true);
    setStatusNotice("Connecting to Redmine API (https://redmine.aiindia.ai)...");
    try {
      const res = await fetch("http://localhost:8000/api/v1/redmine/sync/trigger", {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setStatusNotice(
          `Redmine Delta Sync Completed: ${data.summary?.projects_synced ?? 0} projects and ${data.summary?.tasks_synced ?? 0} tasks synced. Automated alerts generated.`
        );
        await fetchRedmineStatus();
      } else {
        setStatusNotice("Sync failed. Check Redmine configuration or network.");
      }
    } catch {
      setStatusNotice("Error connecting to backend server.");
    } finally {
      setIsSyncing(false);
      setTimeout(() => setStatusNotice(null), 6000);
    }
  };

  const handleScanAlerts = async () => {
    setIsScanningAlerts(true);
    setStatusNotice("Scanning active projects and tasks for overdue deadlines and blockers...");
    try {
      const res = await fetch("http://localhost:8000/api/v1/notifications/generate-alerts", {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setStatusNotice(
          `Alert Scan Complete: ${data.alerts_generated} new alerts generated and routed to ${recipientConfig?.recipient_email || "anil.aiindia@gmail.com"}.`
        );
      }
    } catch {
      setStatusNotice("Failed to execute alert generator.");
    } finally {
      setIsScanningAlerts(false);
      setTimeout(() => setStatusNotice(null), 6000);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
        <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <Sliders className="w-6 h-6 text-indigo-600" />
          System Administration & Integrations
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Single-Admin Operational Mode: Redmine delta synchronization, automated alert triggers, configurable designated recipient, and OpenRouter AI.
        </p>
      </div>

      {statusNotice && (
        <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-lg text-sm text-indigo-800 font-medium">
          {statusNotice}
        </div>
      )}

      {/* Recipient Configuration Card (User Request: All alerts reach one designated account, configurable from admin settings) */}
      <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-100 pb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Mail className="w-5 h-5 text-indigo-600" />
              Default Alert Recipient & Dispatch Routing
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              100% of system-generated notifications (Employee, Project, Task, Team, Company) route to this designated account.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <CheckCircle2 className="w-3.5 h-3.5" /> Single-Recipient Routing Active
            </span>
          </div>
        </div>

        {configSuccessMsg && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs font-semibold text-emerald-800 flex items-center gap-2">
            <Check className="w-4 h-4 text-emerald-600" />
            {configSuccessMsg}
          </div>
        )}

        <form onSubmit={handleSaveRecipientConfig} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Designated Recipient Email <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <input
                  type="email"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  placeholder="e.g. anil.aiindia@gmail.com"
                  required
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2.5 bg-slate-50 focus:bg-white focus:outline-hidden focus:border-indigo-500 font-medium text-slate-800"
                />
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                All automated alerts across the company are dispatched to this account.
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Recipient Name / Display Title
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  placeholder="e.g. Anil (Administrator)"
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2.5 bg-slate-50 focus:bg-white focus:outline-hidden focus:border-indigo-500 font-medium text-slate-800"
                />
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Used in notification headers, Google Chat cards, and email alerts.
              </p>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Google Chat Webhook URL (External Mirroring Channel)
            </label>
            <input
              type="text"
              value={webhookInput}
              onChange={(e) => setWebhookInput(e.target.value)}
              placeholder="https://chat.googleapis.com/v1/spaces/.../messages?key=...&token=..."
              className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2.5 bg-slate-50 focus:bg-white focus:outline-hidden focus:border-indigo-500 font-mono text-slate-800"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              {webhookInput ? (
                <span className="text-emerald-600 font-medium">✓ Webhook configured. External alerts will mirror here.</span>
              ) : (
                <span className="text-amber-600 font-medium">Optional: Leave blank to log delivery status as PENDING_WEBHOOK without dropping alerts.</span>
              )}
            </p>
          </div>

          {/* Delivery Channels Toggle */}
          <div className="border border-slate-200 rounded-lg p-3 bg-slate-50/60 space-y-2">
            <span className="text-xs font-bold text-slate-700 block">Dispatch Channels (Separately Tracked):</span>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={inAppToggle}
                  onChange={(e) => setInAppToggle(e.target.checked)}
                  className="rounded text-indigo-600 focus:ring-indigo-500"
                />
                <span className="font-semibold">In-App Notification Bar</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-mono">SENT</span>
              </label>

              <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={googleChatToggle}
                  onChange={(e) => setGoogleChatToggle(e.target.checked)}
                  className="rounded text-indigo-600 focus:ring-indigo-500"
                />
                <span className="font-semibold">Google Chat Mirror</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${webhookInput ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                  {webhookInput ? "LIVE" : "PENDING"}
                </span>
              </label>

              <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={emailToggle}
                  onChange={(e) => setEmailToggle(e.target.checked)}
                  className="rounded text-indigo-600 focus:ring-indigo-500"
                />
                <span className="font-semibold">Direct Email Routing</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-800 font-mono">READY</span>
              </label>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={isSavingConfig}
              className="inline-flex items-center gap-2 py-2 px-5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-all disabled:opacity-60"
            >
              <Save className="w-3.5 h-3.5" />
              {isSavingConfig ? "Saving Settings..." : "Save Recipient Settings"}
            </button>
          </div>
        </form>
      </div>

      {/* Grid of Admin Control Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Card 1: Redmine Integration */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <RefreshCw className="w-5 h-5 text-indigo-600" />
              Redmine Sync Engine
            </h2>
            <span
              className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                redmineStatus?.connected
                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                  : "bg-amber-50 text-amber-700 border border-amber-200"
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5" /> {redmineStatus?.connected ? "Connected" : "Standby"}
            </span>
          </div>

          <p className="text-xs text-slate-600">
            Bidirectional delta synchronizer targeting live projects, issues, journals, and assignees.
          </p>

          <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-500">Instance URL:</span>
              <span className="font-mono font-semibold text-slate-800">https://redmine.aiindia.ai</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Last Synced:</span>
              <span className="font-semibold text-slate-800">{redmineStatus?.last_synced_at || "Never"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Auto-Interval:</span>
              <span className="font-semibold text-slate-800">Every 5 minutes</span>
            </div>
          </div>

          <button
            onClick={handleSyncRedmine}
            disabled={isSyncing}
            className="w-full inline-flex items-center justify-center gap-2 py-2 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-semibold shadow-xs transition-all disabled:opacity-60"
          >
            <RefreshCw className={`w-4 h-4 ${isSyncing ? "animate-spin" : ""}`} />
            {isSyncing ? "Synchronizing Live..." : "Trigger Redmine Sync Now"}
          </button>
        </div>

        {/* Card 2: Automated Alert Generation Engine */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <BellRing className="w-5 h-5 text-amber-500" />
              Automated Alert Generation
            </h2>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <CheckCircle2 className="w-3.5 h-3.5" /> Automated Active
            </span>
          </div>

          <p className="text-xs text-slate-600">
            Continuously monitors project milestones, overdue tasks, blockers, and workload thresholds.
          </p>

          <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-500">Target Recipient:</span>
              <span className="font-semibold text-indigo-700 font-mono">
                {recipientConfig?.recipient_email || "anil.aiindia@gmail.com"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Dispatch Channels:</span>
              <span className="font-semibold text-slate-800">System Notification Bar + Google Chat</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Deduplication:</span>
              <span className="font-semibold text-emerald-600">Enabled (Prevents spam)</span>
            </div>
          </div>

          <button
            onClick={handleScanAlerts}
            disabled={isScanningAlerts}
            className="w-full inline-flex items-center justify-center gap-2 py-2 px-4 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-semibold shadow-xs transition-all disabled:opacity-60"
          >
            <BellRing className={`w-4 h-4 ${isScanningAlerts ? "animate-spin" : ""}`} />
            {isScanningAlerts ? "Scanning Engine..." : "Scan & Generate Alerts Now"}
          </button>
        </div>

        {/* Card 3: OpenRouter AI Grounding */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Bot className="w-5 h-5 text-indigo-600" />
              OpenRouter AI Gateway
            </h2>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
              <ShieldCheck className="w-3.5 h-3.5" /> Grounded
            </span>
          </div>

          <p className="text-xs text-slate-600">
            Natural language executive queries answered strictly through deterministic database tool execution. Zero hallucination.
          </p>

          <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-500">Active Model:</span>
              <span className="font-mono font-bold text-indigo-600">Qwen3.5-Flash (qwen3.5-flash-02-23)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Gateway:</span>
              <span className="font-semibold text-slate-800">OpenRouter Multi-Model Router</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Citation Engine:</span>
              <span className="font-semibold text-emerald-600">100% Deterministic Grounding</span>
            </div>
          </div>
        </div>

        {/* Card 4: Google Chat Webhook Mirroring */}
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-emerald-600" />
              Admin Google Chat Mirroring
            </h2>
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <CheckCircle2 className="w-3.5 h-3.5" /> Dual-Dispatch Invariant
            </span>
          </div>

          <p className="text-xs text-slate-600">
            Mandatory architectural rule: 100% of notifications received in the System Notification Bar mirror 1:1 to Admin Google Chat in Cards v2 schema.
          </p>

          <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-500">Payload Schema:</span>
              <span className="font-mono font-semibold text-slate-800">Google Chat Cards v2</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Dual-Dispatch:</span>
              <span className="font-semibold text-emerald-600">Active</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Recipient Mirror:</span>
              <span className="font-mono text-slate-800 font-semibold">{recipientConfig?.recipient_email || "anil.aiindia@gmail.com"}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
