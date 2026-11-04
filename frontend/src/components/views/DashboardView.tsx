"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import {
  FolderKanban,
  ListTodo,
  AlarmClock,
  AlertTriangle,
  BellRing,
  Mail,
  RefreshCw,
  ShieldCheck,
  Ban,
  UserX,
  CalendarClock,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  Minus,
  Trophy,
  Coffee,
} from "lucide-react";
import type { NotificationCategory } from "@/components/NotificationModal";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/* Validated palette (dataviz reference, light). Status colours are reserved for state and always labelled. */
const C = {
  blue: "#2a78d6",
  orange: "#eb6834",
  aqua: "#1baf7a",
  good: "#0ca30c",
  warning: "#fab219",
  serious: "#ec835a",
  critical: "#d03b3b",
  neutral: "#94a3b8",
  grid: "#e2e8f0",
  axis: "#64748b",
  surface: "#ffffff",
};

const PERIODS: { label: string; days: number | null }[] = [
  { label: "Last 7 days", days: 7 },
  { label: "Last 30 days", days: 30 },
  { label: "Last 90 days", days: 90 },
  { label: "All time", days: null },
];

type Stats = Record<string, number>;
interface Person {
  employee_id: string; name: string; job_title: string; rank: number; score: number;
  open_tasks: number; open_on_time: number; overdue: number; max_days_overdue: number;
  completed_in_period: number; updates_in_period: number; completed_all_time: number;
  availability: "Free" | "Light" | "Busy" | "Overloaded";
  weekly_activity: { week: string; count: number }[];
}
interface Overview {
  as_of: string;
  visibility?: "company" | "assigned_projects";
  period: { days: number | null; start: string; end: string; granularity: "day" | "week" | "month"; label: string };
  period_stats: Stats;
  prev_period_stats: Stats | null;
  timeline: { bucket: string; created: number; completed: number; updates: number; alerts: number }[];
  upcoming_deadlines: { id: string; title: string; project: string | null; due_date: string; days_left: number; assignee: string | null; priority: string }[];
  kpis: Stats;
  projects: { id: string; name: string; status: string; health_status: string; health_reason: string | null; total_tasks: number; completed_tasks: number; open_on_time: number; overdue_tasks: number; team_size: number }[];
  top_overdue: { id: string; title: string; project: string | null; assignee: string | null; days_overdue: number; priority: string }[];
  people: {
    employees: Person[];
    availability_counts: { label: Person["availability"]; count: number; range: string }[];
    free_today: string[];
    score_formula: string;
  };
}
interface SyncStatus { connected: boolean; last_synced_at: string; syncing_now?: boolean; next_sync_at?: string | null; auto_sync_interval_seconds?: number }
interface DashboardProps {
  onNavigate: (view: string) => void;
  onOpenNotifications: (category: NotificationCategory) => void;
  refreshKey: number;
}

const axisProps = { tick: { fill: C.axis, fontSize: 11 }, axisLine: { stroke: C.grid }, tickLine: false } as const;
const tooltipProps = {
  cursor: { fill: "rgba(148,163,184,0.12)" },
  contentStyle: { borderRadius: 10, border: "1px solid #e2e8f0", fontSize: 12, boxShadow: "0 4px 16px rgba(15,23,42,.08)" },
  labelStyle: { color: "#0f172a", fontWeight: 600 },
} as const;
const legendProps = { iconType: "circle" as const, iconSize: 8, wrapperStyle: { fontSize: 11, color: "#475569" } };

const parseUtc = (s?: string | null) => (s ? new Date(s.replace(" UTC", "Z").replace(" ", "T")) : null);
const fmtDur = (s: number) => (s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${Math.floor(s / 3600)}h`);
const fmtBucket = (iso: string, g: string) => {
  const d = new Date(`${iso}T00:00:00`);
  return g === "month" ? d.toLocaleDateString(undefined, { month: "short", year: "2-digit" }) : d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
};

const HEALTH: Record<string, { label: string; icon: React.ElementType; chip: string }> = {
  ON_TRACK: { label: "On track", icon: ShieldCheck, chip: "bg-green-50 text-green-800 border-green-200" },
  AT_RISK: { label: "At risk", icon: AlertTriangle, chip: "bg-orange-50 text-orange-800 border-orange-200" },
  BLOCKED: { label: "Blocked", icon: Ban, chip: "bg-red-50 text-red-800 border-red-200" },
  OFF_TRACK: { label: "Off track", icon: AlertTriangle, chip: "bg-red-50 text-red-800 border-red-200" },
};

const AVAIL: Record<Person["availability"], { color: string; chip: string; hint: string }> = {
  Free: { color: C.good, chip: "bg-green-50 text-green-800 border-green-200", hint: "no open tasks" },
  Light: { color: C.blue, chip: "bg-blue-50 text-blue-800 border-blue-200", hint: "1–2 open tasks" },
  Busy: { color: C.warning, chip: "bg-amber-50 text-amber-800 border-amber-200", hint: "3–5 open tasks" },
  Overloaded: { color: C.critical, chip: "bg-red-50 text-red-800 border-red-200", hint: "6+ open tasks" },
};

/* ---------- small building blocks ---------- */
const Panel: React.FC<{ title: string; subtitle?: string; action?: React.ReactNode; className?: string; children: React.ReactNode }> = ({
  title, subtitle, action, className = "", children,
}) => (
  <section className={`bg-white rounded-2xl border border-slate-200/80 shadow-2xs p-3.5 sm:p-4 flex flex-col min-w-0 ${className}`}>
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
        {subtitle && <p className="text-[11px] text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
      {action}
    </div>
    <div className="mt-3 flex-1 min-h-0">{children}</div>
  </section>
);

const LinkBtn: React.FC<{ onClick: () => void; children: React.ReactNode }> = ({ onClick, children }) => (
  <button onClick={onClick} className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 whitespace-nowrap">
    {children} <ArrowRight className="w-3 h-3" />
  </button>
);

const Empty: React.FC<{ text: string }> = ({ text }) => (
  <div className="h-full min-h-24 flex items-center justify-center text-xs text-slate-400 text-center px-4">{text}</div>
);

const Delta: React.FC<{ cur: number; prev: number | undefined; goodWhenUp?: boolean }> = ({ cur, prev, goodWhenUp = true }) => {
  if (prev === undefined) return null;
  const d = cur - prev;
  if (d === 0) return <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold text-slate-400"><Minus className="w-3 h-3" />same</span>;
  const up = d > 0;
  const good = up === goodWhenUp;
  return (
    <span className={`inline-flex items-center gap-0.5 text-[10px] font-semibold ${good ? "text-green-700" : "text-red-700"}`} title={`Previous period: ${prev}`}>
      {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
      {up ? "+" : ""}{d}
    </span>
  );
};

const Sparkline: React.FC<{ data: { week: string; count: number }[] }> = ({ data }) => {
  const max = Math.max(1, ...data.map((d) => d.count));
  return (
    <div className="flex items-end gap-[2px] h-6" aria-label={`8-week activity: ${data.map((d) => d.count).join(", ")}`}>
      {data.map((d) => (
        <div
          key={d.week}
          title={`Week of ${fmtBucket(d.week, "day")}: ${d.count} completed/updates`}
          className="w-[6px] rounded-sm"
          style={{ height: `${Math.max(8, (d.count / max) * 100)}%`, background: d.count ? C.blue : "#e2e8f0" }}
        />
      ))}
    </div>
  );
};

/* ---------- main view ---------- */
export const DashboardView: React.FC<DashboardProps> = ({ onNavigate, onOpenNotifications, refreshKey }) => {
  const [days, setDays] = useState<number | null>(7);
  const [periodRestored, setPeriodRestored] = useState(false);
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sync, setSync] = useState<SyncStatus | null>(null);
  const [now, setNow] = useState(Date.now());
  const [showAllPeople, setShowAllPeople] = useState(false);
  const reqId = useRef(0);

  const load = useCallback(async () => {
    const id = ++reqId.current; // ignore responses from superseded requests (fast period switching)
    setLoading(true);
    try {
      const q = `include_inactive=true&weeks=12${days ? `&days=${days}` : ""}`;
      const res = await apiFetch(`${API_BASE_URL}/reports/overview?${q}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json: Overview = await res.json();
      if (id !== reqId.current) return;
      setData(json);
      setError(null);
    } catch {
      if (id === reqId.current) setError("Couldn't load the dashboard. Please check your connection and try again.");
    } finally {
      if (id === reqId.current) setLoading(false);
    }
  }, [days]);

  // Restore the viewer's last period after mount (keeps server and client markup identical)
  useEffect(() => {
    try {
      const v = window.localStorage.getItem("cip.dashboard.days");
      if (v !== null) setDays(v === "all" ? null : Number(v) || 7);
    } catch {
      /* storage unavailable */
    }
    setPeriodRestored(true);
  }, []);

  useEffect(() => {
    if (periodRestored) load();
  }, [load, refreshKey, periodRestored]);

  useEffect(() => {
    if (!periodRestored) return;
    try {
      window.localStorage.setItem("cip.dashboard.days", days === null ? "all" : String(days));
    } catch {
      /* storage unavailable */
    }
  }, [days, periodRestored]);

  // Live sync status: poll every 10 s; reload data whenever a new Redmine sync lands.
  useEffect(() => {
    let lastSeen: string | null = null;
    let alive = true;
    const poll = async () => {
      try {
        const r = await apiFetch(`${API_BASE_URL}/redmine/status`, { cache: "no-store" });
        if (!r.ok) return;
        const s: SyncStatus = await r.json();
        if (!alive) return;
        setSync(s);
        if (lastSeen && s.last_synced_at !== lastSeen) load();
        lastSeen = s.last_synced_at;
      } catch {
        /* backend offline — the error banner covers it */
      }
    };
    poll();
    const pollId = window.setInterval(poll, 10000);
    const tick = window.setInterval(() => setNow(Date.now()), 1000);
    return () => {
      alive = false;
      window.clearInterval(pollId);
      window.clearInterval(tick);
    };
  }, [load]);

  const lastSync = parseUtc(sync?.last_synced_at);
  const syncAgo = lastSync ? Math.max(0, Math.round((now - lastSync.getTime()) / 1000)) : null;
  const nextSync = parseUtc(sync?.next_sync_at);
  const nextIn = nextSync ? Math.max(0, Math.round((nextSync.getTime() - now) / 1000)) : null;
  const syncStale = syncAgo !== null && sync?.auto_sync_interval_seconds ? syncAgo > sync.auto_sync_interval_seconds * 3 : false;

  const k = data?.kpis;
  const ps = data?.period_stats;
  const prev = data?.prev_period_stats ?? undefined;
  const periodLabel = data?.period.label ?? PERIODS.find((p) => p.days === days)?.label ?? "";
  const timeline = data?.timeline ?? [];
  const hasTimeline = timeline.some((t) => t.created || t.completed || t.updates);
  const activeProjects = (data?.projects ?? []).filter((p) => p.status === "ACTIVE");
  const people = data?.people;
  const ranked = people?.employees ?? [];
  const peopleShown = showAllPeople ? ranked : ranked.slice(0, 8);
  const totalPeople = ranked.length || 1;
  const maxScore = Math.max(1, ranked[0]?.score ?? 1);
  const busiest = [...ranked].sort((a, b) => b.open_tasks - a.open_tasks).filter((p) => p.open_tasks > 0).slice(0, 3);
  const dim = loading ? "opacity-60" : "";

  const nowTiles = k ? [
    { icon: FolderKanban, label: "Active projects", value: k.active_projects, note: `${k.at_risk_projects} need attention`, tone: k.at_risk_projects ? "warn" : "ok", go: () => onNavigate("projects") },
    { icon: ListTodo, label: "Open tasks", value: k.open_tasks, note: `${k.total_tasks} tasks in total`, tone: "ok", go: () => onNavigate("tasks") },
    { icon: AlarmClock, label: "Overdue", value: k.overdue_tasks, note: `avg ${k.avg_days_overdue} days late`, tone: k.overdue_tasks ? "bad" : "ok", go: () => onNavigate("tasks") },
    { icon: UserX, label: "Unassigned", value: k.unassigned_open_tasks, note: "open tasks without owner", tone: k.unassigned_open_tasks ? "warn" : "ok", go: () => onNavigate("tasks") },
  ] : [];

  const periodTiles = ps ? [
    { label: "Tasks created", key: "tasks_created", up: true },
    { label: "Tasks completed", key: "tasks_completed", up: true },
    { label: "Redmine updates", key: "redmine_updates", up: true },
    { label: "Critical + urgent alerts", key: "_alerts", up: false },
    { label: "Alert emails sent", key: "emails_sent", up: true },
  ].map((t) => ({
    ...t,
    value: t.key === "_alerts" ? ps.alerts_critical + ps.alerts_urgent : ps[t.key],
    prev: prev ? (t.key === "_alerts" ? prev.alerts_critical + prev.alerts_urgent : prev[t.key]) : undefined,
  })) : [];

  return (
    <div className="space-y-4 sm:space-y-5">
      {/* Header */}
      <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-3">
        <div>
          <h2 className="text-lg sm:text-xl font-bold text-slate-900 tracking-tight">Operations overview</h2>
          <p className="text-xs text-slate-500 mt-1">
            AI India Innovations · live from Redmine
            {data?.visibility === "assigned_projects" && (
              <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 text-[10px] font-semibold align-middle">
                Showing your assigned projects only
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex items-center gap-2 px-3 py-2 rounded-xl border border-slate-200 bg-white text-[11px] font-medium text-slate-600 min-w-0 flex-1 sm:flex-none" role="status">
            <span className={`w-2 h-2 shrink-0 rounded-full ${sync?.syncing_now ? "bg-indigo-500 animate-pulse" : syncStale || (sync && !sync.connected) ? "bg-amber-500" : "bg-green-600"}`} />
            {sync === null ? "Checking sync…" : sync.syncing_now ? "Syncing with Redmine…" : (
              <span className="truncate">
                <span className="hidden sm:inline">Redmine </span>{sync.connected ? "connected" : "unreachable"} · synced {syncAgo !== null ? `${fmtDur(syncAgo)} ago` : "never"}
                {nextIn !== null && <span className="hidden sm:inline">{` · next in ${fmtDur(nextIn)}`}</span>}
              </span>
            )}
          </div>
          <button onClick={load} disabled={loading} className="p-2.5 sm:p-2 shrink-0 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 disabled:opacity-60" aria-label="Refresh dashboard">
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-indigo-600" : ""}`} />
          </button>
        </div>
      </div>

      {error && <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">{error}</div>}
      {!data && loading && <div className="py-24 text-center text-sm text-slate-400">Loading live operations data…</div>}

      {data && k && ps && people && (
        <>
          {/* RIGHT NOW */}
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">Right now</p>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-3">
              {nowTiles.map((t) => {
                const Icon = t.icon;
                return (
                  <button key={t.label} onClick={t.go} className="text-left bg-white rounded-2xl border border-slate-200/80 shadow-2xs p-3 sm:p-4 hover:border-indigo-300 hover:shadow-sm active:scale-[0.98] transition-all group flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-3 min-w-0">
                    <span className={`w-9 h-9 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center shrink-0 ${t.tone === "bad" ? "bg-red-50 text-red-600" : t.tone === "warn" ? "bg-orange-50 text-orange-600" : "bg-indigo-50 text-indigo-600"}`}>
                      <Icon className="w-5 h-5" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-col sm:flex-row sm:items-baseline sm:gap-2">
                        <span className="text-2xl font-bold text-slate-900 tabular-nums leading-tight">{t.value}</span>
                        <span className="text-xs font-semibold text-slate-700 truncate">{t.label}</span>
                      </div>
                      <div className="text-[11px] text-slate-500 truncate">{t.note}</div>
                    </div>
                    <ArrowRight className="hidden sm:block w-3.5 h-3.5 text-slate-300 group-hover:text-indigo-500 transition-colors shrink-0" />
                  </button>
                );
              })}
            </div>
          </div>

          {/* SELECTED PERIOD — selector + summary with comparison */}
          <div className={`bg-white rounded-2xl border border-slate-200/80 shadow-2xs p-3 sm:p-4 transition-opacity ${dim}`}>
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Selected period</p>
                <p className="text-sm font-semibold text-slate-900 mt-0.5">
                  {periodLabel}{" "}
                  <span className="text-xs font-normal text-slate-500">
                    · {data.period.start} → {data.period.end}<span className="hidden sm:inline">{prev ? " · arrows compare with the previous period" : ""}</span>
                  </span>
                </p>
              </div>
              <div className="grid grid-cols-4 md:flex rounded-xl border border-slate-200 bg-slate-50 p-0.5 w-full md:w-auto md:self-start" role="tablist" aria-label="Reporting period">
                {PERIODS.map((p) => (
                  <button
                    key={p.label}
                    role="tab"
                    aria-selected={days === p.days}
                    onClick={() => setDays(p.days)}
                    className={`px-1 sm:px-3 py-2 md:py-1.5 rounded-lg text-[11px] sm:text-xs font-semibold whitespace-nowrap transition-colors ${days === p.days ? "bg-indigo-600 text-white shadow-xs" : "text-slate-600 hover:bg-white"}`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 sm:gap-3">
              {periodTiles.map((t) => (
                <div key={t.label} className="rounded-xl bg-slate-50 border border-slate-100 px-3 py-2.5">
                  <div className="text-[11px] text-slate-500">{t.label}</div>
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-xl font-bold text-slate-900 tabular-nums">{t.value}</span>
                    <Delta cur={t.value} prev={t.prev} goodWhenUp={t.up} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Trends: delivery + alerts — equal height */}
          <div className={`grid grid-cols-1 xl:grid-cols-3 gap-4 sm:gap-5 transition-opacity ${dim}`}>
            <Panel title="Delivery activity" subtitle={`Tasks created and completed, and Redmine updates, per ${data.period.granularity} · ${periodLabel.toLowerCase()}`} className="xl:col-span-2 h-[280px] sm:h-[300px]">
              {!hasTimeline ? (
                <Empty text={`No task activity in ${periodLabel.toLowerCase()}. Try a longer period.`} />
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={timeline} margin={{ top: 4, right: 8, left: -12, bottom: 0 }} barGap={2} barCategoryGap="22%">
                    <CartesianGrid vertical={false} stroke={C.grid} />
                    <XAxis dataKey="bucket" tickFormatter={(b) => fmtBucket(b, data.period.granularity)} minTickGap={16} {...axisProps} />
                    <YAxis allowDecimals={false} width={36} {...axisProps} />
                    <Tooltip {...tooltipProps} labelFormatter={(b) => fmtBucket(String(b), data.period.granularity)} />
                    <Legend {...legendProps} />
                    <Bar isAnimationActive={false} dataKey="created" name="Created" fill={C.blue} radius={[4, 4, 0, 0]} maxBarSize={26} />
                    <Bar isAnimationActive={false} dataKey="completed" name="Completed" fill={C.orange} radius={[4, 4, 0, 0]} maxBarSize={26} />
                    <Line isAnimationActive={false} type="linear" dataKey="updates" name="Redmine updates" stroke={C.aqua} strokeWidth={2} dot={{ r: 3, strokeWidth: 2, fill: C.surface }} />
                  </ComposedChart>
                </ResponsiveContainer>
              )}
            </Panel>

            <Panel title="Alerts in period" subtitle="Tap a category to open it" className="xl:h-[300px]" action={<LinkBtn onClick={() => onOpenNotifications("all")}>Open</LinkBtn>}>
              <div className="h-full flex flex-col justify-between">
                <div className="space-y-2.5">
                  {([
                    ["critical", "Critical", ps.alerts_critical, C.critical],
                    ["urgent", "Urgent", ps.alerts_urgent, C.serious],
                    ["completed", "Completed / closed", ps.alerts_completed, C.good],
                    ["all", "Info / warning", ps.alerts_info, C.neutral],
                  ] as [NotificationCategory, string, number, string][]).map(([cat, label, n, color]) => (
                    <button key={label} onClick={() => onOpenNotifications(cat)} className="w-full text-left group">
                      <div className="flex items-center justify-between text-xs">
                        <span className="flex items-center gap-1.5 font-medium text-slate-700 group-hover:text-indigo-700">
                          <span className="w-2 h-2 rounded-full" style={{ background: color }} /> {label}
                        </span>
                        <span className="font-semibold tabular-nums text-slate-900">{n}</span>
                      </div>
                      <div className="mt-1 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${ps.alerts_total ? (n / ps.alerts_total) * 100 : 0}%`, background: color }} />
                      </div>
                    </button>
                  ))}
                </div>
                <div className="pt-3 mt-3 border-t border-slate-100 grid grid-cols-3 gap-2 text-center">
                  <div><div className="text-lg font-bold tabular-nums text-slate-900">{ps.emails_sent}</div><div className="text-[10px] text-slate-500 flex items-center justify-center gap-1"><Mail className="w-3 h-3" />emailed</div></div>
                  <div><div className={`text-lg font-bold tabular-nums ${ps.emails_failed ? "text-red-700" : "text-slate-900"}`}>{ps.emails_failed}</div><div className="text-[10px] text-slate-500">failed</div></div>
                  <div><div className="text-lg font-bold tabular-nums text-slate-900">{ps.alerts_total}</div><div className="text-[10px] text-slate-500 flex items-center justify-center gap-1"><BellRing className="w-3 h-3" />total</div></div>
                </div>
              </div>
            </Panel>
          </div>

          {/* People: availability + ranking */}
          <div className={`grid grid-cols-1 xl:grid-cols-3 gap-4 sm:gap-5 transition-opacity ${dim}`}>
            <Panel title="Team availability today" subtitle={`${ranked.length} Redmine team members by open workload`} action={<LinkBtn onClick={() => onNavigate("employees")}>Employees</LinkBtn>}>
              <div className="flex h-3 rounded-full overflow-hidden gap-0.5 bg-slate-100" aria-label="Availability split">
                {people.availability_counts.filter((a) => a.count).map((a) => (
                  <div key={a.label} style={{ width: `${(a.count / totalPeople) * 100}%`, background: AVAIL[a.label].color }} title={`${a.label}: ${a.count}`} />
                ))}
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {people.availability_counts.map((a) => (
                  <div key={a.label} className="flex items-center justify-between rounded-lg border border-slate-100 px-2.5 py-1.5">
                    <span className="flex items-center gap-1.5 text-xs font-medium text-slate-700">
                      <span className="w-2 h-2 rounded-full" style={{ background: AVAIL[a.label].color }} />
                      {a.label}
                      <span className="text-[10px] text-slate-400">({a.range})</span>
                    </span>
                    <span className="text-sm font-bold tabular-nums text-slate-900">{a.count}</span>
                  </div>
                ))}
              </div>
              <div className="mt-4">
                <p className="text-[11px] font-semibold text-slate-700 flex items-center gap-1.5"><Coffee className="w-3.5 h-3.5 text-green-700" /> Free today ({people.free_today.length})</p>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {people.free_today.length === 0 ? <span className="text-[11px] text-slate-400">Everyone has open work.</span> : people.free_today.map((n) => (
                    <span key={n} className="px-2 py-0.5 rounded-full text-[10.5px] font-medium bg-green-50 text-green-800 border border-green-200">{n}</span>
                  ))}
                </div>
              </div>
              {busiest.length > 0 && (
                <div className="mt-4">
                  <p className="text-[11px] font-semibold text-slate-700">Busiest right now</p>
                  <ul className="mt-1.5 space-y-1">
                    {busiest.map((p) => (
                      <li key={p.employee_id} className="flex items-center justify-between text-xs">
                        <span className="text-slate-700 truncate">{p.name}</span>
                        <span className="text-slate-500 tabular-nums">{p.open_tasks} open{p.overdue ? <span className="text-red-700 font-semibold"> · {p.overdue} overdue</span> : ""}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Panel>

            <Panel
              title="Employee ranking"
              subtitle={`${periodLabel} · score = ${people.score_formula.replace(" (selected period)", "")}`}
              className="xl:col-span-2"
              action={<span className="flex items-center gap-1 text-[11px] text-amber-700 font-semibold whitespace-nowrap"><Trophy className="w-3.5 h-3.5" />Leaderboard</span>}
            >
              {ranked.length === 0 ? (
                <Empty text="No Redmine team members synchronized yet." />
              ) : (
                <div>
                  {/* Phones: compact cards */}
                  <ul className="md:hidden divide-y divide-slate-100 -mx-1">
                    {peopleShown.map((p) => {
                      const podium = p.score > 0 && p.rank <= 3;
                      const medal = podium ? ["bg-amber-400", "bg-slate-400", "bg-orange-400"][p.rank - 1] + " text-white" : "bg-slate-100 text-slate-500";
                      return (
                        <li key={p.employee_id} className="px-1 py-2.5 flex items-center gap-3">
                          <span className={`w-7 h-7 shrink-0 rounded-full inline-flex items-center justify-center text-[11px] font-bold ${medal}`}>{p.rank}</span>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 min-w-0">
                              <span className="text-[13px] font-semibold text-slate-900 truncate capitalize">{p.name}</span>
                              <span className={`shrink-0 px-1.5 py-0.5 rounded-full border text-[10px] font-bold ${AVAIL[p.availability].chip}`}>{p.availability}</span>
                            </div>
                            <div className="mt-1 flex items-center gap-2">
                              <div className="flex-1 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                                <div className="h-full rounded-full" style={{ width: `${(p.score / maxScore) * 100}%`, background: C.blue }} />
                              </div>
                              <span className="text-xs font-bold tabular-nums text-slate-900 w-6 text-right">{p.score}</span>
                            </div>
                            <p className="mt-0.5 text-[11px] text-slate-500 tabular-nums">
                              {p.open_tasks} open{p.overdue > 0 && <span className="text-red-700 font-semibold"> · {p.overdue} late</span>} · {p.completed_in_period} done · {p.updates_in_period} updates
                            </p>
                          </div>
                          <div className="shrink-0"><Sparkline data={p.weekly_activity} /></div>
                        </li>
                      );
                    })}
                  </ul>
                  <div className="hidden md:block overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-left text-[10.5px] text-slate-500 border-b border-slate-200">
                        <th className="py-1.5 pr-2 font-semibold w-8">#</th>
                        <th className="py-1.5 pr-2 font-semibold">Employee</th>
                        <th className="py-1.5 pr-2 font-semibold">Status</th>
                        <th className="py-1.5 pr-2 font-semibold w-40">Score</th>
                        <th className="py-1.5 pr-2 font-semibold">Open work</th>
                        <th className="py-1.5 pr-2 font-semibold text-right">Done</th>
                        <th className="py-1.5 pr-2 font-semibold text-right">Updates</th>
                        <th className="py-1.5 font-semibold">8-week trend</th>
                      </tr>
                    </thead>
                    <tbody>
                      {peopleShown.map((p) => {
                        const podium = p.score > 0 && p.rank <= 3;
                        const medal = podium ? ["bg-amber-400", "bg-slate-400", "bg-orange-400"][p.rank - 1] + " text-white" : "bg-slate-100 text-slate-500";
                        return (
                          <tr key={p.employee_id} className="border-b border-slate-100 hover:bg-slate-50/70">
                            <td className="py-2 pr-2">
                              <span className={`w-5 h-5 rounded-full inline-flex items-center justify-center text-[10px] font-bold ${medal}`}>{p.rank}</span>
                            </td>
                            <td className="py-2 pr-2 font-semibold text-slate-900 whitespace-nowrap">{p.name}</td>
                            <td className="py-2 pr-2">
                              <span className={`px-1.5 py-0.5 rounded-full border text-[10px] font-bold ${AVAIL[p.availability].chip}`} title={AVAIL[p.availability].hint}>{p.availability}</span>
                            </td>
                            <td className="py-2 pr-2">
                              <div className="flex items-center gap-2">
                                <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                                  <div className="h-full rounded-full" style={{ width: `${(p.score / maxScore) * 100}%`, background: C.blue }} />
                                </div>
                                <span className="w-6 text-right font-bold tabular-nums text-slate-900">{p.score}</span>
                              </div>
                            </td>
                            <td className="py-2 pr-2 whitespace-nowrap tabular-nums text-slate-700">
                              {p.open_tasks === 0 ? <span className="text-slate-400">—</span> : (
                                <>{p.open_on_time} on time{p.overdue > 0 && <span className="text-red-700 font-semibold"> · {p.overdue} late</span>}</>
                              )}
                            </td>
                            <td className="py-2 pr-2 text-right tabular-nums">{p.completed_in_period}</td>
                            <td className="py-2 pr-2 text-right tabular-nums">{p.updates_in_period}</td>
                            <td className="py-2"><Sparkline data={p.weekly_activity} /></td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                  </div>
                  {ranked.length > 8 && (
                    <button onClick={() => setShowAllPeople((v) => !v)} className="mt-2 w-full md:w-auto py-2 md:py-0 rounded-lg md:rounded-none bg-slate-50 md:bg-transparent text-xs md:text-[11px] font-semibold text-indigo-600 hover:text-indigo-800">
                      {showAllPeople ? "Show top 8" : `Show all ${ranked.length} team members`}
                    </button>
                  )}
                </div>
              )}
            </Panel>
          </div>

          {/* Attention + deadlines — equal height, internal scroll */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 sm:gap-5">
            <Panel title="Needs attention" subtitle="Most overdue open tasks" className="h-[320px] sm:h-[340px]" action={<LinkBtn onClick={() => onNavigate("tasks")}>All tasks</LinkBtn>}>
              {data.top_overdue.length === 0 ? (
                <Empty text="Nothing overdue. All clear." />
              ) : (
                <ul className="space-y-2 h-full overflow-y-auto pr-1">
                  {data.top_overdue.map((t) => (
                    <li key={t.id} className="flex items-start gap-3 p-2 rounded-xl border border-red-100 bg-red-50/40">
                      <span className="mt-0.5 shrink-0 min-w-10 text-center px-1.5 py-0.5 rounded-md bg-red-600 text-white text-[10px] font-bold tabular-nums">{t.days_overdue}d</span>
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-slate-900 truncate" title={t.title}>{t.title}</p>
                        <p className="text-[11px] text-slate-500 truncate">{t.project} · {t.assignee ?? <span className="text-orange-700 font-semibold">unassigned</span>} · {t.priority}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>

            <Panel title="Deadlines" subtitle="Overdue and due in the next 14 days" className="h-[320px] sm:h-[340px]" action={<LinkBtn onClick={() => onNavigate("tasks")}>Tasks</LinkBtn>}>
              {data.upcoming_deadlines.length === 0 ? (
                <Empty text="No deadlines in the next 14 days." />
              ) : (
                <ul className="divide-y divide-slate-100 h-full overflow-y-auto pr-1">
                  {data.upcoming_deadlines.map((d) => {
                    const late = d.days_left < 0;
                    return (
                      <li key={d.id} className="py-2 flex items-center gap-3">
                        <CalendarClock className={`w-4 h-4 shrink-0 ${late ? "text-red-600" : d.days_left <= 2 ? "text-orange-600" : "text-slate-400"}`} />
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-semibold text-slate-900 truncate" title={d.title}>{d.title}</p>
                          <p className="text-[11px] text-slate-500 truncate">{d.project} · {d.assignee ?? "unassigned"}</p>
                        </div>
                        <span className={`shrink-0 text-[10px] font-bold px-2 py-0.5 rounded-full border ${late ? "bg-red-50 text-red-700 border-red-200" : d.days_left <= 2 ? "bg-orange-50 text-orange-700 border-orange-200" : "bg-slate-50 text-slate-600 border-slate-200"}`}>
                          {late ? `${-d.days_left}d late` : d.days_left === 0 ? "today" : `in ${d.days_left}d`}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </Panel>
          </div>

          {/* Project health — compact cards */}
          <Panel title="Active project health" subtitle="Task split per active Redmine project" action={<LinkBtn onClick={() => onNavigate("projects")}>Projects</LinkBtn>}>
            {activeProjects.length === 0 ? (
              <Empty text="No active projects synchronized from Redmine." />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {activeProjects.map((p) => {
                  const h = HEALTH[p.health_status] ?? HEALTH.ON_TRACK;
                  const Icon = h.icon;
                  const total = Math.max(1, p.total_tasks);
                  return (
                    <button key={p.id} onClick={() => onNavigate("projects")} className="text-left p-3 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-slate-50/50 transition-all">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-xs font-semibold text-slate-900 leading-snug line-clamp-2" title={p.name}>{p.name}</p>
                        <span className={`shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-bold ${h.chip}`}><Icon className="w-3 h-3" /> {h.label}</span>
                      </div>
                      <div className="mt-2.5 flex h-2 rounded-full overflow-hidden bg-slate-100 gap-0.5">
                        {p.completed_tasks > 0 && <div style={{ width: `${(p.completed_tasks / total) * 100}%`, background: C.good }} title={`${p.completed_tasks} completed`} />}
                        {p.open_on_time > 0 && <div style={{ width: `${(p.open_on_time / total) * 100}%`, background: C.blue }} title={`${p.open_on_time} open on time`} />}
                        {p.overdue_tasks > 0 && <div style={{ width: `${(p.overdue_tasks / total) * 100}%`, background: C.critical }} title={`${p.overdue_tasks} overdue`} />}
                      </div>
                      <p className="mt-1.5 text-[11px] text-slate-500 tabular-nums">
                        {p.total_tasks} tasks · {p.completed_tasks} done · <span className={p.overdue_tasks ? "text-red-700 font-semibold" : ""}>{p.overdue_tasks} overdue</span> · team {p.team_size}
                      </p>
                    </button>
                  );
                })}
              </div>
            )}
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-slate-500">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{ background: C.good }} />Completed</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{ background: C.blue }} />Open on time</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{ background: C.critical }} />Overdue</span>
            </div>
          </Panel>
        </>
      )}
    </div>
  );
};
