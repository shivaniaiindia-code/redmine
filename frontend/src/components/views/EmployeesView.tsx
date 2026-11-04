"use client";

import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { Users, Mail, Briefcase, CheckCircle, AlertTriangle, Layers, FolderGit2, Gauge, RefreshCw } from "lucide-react";

interface ProjectAssignment {
  id: string;
  name: string;
  code: string;
  role: string;
}

interface EmployeeItem {
  id: string;
  name: string;
  email: string;
  job_title: string;
  department: string;
  status: string;
  weekly_capacity_hours: number;
  total_tasks: number;
  overdue_tasks: number;
  completed_tasks: number;
  current_projects?: ProjectAssignment[];
  allocated_hours?: number;
  workload_score?: number;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const EmployeesView: React.FC = () => {
  const [employees, setEmployees] = useState<EmployeeItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const fetchEmployees = async () => {
    try {
      setIsLoading(true);
      setFetchError(null);
      const res = await apiFetch(`${API_BASE_URL}/employees/`);
      if (res.ok) {
        const data = await res.json();
        setEmployees(data);
      } else {
        setFetchError(`Couldn't load employees (error ${res.status}). Please try again.`);
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "Service unavailable";
      console.error("Failed to load employees", err);
      setFetchError(`Network error: Unable to load employees (${errMsg})`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchEmployees();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "ACTIVE":
        return (
          <span className="inline-flex shrink-0 whitespace-nowrap items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 select-none">
            <CheckCircle className="w-3 h-3" /> Active
          </span>
        );
      case "ON_LEAVE":
        return (
          <span className="inline-flex shrink-0 whitespace-nowrap items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 select-none">
            <AlertTriangle className="w-3 h-3" /> On Leave
          </span>
        );
      case "DEPARTED":
        return (
          <span className="inline-flex shrink-0 whitespace-nowrap items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 select-none">
            Departed
          </span>
        );
      default:
        return (
          <span className="inline-flex shrink-0 whitespace-nowrap items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  const getWorkloadStyle = (score: number, allocated: number, capacity: number) => {
    const pct = capacity > 0 ? Math.min(100, Math.round((allocated / capacity) * 100)) : 0;
    if (score > 1.25 || allocated > 45) {
      return {
        barColor: "bg-rose-500",
        badgeBg: "bg-rose-50 text-rose-700 border-rose-200",
        label: "Exceeded",
        pct
      };
    }
    if (score > 1.0 || allocated > capacity) {
      return {
        barColor: "bg-amber-500",
        badgeBg: "bg-amber-50 text-amber-700 border-amber-200",
        label: "High Load",
        pct
      };
    }
    return {
      barColor: "bg-emerald-500",
      badgeBg: "bg-emerald-50 text-emerald-700 border-emerald-200",
      label: "Optimal",
      pct
    };
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200/80 shadow-sm">
        <h1 className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">
          <Users className="w-5 h-5 sm:w-6 sm:h-6 text-indigo-600 shrink-0" />
          Employee 360 & Talent Directory
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Historical project contributions, active allocations, and workload distribution monitoring
        </p>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-slate-400">Loading team members...</div>
      ) : fetchError ? (
        <div className="p-8 bg-rose-50 border border-rose-200 rounded-xl text-center space-y-3">
          <div className="flex items-center justify-center gap-2 text-rose-700 font-semibold text-sm">
            <AlertTriangle className="w-5 h-5 text-rose-600" />
            <span>Unable to Load Employees</span>
          </div>
          <p className="text-xs text-rose-600 max-w-lg mx-auto">{fetchError}</p>
          <button
            onClick={fetchEmployees}
            className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-all inline-flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Retry Fetch
          </button>
        </div>
      ) : employees.length === 0 ? (
        <div className="p-12 text-center text-slate-400">No employees found. Click &quot;Sync Redmine Now&quot; to populate.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 sm:gap-5">
          {employees.map((emp) => {
            const capacity = emp.weekly_capacity_hours || 40;
            const allocated = emp.allocated_hours || 0;
            const score = emp.workload_score || 0;
            const workloadStyle = getWorkloadStyle(score, allocated, capacity);

            return (
              <div
                key={emp.id}
                className="bg-white rounded-xl border border-slate-200/80 p-4 sm:p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between min-w-0 overflow-hidden"
              >
                <div className="w-full min-w-0">
                  <div className="flex items-start justify-between gap-2 mb-3 w-full min-w-0">
                    <div className="flex items-center gap-3 min-w-0 flex-1 overflow-hidden">
                      <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm shrink-0">
                        {emp.name.split(" ").filter(Boolean).slice(0, 2).map((n) => n[0].toUpperCase()).join("")}
                      </div>
                      <div className="min-w-0 flex-1 overflow-hidden">
                        <h3 className="text-base font-bold text-slate-900 truncate capitalize" title={emp.name}>
                          {emp.name}
                        </h3>
                        <p className="text-xs text-slate-500 flex items-center gap-1 min-w-0">
                          <Briefcase className="w-3 h-3 shrink-0" />
                          <span className="truncate">{emp.job_title}</span>
                        </p>
                      </div>
                    </div>
                    <div className="shrink-0">
                      {getStatusBadge(emp.status)}
                    </div>
                  </div>

                  <div className="space-y-1.5 text-xs text-slate-600 mb-3 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                    <div className="flex items-center gap-1.5">
                      <Mail className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span className="truncate">{emp.email}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span>Department: {emp.department}</span>
                    </div>
                  </div>

                  {/* Current Projects Assignments */}
                  <div className="mb-3">
                    <div className="text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1">
                      <FolderGit2 className="w-3.5 h-3.5 text-indigo-500" />
                      <span>Current Projects ({emp.current_projects?.length || 0}):</span>
                    </div>
                    {emp.current_projects && emp.current_projects.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5 max-h-20 overflow-y-auto">
                        {emp.current_projects.map((proj) => (
                          <span
                            key={proj.id}
                            className="inline-flex max-w-full min-w-0 items-center gap-1 text-[11px] bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded border border-indigo-100 font-medium"
                            title={`${proj.name} (${proj.role})`}
                          >
                            <span className="font-semibold truncate">{proj.code || proj.name}</span>
                            <span className="text-indigo-400 text-[10px] shrink-0">· {proj.role}</span>
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-400 italic">No active project assignments</p>
                    )}
                  </div>

                  {/* Workload Distribution Gauge */}
                  <div className="mb-4 bg-slate-50/70 p-2.5 rounded-lg border border-slate-100">
                    <div className="flex flex-wrap items-center justify-between gap-1.5 text-xs mb-1.5">
                      <span className="font-semibold text-slate-700 flex items-center gap-1 whitespace-nowrap">
                        <Gauge className="w-3.5 h-3.5 text-slate-400" />
                        Workload ({allocated}h / {capacity}h)
                      </span>
                      <span className={`shrink-0 whitespace-nowrap text-[11px] font-semibold px-1.5 py-0.5 rounded border ${workloadStyle.badgeBg}`}>
                        Score: {score.toFixed(2)} ({workloadStyle.label})
                      </span>
                    </div>
                    <div className="w-full bg-slate-200/80 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-2 rounded-full transition-all duration-500 ${workloadStyle.barColor}`}
                        style={{ width: `${workloadStyle.pct}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Tasks Summary */}
                <div className="pt-3 border-t border-slate-100 grid grid-cols-3 gap-2 text-center">
                  <div className="bg-slate-50 p-2 rounded">
                    <div className="text-xs text-slate-500">Tasks</div>
                    <div className="text-sm font-bold text-slate-900">{emp.total_tasks}</div>
                  </div>
                  <div className="bg-amber-50 p-2 rounded">
                    <div className="text-xs text-amber-700">Overdue</div>
                    <div className="text-sm font-bold text-amber-700">{emp.overdue_tasks}</div>
                  </div>
                  <div className="bg-emerald-50 p-2 rounded">
                    <div className="text-xs text-emerald-700">Done</div>
                    <div className="text-sm font-bold text-emerald-700">{emp.completed_tasks}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

