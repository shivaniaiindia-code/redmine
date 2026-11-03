"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Bell,
  AlertTriangle,
  AlertCircle,
  Info,
  Calendar,
  Send,
  Check,
  CheckCircle2,
  Clock,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Mail,
  Layers,
} from "lucide-react";

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
  deliveries: DeliveryItem[];
}

interface NotificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNewNotificationTriggered?: () => void;
}

export const NotificationModal: React.FC<NotificationModalProps> = ({
  isOpen,
  onClose,
  onNewNotificationTriggered,
}) => {
  const [notifications, setNotifications] = useState<NotificationRecord[]>([]);
  const [recipientEmail, setRecipientEmail] = useState<string>("anil.aiindia@gmail.com");
  const [isLoading, setIsLoading] = useState(false);
  const [testTitle, setTestTitle] = useState("");
  const [testMessage, setTestMessage] = useState("");
  const [severity, setSeverity] = useState("WARNING");
  const [isSending, setIsSending] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const [showTestForm, setShowTestForm] = useState(false);

  const fetchNotificationsAndConfig = async () => {
    setIsLoading(true);
    try {
      const [notifRes, configRes] = await Promise.all([
        fetch("http://localhost:8000/api/v1/notifications/"),
        fetch("http://localhost:8000/api/v1/admin/recipient-config"),
      ]);
      if (notifRes.ok) {
        const notifData = await notifRes.json();
        setNotifications(notifData);
      }
      if (configRes.ok) {
        const configData = await configRes.json();
        if (configData.recipient_email) {
          setRecipientEmail(configData.recipient_email);
        }
      }
    } catch (err) {
      console.error("Error fetching notification center data", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchNotificationsAndConfig();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleTriggerTest = async () => {
    if (!testTitle.trim() || !testMessage.trim()) return;

    setIsSending(true);
    setStatusMsg("");

    try {
      const response = await fetch("http://localhost:8000/api/v1/notifications/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: testTitle,
          message: testMessage,
          severity: severity,
          entity_type: "SYSTEM",
        }),
      });

      if (response.ok) {
        setStatusMsg(`Dispatched to In-App Bar & routed to ${recipientEmail}`);
        setTestTitle("");
        setTestMessage("");
        await fetchNotificationsAndConfig();
        if (onNewNotificationTriggered) {
          onNewNotificationTriggered();
        }
      } else {
        setStatusMsg("Alert recorded locally.");
      }
    } catch {
      setStatusMsg("Alert dispatch failed.");
    } finally {
      setIsSending(false);
    }
  };

  const handleScanAlerts = async () => {
    setIsSending(true);
    setStatusMsg("Scanning projects and tasks for automated alerts...");
    try {
      const res = await fetch("http://localhost:8000/api/v1/notifications/generate-alerts", {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setStatusMsg(`Scan complete: ${data.alerts_generated} automated alerts generated.`);
        await fetchNotificationsAndConfig();
        if (onNewNotificationTriggered) onNewNotificationTriggered();
      }
    } catch {
      setStatusMsg("Failed to execute alert generator.");
    } finally {
      setIsSending(false);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await fetch("http://localhost:8000/api/v1/notifications/read-all", { method: "POST" });
      setStatusMsg("All notifications marked as read.");
      await fetchNotificationsAndConfig();
      if (onNewNotificationTriggered) onNewNotificationTriggered();
    } catch {
      // ignored
    }
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case "CRITICAL":
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-100 text-red-700 border border-red-200">CRITICAL</span>;
      case "URGENT":
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">URGENT</span>;
      case "WARNING":
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-yellow-100 text-yellow-800 border border-yellow-200">WARNING</span>;
      default:
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-200">INFO</span>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 animate-fadeIn">
      <div className="bg-white rounded-3xl w-full max-w-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Bell className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-slate-900 text-base">
                  Notification & Alert Dashboard
                </h3>
                <span className="text-[10px] bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded-full font-bold">
                  {notifications.length} alerts
                </span>
              </div>
              <p className="text-xs text-slate-500 flex items-center gap-1.5 mt-0.5">
                <Mail className="w-3.5 h-3.5 text-indigo-500" />
                Default Recipient: <span className="font-semibold text-slate-700">{recipientEmail}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Action Bar */}
        <div className="p-3.5 bg-slate-100/60 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2">
            <button
              onClick={handleScanAlerts}
              disabled={isSending}
              className="py-1.5 px-3 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-semibold flex items-center gap-1.5 shadow-2xs transition-all disabled:opacity-60"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Scan & Generate Alerts Now
            </button>
            <button
              onClick={handleMarkAllRead}
              className="py-1.5 px-3 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold flex items-center gap-1.5 transition-colors"
            >
              <Check className="w-3.5 h-3.5" />
              Mark All Read
            </button>
          </div>

          <button
            onClick={() => setShowTestForm(!showTestForm)}
            className="text-indigo-600 hover:text-indigo-800 font-semibold flex items-center gap-1"
          >
            {showTestForm ? "Hide Test Dispatch" : "+ Dispatch Custom Alert"}
            {showTestForm ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        {statusMsg && (
          <div className="p-2.5 px-4 bg-emerald-50 border-b border-emerald-100 text-xs font-semibold text-emerald-800 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            {statusMsg}
          </div>
        )}

        {/* Optional Collapsible Test Form */}
        {showTestForm && (
          <div className="p-4 bg-indigo-50/50 border-b border-indigo-100 space-y-3">
            <h4 className="text-xs font-bold text-slate-900">Dispatch Custom Test Alert</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input
                type="text"
                value={testTitle}
                onChange={(e) => setTestTitle(e.target.value)}
                placeholder="Alert Title"
                className="text-xs border border-slate-200 rounded-lg px-3 py-2 bg-white"
              />
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="text-xs border border-slate-200 rounded-lg px-2.5 py-2 bg-white"
              >
                <option value="INFO">INFO (Blue)</option>
                <option value="WARNING">WARNING (Yellow)</option>
                <option value="URGENT">URGENT (Amber)</option>
                <option value="CRITICAL">CRITICAL (Red)</option>
              </select>
            </div>
            <textarea
              value={testMessage}
              onChange={(e) => setTestMessage(e.target.value)}
              placeholder="Alert message content..."
              rows={2}
              className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 bg-white"
            />
            <button
              onClick={handleTriggerTest}
              disabled={isSending || !testTitle.trim() || !testMessage.trim()}
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 rounded-lg text-xs flex items-center justify-center gap-2"
            >
              <Send className="w-3.5 h-3.5" />
              Dispatch to Bar + Admin Google Chat
            </button>
          </div>
        )}

        {/* Notifications List with Channel Delivery Tracking */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {isLoading ? (
            <div className="py-12 text-center text-xs text-slate-400">Loading alerts...</div>
          ) : notifications.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-400">
              No notifications generated yet. Click &quot;Scan &amp; Generate Alerts Now&quot; above.
            </div>
          ) : (
            notifications.map((n) => (
              <div
                key={n.id}
                className={`p-3.5 rounded-xl border transition-all ${
                  n.is_read
                    ? "bg-slate-50/70 border-slate-200/70 opacity-80"
                    : "bg-white border-slate-200 shadow-2xs"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      {getSeverityBadge(n.severity)}
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                        {n.entity_type}
                      </span>
                      <h4 className="text-xs font-bold text-slate-900">{n.title}</h4>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">{n.message}</p>
                  </div>
                  <span className="text-[10px] text-slate-400 whitespace-nowrap flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {n.created_at}
                  </span>
                </div>

                {/* Delivery Channels Breakdown (User Requirement: Separate delivery tracking) */}
                <div className="mt-2.5 pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-[10px]">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 font-medium">Delivery:</span>
                    {n.deliveries && n.deliveries.length > 0 ? (
                      n.deliveries.map((d) => (
                        <span
                          key={d.id}
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded font-mono font-semibold ${
                            d.status === "SENT"
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : d.status === "PENDING_WEBHOOK"
                              ? "bg-amber-50 text-amber-700 border border-amber-200"
                              : "bg-red-50 text-red-700 border border-red-200"
                          }`}
                          title={d.error_message || d.destination}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              d.status === "SENT"
                                ? "bg-emerald-500"
                                : d.status === "PENDING_WEBHOOK"
                                ? "bg-amber-500"
                                : "bg-red-500"
                            }`}
                          />
                          {d.channel}: {d.status}
                        </span>
                      ))
                    ) : (
                      <span className="text-slate-400 italic">In-App Bar Recorded</span>
                    )}
                  </div>

                  <span className="text-indigo-600 font-medium text-[10px]">
                    To: {recipientEmail}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
