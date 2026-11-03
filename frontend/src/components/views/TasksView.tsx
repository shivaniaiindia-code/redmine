"use client";

import React, { useState, useEffect } from "react";
import { CheckSquare, AlertTriangle, ShieldAlert, Clock, User, Check, RefreshCw } from "lucide-react";

interface TaskItem {
  id: string;
  title: string;
  project_id: string;
  project_name: string;
  tracker: string;
  status: string;
  priority: string;
  due_date: string | null;
  is_overdue: boolean;
  is_blocked: boolean;
  blocker_reason: string | null;
  assigned_to: string;
  estimated_hours: number;
  progress_percentage: number;
}

export const TasksView: React.FC = () => {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [filter, setFilter] = useState<string>("ALL");
  const [isLoading, setIsLoading] = useState(true);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const fetchTasks = async () => {
    try {
      setIsLoading(true);
      const res = await fetch("http://localhost:8000/api/v1/tasks/");
      if (res.ok) {
        const data = await res.json();
        setTasks(data);
      }
    } catch (err) {
      console.error("Failed to fetch tasks", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  const handleToggleBlocker = async (task: TaskItem) => {
    const nextBlockedState = !task.is_blocked;
    const reason = nextBlockedState ? prompt("Enter operational blocker reason:", "Dependent API authentication credentials pending") : null;
    if (nextBlockedState && !reason) return; // User cancelled prompt

    try {
      const res = await fetch(`http://localhost:8000/api/v1/tasks/${task.id}/toggle-blocker`, {
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

  const filteredTasks = tasks.filter((t) => {
    if (filter === "OVERDUE") return t.is_overdue;
    if (filter === "BLOCKED") return t.is_blocked;
    if (filter === "IN_PROGRESS") return t.status === "In Progress";
    if (filter === "COMPLETED") return t.status === "DONE" || t.status === "Closed" || t.status === "Resolved";
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <CheckSquare className="w-6 h-6 text-indigo-600" />
            Operational Tasks & Issues
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Tracking synced Redmine issues, blocker alerts, and deadline compliance
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
          {[
            { id: "ALL", label: "All Tasks" },
            { id: "OVERDUE", label: "Overdue" },
            { id: "BLOCKED", label: "Blocked" },
            { id: "IN_PROGRESS", label: "In Progress" },
            { id: "COMPLETED", label: "Completed" }
          ].map((pill) => (
            <button
              key={pill.id}
              onClick={() => setFilter(pill.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
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
        ) : filteredTasks.length === 0 ? (
          <div className="p-12 text-center text-slate-400">No tasks found matching filter.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-50/80 text-slate-500 text-xs uppercase tracking-wider border-b border-slate-200">
                  <th className="py-3 px-4 font-semibold">Task / Issue</th>
                  <th className="py-3 px-4 font-semibold">Project</th>
                  <th className="py-3 px-4 font-semibold">Assignee</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold">Due Date</th>
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
                          : task.status === "In Progress"
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
        )}
      </div>
    </div>
  );
};

