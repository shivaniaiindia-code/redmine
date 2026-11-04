"use client";

import React, { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import {
  Bell,
  X,
  Check,
  AlertTriangle,
  AlertCircle,
  Clock,
  ExternalLink,
  Loader2,
  Mail,
  CheckCircle2,
  Layers,
} from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export type NotificationCategory = "all" | "critical" | "urgent" | "completed" | "info";

interface DeliveryItem {
  id: string;
  channel: string;
  destination: string;
  status: string;
  delivered_at: string | null;
  error_message: string | null;
}

interface NotificationRecord {
  id: string;
  title: string;
  message: string;
  severity: string;
  entity_type: string;
  entity_id: string | null;
  is_read: boolean;
  created_at: string;
  category: NotificationCategory;
  deep_link: string;
  deliveries: DeliveryItem[];
}

type Summary = Record<NotificationCategory, { total: number; unread: number }>;

interface NotificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNotificationsChanged?: () => void;
  initialCategory?: NotificationCategory;
  highlightId?: string | null;
}

const PILLS: { id: NotificationCategory; label: string; icon: React.ElementType; active: string }[] = [
  { id: "all", label: "All", icon: Bell, active: "bg-slate-900 text-white border-slate-900" },
  { id: "critical", label: "Critical", icon: AlertCircle, active: "bg-red-700 text-white border-red-700" },
  { id: "urgent", label: "Urgent", icon: AlertTriangle, active: "bg-amber-600 text-white border-amber-600" },
  { id: "completed", label: "Completed / Closed", icon: CheckCircle2, active: "bg-emerald-700 text-white border-emerald-700" },
];

const SEVERITY_BADGE: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-700 border-red-200",
  URGENT: "bg-amber-100 text-amber-800 border-amber-200",
  WARNING: "bg-yellow-100 text-yellow-800 border-yellow-200",
  INFO: "bg-blue-100 text-blue-800 border-blue-200",
};

const deliveryLabel = (d: DeliveryItem): { text: string; cls: string } => {
  if (d.channel === "IN_APP") {
    return { text: "In-app", cls: "bg-slate-50 text-slate-600 border-slate-200" };
  }
  switch (d.status) {
    case "SENT":
      return { text: `Email sent → ${d.destination}`, cls: "bg-emerald-50 text-emerald-700 border-emerald-200" };
    case "NOT_CONFIGURED":
      return { text: "Email not sent — email isn't set up yet", cls: "bg-amber-50 text-amber-700 border-amber-200" };
    case "DISABLED":
      return { text: "Email disabled", cls: "bg-slate-100 text-slate-500 border-slate-200" };
    case "FAILED":
      return { text: `Email failed → ${d.destination}`, cls: "bg-red-50 text-red-700 border-red-200" };
    default:
      return { text: `${d.channel}: ${d.status}`, cls: "bg-slate-50 text-slate-500 border-slate-200" };
  }
};

export const NotificationModal: React.FC<NotificationModalProps> = ({
  isOpen,
  onClose,
  onNotificationsChanged,
  initialCategory = "all",
  highlightId = null,
}) => {
  const [category, setCategory] = useState<NotificationCategory>(initialCategory);
  const [notifications, setNotifications] = useState<NotificationRecord[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [recipientCount, setRecipientCount] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ text: string; ok: boolean } | null>(null);

  useEffect(() => {
    if (isOpen) setCategory(initialCategory);
  }, [isOpen, initialCategory]);

  const load = useCallback(async (cat: NotificationCategory) => {
    setIsLoading(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("cip_token") : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const [listRes, summaryRes, configRes] = await Promise.all([
        apiFetch(`${API_BASE_URL}/notifications/?category=${cat}&limit=100`, { headers }),
        apiFetch(`${API_BASE_URL}/notifications/summary`, { headers }),
        apiFetch(`${API_BASE_URL}/admin/email-recipients`, { headers }).catch(() => null),
      ]);

      if (!listRes.ok) throw new Error(`HTTP ${listRes.status}`);
      setNotifications(await listRes.json());

      if (summaryRes.ok) {
        setSummary(await summaryRes.json());
      }

      if (configRes && configRes.ok) {
        const list = await configRes.json();
        if (Array.isArray(list)) {
          setRecipientCount(list.filter((r: any) => r.is_active).length);
        }
      }

      setStatusMsg(null);
    } catch {
      setStatusMsg({ text: "Couldn't load notifications. Please try again in a moment.", ok: false });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) load(category);
  }, [isOpen, category, load]);

  useEffect(() => {
    if (!isOpen || !highlightId || isLoading) return;
    document.getElementById(`notif-${highlightId}`)?.scrollIntoView({ block: "center" });
  }, [isOpen, highlightId, isLoading, notifications]);

  if (!isOpen) return null;

  const refreshAll = async () => {
    await load(category);
    onNotificationsChanged?.();
  };

  const handleScanAlerts = async () => {
    setIsScanning(true);
    setStatusMsg({ text: "Scanning synchronized Redmine tasks and projects...", ok: true });
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("cip_token") : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await apiFetch(`${API_BASE_URL}/notifications/generate-alerts`, {
        method: "POST",
        headers,
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setStatusMsg({ text: `Scan complete: ${data.alerts_generated} new alert(s).`, ok: true });
      await refreshAll();
    } catch {
      setStatusMsg({ text: "Alert scan failed.", ok: false });
    } finally {
      setIsScanning(false);
      setTimeout(() => setStatusMsg((prev) => (prev?.ok ? null : prev)), 5000);
    }
  };

  const handleMarkRead = async (id: string) => {
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("cip_token") : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await apiFetch(`${API_BASE_URL}/notifications/${id}/read`, {
        method: "PATCH",
        headers,
      });
      if (res.ok) {
        setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
        onNotificationsChanged?.();
        const s = await apiFetch(`${API_BASE_URL}/notifications/summary`, { headers }).catch(() => null);
        if (s && s.ok) setSummary(await s.json());
      }
    } catch (err) {
      console.error("Failed to mark notification as read", err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("cip_token") : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await apiFetch(`${API_BASE_URL}/notifications/read-all`, {
        method: "POST",
        headers,
      });
      if (res.ok) {
        setStatusMsg({ text: "All notifications marked as read.", ok: true });
        setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
        await refreshAll();
      } else {
        setStatusMsg({ text: `Failed to mark as read (HTTP ${res.status}).`, ok: false });
      }
    } catch {
      setStatusMsg({ text: "Network error while marking notifications as read.", ok: false });
    } finally {
      setTimeout(() => setStatusMsg((prev) => (prev?.ok ? null : prev)), 4000);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-hidden flex items-end sm:items-center justify-center bg-slate-900/50 backdrop-blur-xs sm:p-4 animate-fadeIn"
      role="dialog"
      aria-modal="true"
      aria-label="Notifications"
    >
      <div className="bg-white rounded-t-3xl sm:rounded-3xl w-full max-w-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col h-[92dvh] sm:h-auto sm:max-h-[90vh] pb-[env(safe-area-inset-bottom)]">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-200 flex items-center justify-between gap-3 bg-slate-50/90">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0 border border-indigo-100/80">
              <Bell className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-bold text-slate-900 text-base">Notifications & Alerts</h3>
                {summary && (
                  <span className="text-[11px] bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded-full font-bold">
                    {summary.all.unread} unread
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 flex flex-wrap items-center gap-1.5 mt-0.5">
                <Mail className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                <span>
                  Emailed to{" "}
                  <strong className="text-slate-700">
                    {recipientCount === null ? "configured recipients" : `${recipientCount} recipient(s)`}
                  </strong>{" "}
                  · manage in Administration
                </span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close notifications"
            className="p-2 shrink-0 rounded-xl text-slate-500 hover:text-slate-700 hover:bg-slate-200/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Unified Controls Toolbar: Filter Pills & Action Buttons (Spacious, No Sandwiched Layout) */}
        <div className="px-4 py-3 bg-slate-50/60 border-b border-slate-200 space-y-2.5">
          {/* Filter Pills with ample padding & no clipping */}
          <div
            className="flex items-center gap-2 overflow-x-auto py-1 [scrollbar-width:none]"
            role="tablist"
          >
            {PILLS.map((p) => {
              const Icon = p.icon;
              const isActive = category === p.id;
              const counts = summary?.[p.id];
              return (
                <button
                  key={p.id}
                  role="tab"
                  aria-selected={isActive}
                  onClick={() => setCategory(p.id)}
                  className={`inline-flex shrink-0 items-center gap-1.5 px-3.5 py-1.5 rounded-full border text-xs font-semibold whitespace-nowrap shadow-xs transition-all ${
                    isActive
                      ? p.active
                      : "bg-white text-slate-600 border-slate-200 hover:border-slate-300 hover:bg-slate-100/80"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5 shrink-0" />
                  <span>{p.label}</span>
                  {counts && (
                    <span
                      className={`ml-1 px-1.5 py-0.5 rounded-full text-[10px] font-bold ${
                        isActive ? "bg-white/20 text-white" : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {counts.total}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Action Buttons Row */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-200/80 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={handleScanAlerts}
                disabled={isScanning}
                className="py-1.5 px-3 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-semibold flex items-center gap-1.5 shadow-xs transition-all disabled:opacity-60"
              >
                {isScanning ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <AlertTriangle className="w-3.5 h-3.5" />
                )}
                <span>Scan for Alerts Now</span>
              </button>
              <button
                onClick={handleMarkAllRead}
                className="py-1.5 px-3 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold flex items-center gap-1.5 shadow-2xs transition-colors"
              >
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span>Mark All Read</span>
              </button>
            </div>

            {summary && (
              <span className="text-[11px] text-slate-400 font-medium hidden sm:inline">
                {summary[category]?.unread || 0} unread in {category === "all" ? "all categories" : category}
              </span>
            )}
          </div>
        </div>

        {/* Status Message */}
        {statusMsg && (
          <div
            className={`p-2.5 px-4 border-b text-xs font-semibold flex items-center justify-between gap-2 ${
              statusMsg.ok
                ? "bg-emerald-50 border-emerald-100 text-emerald-800"
                : "bg-red-50 border-red-100 text-red-700"
            }`}
          >
            <div className="flex items-center gap-2 min-w-0">
              {statusMsg.ok ? (
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
              ) : (
                <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
              )}
              <span className="truncate">{statusMsg.text}</span>
            </div>
            <button
              onClick={() => setStatusMsg(null)}
              className="p-1 hover:bg-black/5 rounded text-slate-500"
              aria-label="Dismiss alert"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Notifications List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {isLoading && notifications.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-400 flex flex-col items-center justify-center gap-2">
              <Loader2 className="w-5 h-5 animate-spin text-indigo-500" />
              <span>Loading alerts...</span>
            </div>
          ) : notifications.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-400">
              No {category === "all" ? "" : PILLS.find((p) => p.id === category)?.label.toLowerCase() + " "}notifications.
            </div>
          ) : (
            notifications.map((n) => (
              <div
                key={n.id}
                id={`notif-${n.id}`}
                className={`p-4 rounded-xl border transition-all ${
                  n.id === highlightId
                    ? "ring-2 ring-indigo-500 bg-indigo-50/40 border-indigo-200"
                    : n.is_read
                    ? "bg-slate-50/60 border-slate-200 text-slate-600"
                    : "bg-white border-slate-300 shadow-xs text-slate-900"
                }`}
              >
                <div className="flex items-start justify-between gap-3 mb-1.5">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span
                      className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border ${
                        SEVERITY_BADGE[n.severity] || "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {n.severity}
                    </span>
                    <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 flex items-center gap-1">
                      <Layers className="w-3 h-3 text-slate-400" /> {n.entity_type}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[11px] text-slate-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {n.created_at}
                    </span>
                    {!n.is_read && (
                      <button
                        onClick={() => handleMarkRead(n.id)}
                        className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 hover:underline ml-1"
                        title="Mark as read"
                      >
                        <Check className="w-3 h-3" />
                        <span className="hidden sm:inline">Mark read</span>
                      </button>
                    )}
                  </div>
                </div>

                <h4 className="text-sm font-bold mb-1 leading-snug">{n.title}</h4>
                <p className="text-xs text-slate-600 whitespace-pre-wrap leading-relaxed">{n.message}</p>

                {/* Delivery Badges & Deep Link */}
                <div className="mt-3 pt-2.5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-1.5">
                    {n.deliveries &&
                      n.deliveries.map((d) => {
                        const lbl = deliveryLabel(d);
                        return (
                          <span
                            key={d.id}
                            className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-md border ${lbl.cls}`}
                            title={d.error_message || undefined}
                          >
                            <Mail className="w-3 h-3" />
                            {lbl.text}
                          </span>
                        );
                      })}
                  </div>

                  {n.deep_link && (
                    <a
                      href={n.deep_link}
                      className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 hover:underline ml-auto"
                    >
                      <span>View details</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
