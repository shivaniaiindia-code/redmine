"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  LineChart,
  Line,
  Cell,
} from "recharts";
import {
  BarChart3,
  RefreshCw,
  Download,
  FolderKanban,
  ListTodo,
  AlarmClock,
  Timer,
  CheckCircle2,
  UserX,
  AlertTriangle,
  ShieldCheck,
  Ban,
} from "lucide-react";
import { useIsPhone } from "@/lib/useMediaQuery";


const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/* Validated palette (dataviz reference instance, light mode). Status colours are reserved for state. */
const C = {
  blue: "#2a78d6", // categorical slot 1
  orange: "#eb6834", // categorical slot 2
  good: "#0ca30c",
  warning: "#fab219",
  serious: "#ec835a",
  critical: "#d03b3b",
  neutral: "#94a3b8",
  ramp: ["#86b6ef", "#3987e5", "#256abf", "#184f95"], // ordinal blue, light → dark
  grid: "#e2e8f0",
  axis: "#64748b",
  surface: "#ffffff",
};

interface Report {
  generated_at: string;
  as_of: string;
  scope: string;
  kpis: Record<string, number>;
  projects: {
    id: string; name: string; code: string; status: string; health_status: string; health_reason: string | null;
    progress_percentage: number; total_tasks: number; completed_tasks: number; open_on_time: number;
    overdue_tasks: number; blocked_tasks: number; unassigned_open_tasks: number; max_days_overdue: number;
    team_size: number; estimated_hours: number; spent_hours: number;
  }[];
  task_status: { status: string; count: number }[];
  priorities: { priority: string; count: number }[];
  overdue_aging: { bucket: string; count: number }[];
  project_health: { health: string; count: number }[];
  workload: { employee_id: string; name: string; open_on_time: number; overdue: number; open_tasks: number; projects: number; estimated_hours: number }[];
  weekly_trend: { week: string; created: number; completed: number }[];
  alerts_daily: { date: string; critical: number; urgent: number; completed: number; info: number }[];
  top_overdue: { id: string; title: string; project: string | null; assignee: string | null; priority: string; due_date: string | null; days_overdue: number; status: string }[];
}

const axisProps = { tick: { fill: C.axis, fontSize: 11 }, axisLine: { stroke: C.grid }, tickLine: false } as const;
const tooltipProps = {
  cursor: { fill: "rgba(148,163,184,0.12)" },
  contentStyle: { borderRadius: 10, border: "1px solid #e2e8f0", fontSize: 12, boxShadow: "0 4px 16px rgba(15,23,42,.08)" },
  labelStyle: { color: "#0f172a", fontWeight: 600 },
} as const;
const legendProps = { iconType: "circle" as const, iconSize: 8, wrapperStyle: { fontSize: 11, color: "#475569" } };

const short = (s: string, n = 22) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);
const fmtWeek = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" });

const Card: React.FC<{ title: string; subtitle?: string; className?: string; children: React.ReactNode; empty?: boolean }> = ({
  title, subtitle, className = "", children, empty,
}) => (
  <section className={`bg-white rounded-2xl border border-slate-200/80 shadow-2xs p-3.5 sm:p-5 min-w-0 ${className}`}>
    <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
    {subtitle && <p className="text-[11px] text-slate-500 mt-0.5">{subtitle}</p>}
    <div className="mt-4">
      {empty ? <div className="h-40 flex items-center justify-center text-xs text-slate-400">No data for this scope.</div> : children}
    </div>
  </section>
);

const Kpi: React.FC<{ icon: React.ElementType; label: string; value: string; note?: string; tone?: "critical" | "good" | "default" }> = ({
  icon: Icon, label, value, note, tone = "default",
}) => (
  <div className="bg-white rounded-2xl border border-slate-200/80 shadow-2xs p-3 sm:p-4 min-w-0">
    <div className="flex items-center gap-2 text-[11px] font-medium text-slate-500 truncate">
      <Icon className={`w-4 h-4 shrink-0 ${tone === "critical" ? "text-red-600" : tone === "good" ? "text-green-700" : "text-indigo-500"}`} />
      {label}
    </div>
    <div className="mt-1.5 sm:mt-2 text-xl sm:text-2xl font-bold text-slate-900 tabular-nums">{value}</div>
    {note && <div className="text-[11px] text-slate-500 mt-0.5">{note}</div>}
  </div>
);

const HEALTH_META: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  ON_TRACK: { label: "On track", color: C.good, icon: ShieldCheck },
  AT_RISK: { label: "At risk", color: C.serious, icon: AlertTriangle },
  BLOCKED: { label: "Blocked", color: C.critical, icon: Ban },
  OFF_TRACK: { label: "Off track", color: C.critical, icon: AlertTriangle },
};

const toCsv = (rows: Record<string, unknown>[]) => {
  if (!rows.length) return "";
  const cols = Object.keys(rows[0]);
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [cols.join(","), ...rows.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n");
};

export const ReportsView: React.FC = () => {
  const [data, setData] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [includeInactive, setIncludeInactive] = useState(true);
  const [weeks, setWeeks] = useState(12);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`${API_BASE_URL}/reports/overview?include_inactive=${includeInactive}&weeks=${weeks}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData(await res.json());
      setError(null);
    } catch {
      setError("Couldn't load reports. Please try again in a moment.");
    } finally {
      setLoading(false);
    }
  }, [includeInactive, weeks]);

  useEffect(() => {
    load();
  }, [load]);

  const exportCsv = () => {
    if (!data) return;
    const rows = data.projects.map((p) => ({
      project: p.name, code: p.code, status: p.status, health: p.health_status, health_reason: p.health_reason ?? "",
      progress_pct: p.progress_percentage, total_tasks: p.total_tasks, completed: p.completed_tasks,
      open_on_time: p.open_on_time, overdue: p.overdue_tasks, blocked: p.blocked_tasks,
      unassigned_open: p.unassigned_open_tasks, max_days_overdue: p.max_days_overdue, team_size: p.team_size,
      estimated_hours: p.estimated_hours, spent_hours: p.spent_hours,
    }));
    const blob = new Blob([toCsv(rows)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `project-report-${data.as_of}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const phone = useIsPhone();
  const projectBars = useMemo(
    () => (data?.projects ?? []).filter((p) => p.total_tasks > 0).map((p) => ({ ...p, label: short(p.name, phone ? 14 : 26) })),
    [data, phone]
  );
  const workloadBars = useMemo(() => (data?.workload ?? []).filter((w) => w.open_tasks > 0).slice(0, 12), [data]);
  const alertsTotal = useMemo(
    () => (data?.alerts_daily ?? []).reduce((s, d) => s + d.critical + d.urgent + d.completed + d.info, 0),
    [data]
  );
  const trendTotal = useMemo(() => (data?.weekly_trend ?? []).reduce((s, w) => s + w.created + w.completed, 0), [data]);

  const k = data?.kpis;

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header + filters (one row) */}
      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/80 shadow-2xs flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 sm:w-6 sm:h-6 text-indigo-600 shrink-0" /> Reports &amp; Analytics
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Computed from synchronized Redmine data{data ? ` · as of ${data.as_of} · generated ${data.generated_at}` : ""}.
          </p>
        </div>
        <div className="grid grid-cols-2 sm:flex sm:flex-wrap items-center gap-2 text-xs">
          <label className="col-span-2 sm:col-span-1 flex items-center gap-2 px-3 py-2.5 sm:py-2 rounded-xl border border-slate-200 bg-slate-50 cursor-pointer font-medium text-slate-700">
            <input type="checkbox" checked={includeInactive} onChange={(e) => setIncludeInactive(e.target.checked)} className="rounded text-indigo-600" />
            Include inactive projects
          </label>
          <select
            aria-label="Trend window"
            value={weeks}
            onChange={(e) => setWeeks(Number(e.target.value))}
            className="col-span-2 sm:col-span-1 px-3 py-2.5 sm:py-2 rounded-xl border border-slate-200 bg-slate-50 font-medium text-slate-700"
          >
            <option value={4}>Last 4 weeks</option>
            <option value={12}>Last 12 weeks</option>
            <option value={26}>Last 26 weeks</option>
          </select>
          <button
            onClick={load}
            disabled={loading}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 sm:py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 font-semibold text-slate-700 disabled:opacity-60"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
          </button>
          <button
            onClick={exportCsv}
            disabled={!data}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 sm:py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold disabled:opacity-60"
          >
            <Download className="w-3.5 h-3.5" /> Export CSV
          </button>
        </div>
      </div>

      {error && <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">{error}</div>}
      {!data && loading && <div className="py-20 text-center text-sm text-slate-400">Loading reports…</div>}

      {data && k && (
        <>
          {/* KPI tiles */}
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-2.5 sm:gap-4">
            <Kpi icon={FolderKanban} label="Active projects" value={`${k.active_projects}`} note={`${k.at_risk_projects} at risk · ${k.projects} in scope`} />
            <Kpi icon={ListTodo} label="Open tasks" value={`${k.open_tasks}`} note={`${k.total_tasks} total tasks`} />
            <Kpi icon={AlarmClock} label="Overdue tasks" value={`${k.overdue_tasks}`} note={`${k.overdue_rate}% of open work`} tone={k.overdue_tasks ? "critical" : "default"} />
            <Kpi icon={Timer} label="Avg. days overdue" value={`${k.avg_days_overdue}`} note="across overdue tasks" tone={k.avg_days_overdue ? "critical" : "default"} />
            <Kpi icon={CheckCircle2} label="Completion rate" value={`${k.completion_rate}%`} note={`${k.completed_tasks} completed`} tone={k.completion_rate > 0 ? "good" : "default"} />
            <Kpi icon={UserX} label="Unassigned open" value={`${k.unassigned_open_tasks}`} note="tasks without an owner" />
          </div>

          {/* Project delivery + health */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 sm:gap-6">
            <Card
              title="Task delivery by project"
              subtitle="Completed, open (on time) and overdue tasks per project"
              className="xl:col-span-2"
              empty={!projectBars.length}
            >
              <ResponsiveContainer width="100%" height={Math.max(180, projectBars.length * 44 + 60)}>
                <BarChart data={projectBars} layout="vertical" margin={{ left: phone ? 0 : 8, right: phone ? 8 : 16 }} barCategoryGap={10}>
                  <CartesianGrid horizontal={false} stroke={C.grid} />
                  <XAxis type="number" allowDecimals={false} {...axisProps} />
                  <YAxis type="category" dataKey="label" width={phone ? 96 : 170} {...axisProps} />
                  <Tooltip {...tooltipProps} labelFormatter={(_, p) => p?.[0]?.payload?.name ?? ""} />
                  <Legend {...legendProps} />
                  <Bar isAnimationActive={false} dataKey="completed_tasks" name="Completed" stackId="t" fill={C.good} stroke={C.surface} strokeWidth={2} />
                  <Bar isAnimationActive={false} dataKey="open_on_time" name="Open (on time)" stackId="t" fill={C.blue} stroke={C.surface} strokeWidth={2} />
                  <Bar isAnimationActive={false} dataKey="overdue_tasks" name="Overdue" stackId="t" fill={C.critical} stroke={C.surface} strokeWidth={2} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>

            <Card title="Project health" subtitle="Current health status of projects in scope">
              <div className="space-y-3">
                {data.project_health.map((h) => {
                  const meta = HEALTH_META[h.health] ?? { label: h.health, color: C.neutral, icon: AlertTriangle };
                  const Icon = meta.icon;
                  const pct = k.projects ? (h.count / k.projects) * 100 : 0;
                  return (
                    <div key={h.health}>
                      <div className="flex items-center justify-between text-xs">
                        <span className="flex items-center gap-1.5 font-medium text-slate-700">
                          <Icon className="w-3.5 h-3.5" style={{ color: meta.color }} /> {meta.label}
                        </span>
                        <span className="font-semibold text-slate-900 tabular-nums">{h.count}</span>
                      </div>
                      <div className="mt-1.5 h-2 rounded-full bg-slate-100 overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: meta.color }} />
                      </div>
                    </div>
                  );
                })}
                <div className="pt-3 border-t border-slate-100 space-y-1.5">
                  {data.projects.filter((p) => p.health_status !== "ON_TRACK").map((p) => (
                    <p key={p.id} className="text-[11px] text-slate-600">
                      <span className="font-semibold text-slate-800">{short(p.name, 34)}</span> — {p.health_reason ?? p.health_status}
                    </p>
                  ))}
                </div>
              </div>
            </Card>
          </div>

          {/* Aging + priority */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
            <Card title="Overdue aging" subtitle="How long overdue tasks have been late" empty={!k.overdue_tasks}>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={data.overdue_aging} margin={{ top: 22, right: 8 }} barCategoryGap="28%">
                  <CartesianGrid vertical={false} stroke={C.grid} />
                  <XAxis dataKey="bucket" {...axisProps} />
                  <YAxis allowDecimals={false} width={28} {...axisProps} />
                  <Tooltip {...tooltipProps} />
                  <Bar isAnimationActive={false} dataKey="count" name="Overdue tasks" radius={[4, 4, 0, 0]} label={{ position: "top", fontSize: 11, fill: "#334155" }}>
                    {data.overdue_aging.map((_, i) => (
                      <Cell key={i} fill={C.ramp[i] ?? C.ramp[C.ramp.length - 1]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>

            <Card title="Open tasks by priority" subtitle="Redmine priority of work still open" empty={!k.open_tasks}>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={data.priorities} layout="vertical" margin={{ left: 8, right: 24 }} barCategoryGap="24%">
                  <CartesianGrid horizontal={false} stroke={C.grid} />
                  <XAxis type="number" allowDecimals={false} {...axisProps} />
                  <YAxis type="category" dataKey="priority" width={80} {...axisProps} />
                  <Tooltip {...tooltipProps} />
                  <Bar isAnimationActive={false} dataKey="count" name="Open tasks" fill={C.blue} radius={[0, 4, 4, 0]} label={{ position: "right", fontSize: 11, fill: "#334155" }} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>

          {/* Workload */}
          <Card title="Open workload by employee" subtitle="Open tasks assigned in Redmine, split by on-time vs overdue" empty={!workloadBars.length}>
            <ResponsiveContainer width="100%" height={Math.max(180, workloadBars.length * 38 + 60)}>
              <BarChart data={workloadBars} layout="vertical" margin={{ left: phone ? 0 : 8, right: phone ? 8 : 16 }} barCategoryGap={10}>
                <CartesianGrid horizontal={false} stroke={C.grid} />
                <XAxis type="number" allowDecimals={false} {...axisProps} />
                <YAxis type="category" dataKey="name" width={phone ? 90 : 140} tickFormatter={(n: string) => (phone ? short(n, 12) : n)} {...axisProps} />
                <Tooltip {...tooltipProps} />
                <Legend {...legendProps} />
                <Bar isAnimationActive={false} dataKey="open_on_time" name="Open (on time)" stackId="w" fill={C.blue} stroke={C.surface} strokeWidth={2} />
                <Bar isAnimationActive={false} dataKey="overdue" name="Overdue" stackId="w" fill={C.critical} stroke={C.surface} strokeWidth={2} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          {/* Trends */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
            <Card
              title="Tasks created vs completed"
              subtitle={`Per week, last ${weeks} weeks (completed = closed issues by last Redmine update)`}
              empty={!trendTotal}
            >
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={data.weekly_trend} margin={{ top: 8, right: 12 }}>
                  <CartesianGrid vertical={false} stroke={C.grid} />
                  <XAxis dataKey="week" tickFormatter={fmtWeek} minTickGap={18} {...axisProps} />
                  <YAxis allowDecimals={false} width={28} {...axisProps} />
                  <Tooltip {...tooltipProps} cursor={{ stroke: "#94a3b8", strokeWidth: 1 }} labelFormatter={(w) => `Week of ${fmtWeek(String(w))}`} />
                  <Legend {...legendProps} />
                  <Line type="linear" dataKey="created" name="Created" stroke={C.blue} strokeWidth={2} dot={{ r: 4, strokeWidth: 2, fill: C.surface }} activeDot={{ r: 5 }} />
                  <Line type="linear" dataKey="completed" name="Completed" stroke={C.orange} strokeWidth={2} dot={{ r: 4, strokeWidth: 2, fill: C.surface }} activeDot={{ r: 5 }} />
                </LineChart>
              </ResponsiveContainer>
            </Card>

            <Card title="Alerts raised (last 14 days)" subtitle="Notification volume by category per day" empty={!alertsTotal}>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={data.alerts_daily} margin={{ top: 8, right: 8 }} barCategoryGap="20%">
                  <CartesianGrid vertical={false} stroke={C.grid} />
                  <XAxis dataKey="date" tickFormatter={fmtWeek} minTickGap={12} {...axisProps} />
                  <YAxis allowDecimals={false} width={32} {...axisProps} />
                  <Tooltip {...tooltipProps} labelFormatter={(d) => fmtWeek(String(d))} />
                  <Legend {...legendProps} />
                  <Bar isAnimationActive={false} dataKey="critical" name="Critical" stackId="a" fill={C.critical} stroke={C.surface} strokeWidth={2} />
                  <Bar isAnimationActive={false} dataKey="urgent" name="Urgent" stackId="a" fill={C.serious} stroke={C.surface} strokeWidth={2} />
                  <Bar isAnimationActive={false} dataKey="completed" name="Completed" stackId="a" fill={C.good} stroke={C.surface} strokeWidth={2} />
                  <Bar isAnimationActive={false} dataKey="info" name="Info / warning" stackId="a" fill={C.neutral} stroke={C.surface} strokeWidth={2} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>

          {/* Tables */}
          <Card title="Project report" subtitle={`Scope: ${data.scope}`} empty={!data.projects.length}>
            <div className="overflow-x-auto -mx-1 overscroll-x-contain">
              <table className="w-full min-w-[640px] text-xs">
                <thead>
                  <tr className="text-left text-slate-500 border-b border-slate-200">
                    {["Project", "Status", "Health", "Progress", "Tasks", "Done", "Overdue", "Blocked", "Unassigned", "Max late", "Team"].map((h) => (
                      <th key={h} className="py-2 px-2 font-semibold whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.projects.map((p) => {
                    const meta = HEALTH_META[p.health_status];
                    return (
                      <tr key={p.id} className="border-b border-slate-100 hover:bg-slate-50/70">
                        <td className="py-2 px-2 font-semibold text-slate-900 max-w-[260px] truncate" title={p.name}>{p.name}</td>
                        <td className="py-2 px-2 text-slate-600">{p.status}</td>
                        <td className="py-2 px-2">
                          <span className="inline-flex items-center gap-1 font-medium text-slate-700">
                            <span className="w-2 h-2 rounded-full" style={{ background: meta?.color ?? C.neutral }} />
                            {meta?.label ?? p.health_status}
                          </span>
                        </td>
                        <td className="py-2 px-2 tabular-nums text-slate-700">{p.progress_percentage.toFixed(0)}%</td>
                        <td className="py-2 px-2 tabular-nums">{p.total_tasks}</td>
                        <td className="py-2 px-2 tabular-nums">{p.completed_tasks}</td>
                        <td className={`py-2 px-2 tabular-nums ${p.overdue_tasks ? "font-bold text-red-700" : ""}`}>{p.overdue_tasks}</td>
                        <td className="py-2 px-2 tabular-nums">{p.blocked_tasks}</td>
                        <td className="py-2 px-2 tabular-nums">{p.unassigned_open_tasks}</td>
                        <td className="py-2 px-2 tabular-nums">{p.max_days_overdue ? `${p.max_days_overdue}d` : "—"}</td>
                        <td className="py-2 px-2 tabular-nums">{p.team_size}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>

          <Card title="Most overdue tasks" subtitle="Top 10 open tasks by days past due" empty={!data.top_overdue.length}>
            <div className="overflow-x-auto -mx-1 overscroll-x-contain">
              <table className="w-full min-w-[640px] text-xs">
                <thead>
                  <tr className="text-left text-slate-500 border-b border-slate-200">
                    {["Task", "Project", "Assignee", "Priority", "Due", "Days late"].map((h) => (
                      <th key={h} className="py-2 px-2 font-semibold whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.top_overdue.map((t) => (
                    <tr key={t.id} className="border-b border-slate-100 hover:bg-slate-50/70">
                      <td className="py-2 px-2 font-medium text-slate-900 max-w-[340px] truncate" title={t.title}>{t.title}</td>
                      <td className="py-2 px-2 text-slate-600 max-w-[200px] truncate" title={t.project ?? ""}>{t.project ?? "—"}</td>
                      <td className="py-2 px-2 text-slate-600">{t.assignee ?? <span className="text-amber-700 font-medium">Unassigned</span>}</td>
                      <td className="py-2 px-2 text-slate-600">{t.priority}</td>
                      <td className="py-2 px-2 tabular-nums text-slate-600">{t.due_date}</td>
                      <td className="py-2 px-2 tabular-nums font-bold text-red-700">{t.days_overdue}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
};
