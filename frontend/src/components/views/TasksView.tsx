"use client";

import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { CheckSquare, AlertTriangle, ShieldAlert, User, RefreshCw } from "lucide-react";

interface TaskItem {
  id: string;
  title: string;
  project_id: string;
  project_name: string;
  tracker: string;
  status: string;
  priority: string;
  due_date: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  is_overdue: boolean;
  is_blocked: boolean;
  blocker_reason: string | null;
  assigned_to: string;
  estimated_hours: number;
  progress_percentage: number;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const TasksView: React.FC = () => {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [filter, setFilter] = useState<string>("ALL");
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const fetchTasks = async () => {
    try {
      setIsLoading(true);
      setFetchError(null);
      const res = await apiFetch(`${API_BASE_URL}/tasks/`);
      if (res.ok) {
        const data = await res.json();
        setTasks(data);
      } else {
        setFetchError(`Couldn't load tasks (error ${res.status}). Please try again.`);
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "Service unavailable";
      console.error("Failed to fetch tasks", err);
      setFetchError(`Network error: Unable to load tasks (${errMsg})`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  const handleToggleBlocker = async (task: TaskItem) => {
    const nextBlockedState = !task.is_blocked;
    const reason = nextBlockedState ? prompt("What is blocking this task?", "") : null;
    if (nextBlockedState && !reason) return; // User cancelled prompt

    try {
      const res = await apiFetch(`${API_BASE_URL}/tasks/${task.id}/toggle-blocker`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          is_blocked: nextBlockedState,
          blocker_reason: reason
        })
      });

      if (res.ok) {
        setActionNotice(nextBlockedState ? `Task flagged as Blocked! Critical alert automatically mirrored to Admin.` : `Task unblocked successfully.`);
        await fetchTasks();
      }
    } catch (err) {
      console.error("Error toggling blocker", err);
    } finally {
      setTimeout(() => setActionNotice(null), 5000);
    }
  };

  const formatDate = (isoStr: string | null | undefined) => {
    if (!isoStr) return "-";
    try {
      const d = new Date(isoStr);
      return isNaN(d.getTime())
        ? isoStr.split("T")[0]
        : d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
    } catch {
      return isoStr;
    }
  };

  const filteredTasks = tasks.filter((t) => {
    if (filter === "OVERDUE") return Boolean(t.is_overdue) && (t.progress_percentage ?? 0) < 100;
    if (filter === "BLOCKED") return Boolean(t.is_blocked) && (t.progress_percentage ?? 0) < 100;
    const s = (t.status || "").toLowerCase();
    if (filter === "IN_PROGRESS") {
      return (s.includes("progress") || s.includes("feedback") || s === "in-progress" || s === "development") && (t.progress_percentage ?? 0) < 100;
    }
    if (filter === "COMPLETED") {
      return s === "done" || s === "closed" || s === "resolved" || (t.progress_percentage ?? 0) >= 100;
    }
    return true;
  });

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-4 sm:p-5 rounded-xl border border-slate-200/80 shadow-sm">
        <div>
          <h1 className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">
            <CheckSquare className="w-5 h-5 sm:w-6 sm:h-6 text-indigo-600 shrink-0" />
            Operational Tasks & Issues
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Tracking synced Redmine issues, blocker alerts, and deadline compliance
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto -mx-4 px-4 sm:mx-0 sm:px-0 pb-1 sm:pb-0 [scrollbar-width:none]" role="tablist" aria-label="Filter tasks">
          {[
            { id: "ALL", label: `All Tasks (${tasks.length})` },
            { id: "OVERDUE", label: `Overdue (${tasks.filter((t) => t.is_overdue).length})` },
            { id: "BLOCKED", label: `Blocked (${tasks.filter((t) => t.is_blocked).length})` },
            {
              id: "IN_PROGRESS",
              label: `In Progress (${
                tasks.filter((t) => {
                  const s = (t.status || "").toLowerCase();
                  return s.includes("progress") || s.includes("feedback") || s === "in-progress" || s === "development";
                }).length
              })`
            },
            {
              id: "COMPLETED",
              label: `Completed (${
                tasks.filter((t) => {
                  const s = (t.status || "").toLowerCase();
                  return s === "done" || s === "closed" || s === "resolved";
                }).length
              })`
            }
          ].map((pill) => (
            <button
              key={pill.id}
              onClick={() => setFilter(pill.id)}
              role="tab"
              aria-selected={filter === pill.id}
              className={`px-3 py-2 sm:py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap shrink-0 transition-colors ${
                filter === pill.id
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {pill.label}
            </button>
          ))}
        </div>
      </div>

      {actionNotice && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800 font-medium">
          {actionNotice}
        </div>
      )}

      {/* Tasks Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-slate-400">Loading operational tasks...</div>
        ) : fetchError ? (
          <div className="p-8 bg-rose-50 border border-rose-200 rounded-xl text-center space-y-3">
            <div className="flex items-center justify-center gap-2 text-rose-700 font-semibold text-sm">
              <AlertTriangle className="w-5 h-5 text-rose-600" />
              <span>Unable to Load Tasks</span>
            </div>
            <p className="text-xs text-rose-600 max-w-lg mx-auto">{fetchError}</p>
            <button
              onClick={fetchTasks}
              className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-all inline-flex items-center gap-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Retry Fetch
            </button>
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="p-12 text-center text-slate-400">No tasks found matching filter.</div>
        ) : (
          <>
          {/* Phones: one card per task */}
          <ul className="md:hidden divide-y divide-slate-100">
            {filteredTasks.map((task) => {
              const done = task.status === "DONE" || task.status === "Resolved" || task.status === "Closed";
              return (
                <li key={task.id} className="p-4 space-y-2.5">
                  <div className="flex items-start gap-2">
                    {task.is_blocked ? (
                      <ShieldAlert className="w-4 h-4 mt-0.5 text-rose-600 shrink-0" aria-label="Blocked" />
                    ) : task.is_overdue ? (
                      <AlertTriangle className="w-4 h-4 mt-0.5 text-amber-500 shrink-0" aria-label="Overdue" />
                    ) : null}
                    <p className="text-sm font-semibold text-slate-900 leading-snug">{task.title}</p>
                  </div>
                  {task.blocker_reason && <p className="text-xs text-rose-600 italic">Blocker: {task.blocker_reason}</p>}
                  <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                    <span className={`px-2 py-0.5 rounded font-semibold ${
                      done ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                        : (task.status || "").toLowerCase().includes("progress") ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                        : "bg-slate-100 text-slate-700"}`}>{task.status}</span>
                    {task.due_date && (
                      <span className={`px-2 py-0.5 rounded font-semibold ${task.is_overdue ? "bg-rose-50 text-rose-700 border border-rose-200" : "bg-slate-50 text-slate-600 border border-slate-200"}`}>
                        Due {task.due_date}{task.is_overdue && " · overdue"}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-500 space-y-0.5">
                    <p className="font-semibold text-slate-600">{task.project_name}</p>
                    <p className="flex items-center gap-1.5"><User className="w-3.5 h-3.5 text-slate-400" />{task.assigned_to}</p>
                    <p className="text-[11px]">Updated {formatDate(task.updated_at)}</p>
                  </div>
                  <button
                    onClick={() => handleToggleBlocker(task)}
                    className={`w-full text-xs font-semibold px-3 py-2.5 rounded-lg transition-colors ${
                      task.is_blocked ? "bg-rose-100 active:bg-rose-200 text-rose-800" : "bg-slate-100 active:bg-slate-200 text-slate-700"
                    }`}
                  >
                    {task.is_blocked ? "Unblock Task" : "Flag Blocker"}
                  </button>
                </li>
              );
            })}
          </ul>
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-50/80 text-slate-500 text-xs uppercase tracking-wider border-b border-slate-200">
                  <th className="py-3 px-4 font-semibold">Task / Issue</th>
                  <th className="py-3 px-4 font-semibold">Project</th>
                  <th className="py-3 px-4 font-semibold">Assignee</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold">Due Date</th>
                  <th className="py-3 px-4 font-semibold">Redmine Timestamps</th>
                  <th className="py-3 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredTasks.map((task) => (
                  <tr key={task.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-3.5 px-4 font-medium text-slate-900 max-w-xs sm:max-w-md">
                      <div className="flex items-center gap-2">
                        {task.is_blocked && (
                          <span title="Operational Blocker">
                            <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
                          </span>
                        )}
                        {task.is_overdue && !task.is_blocked && (
                          <span title="Overdue Task">
                            <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
                          </span>
                        )}
                        <span className="line-clamp-2" title={task.title}>
                          {task.title}
                        </span>
                      </div>
                      {task.blocker_reason && (
                        <p className="text-xs text-rose-600 mt-1 pl-6 italic">
                          Blocker: {task.blocker_reason}
                        </p>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-xs font-semibold text-slate-600">
                      {task.project_name}
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-600">
                      <div className="flex items-center gap-1.5">
                        <User className="w-3.5 h-3.5 text-slate-400" />
                        {task.assigned_to}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-semibold ${
                        task.status === "DONE" || task.status === "Resolved" || task.status === "Closed"
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : (task.status || "").toLowerCase().includes("progress")
                          ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
                          : "bg-slate-100 text-slate-700"
                      }`}>
                        {task.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-xs">
                      {task.due_date ? (
                        <span className={`font-semibold ${task.is_overdue ? "text-rose-600" : "text-slate-600"}`}>
                          {task.due_date} {task.is_overdue && "(Overdue)"}
                        </span>
                      ) : (
                        <span className="text-slate-400">None</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-500">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-1" title={`Created on Redmine: ${task.created_at || 'N/A'}`}>
                          <span className="text-slate-400 text-[10px] uppercase font-semibold">Created:</span>
                          <span>{formatDate(task.created_at)}</span>
                        </div>
                        <div className="flex items-center gap-1" title={`Updated on Redmine: ${task.updated_at || 'N/A'}`}>
                          <span className="text-slate-400 text-[10px] uppercase font-semibold">Updated:</span>
                          <span>{formatDate(task.updated_at)}</span>
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleToggleBlocker(task)}
                        className={`text-xs font-semibold px-2.5 py-1 rounded transition-colors ${
                          task.is_blocked
                            ? "bg-rose-100 hover:bg-rose-200 text-rose-800"
                            : "bg-slate-100 hover:bg-slate-200 text-slate-700"
                        }`}
                      >
                        {task.is_blocked ? "Unblock Task" : "Flag Blocker"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          </>
        )}
      </div>
    </div>
  );
};

