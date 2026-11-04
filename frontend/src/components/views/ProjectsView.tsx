"use client";

import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { FolderGit2, AlertTriangle, CheckCircle, RefreshCw, ShieldAlert } from "lucide-react";

interface ProjectItem {
  id: string;
  name: string;
  code: string;
  description: string | null;
  status: string;
  health_status: string;
  health_reason: string | null;
  progress_percentage: number;
  total_tasks: number;
  overdue_tasks: number;
  blocked_tasks: number;
  completed_tasks: number;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const ProjectsView: React.FC = () => {
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);

  const fetchProjects = async () => {
    try {
      setIsLoading(true);
      setFetchError(null);
      const res = await apiFetch(`${API_BASE_URL}/projects/`);
      if (!res.ok) {
        if (res.status === 401) {
          setFetchError("Your session has expired. Please sign in again.");
        } else {
          setFetchError(`Couldn't load projects (error ${res.status}). Please try again.`);
        }
        return;
      }
      const data = await res.json();
      setProjects(data);
    } catch (err: unknown) {
      console.error("Failed to load projects", err);
      setFetchError("Couldn't reach the server. Please check your connection and try again.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleSyncNow = async () => {
    setIsSyncing(true);
    setSyncStatus("Connecting to https://redmine.aiindia.ai...");
    try {
      const res = await apiFetch(`${API_BASE_URL}/redmine/sync/trigger`, {
        method: "POST"
      });
      if (res.ok) {
        const data = await res.json();
        setSyncStatus(`Sync Successful: ${data.summary.projects_synced} projects, ${data.summary.tasks_synced} tasks, ${data.summary.alerts_generated} alerts generated.`);
        await fetchProjects();
      } else {
        setSyncStatus("Sync failed. Check Redmine configuration.");
      }
    } catch {
      setSyncStatus("Couldn't reach the server. Please try again.");
    } finally {
      setIsSyncing(false);
      setTimeout(() => setSyncStatus(null), 6000);
    }
  };

  const getHealthBadge = (health: string) => {
    switch (health) {
      case "ON_TRACK":
        return <span className="inline-flex shrink-0 whitespace-nowrap items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200"><CheckCircle className="w-3.5 h-3.5" /> On Track</span>;
      case "AT_RISK":
        return <span className="inline-flex shrink-0 whitespace-nowrap items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200"><AlertTriangle className="w-3.5 h-3.5" /> At Risk</span>;
      case "BLOCKED":
        return <span className="inline-flex shrink-0 whitespace-nowrap items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200"><ShieldAlert className="w-3.5 h-3.5" /> Blocked</span>;
      default:
        return <span className="inline-flex shrink-0 whitespace-nowrap items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-50 text-slate-700 border border-slate-200">{health}</span>;
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 bg-white p-4 sm:p-5 rounded-xl border border-slate-200/80 shadow-sm">
        <div>
          <h1 className="text-lg sm:text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">
            <FolderGit2 className="w-5 h-5 sm:w-6 sm:h-6 text-indigo-600 shrink-0" />
            Company Projects Portfolio
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1 break-words">
            Real-time synchronization with Redmine (<code className="break-all text-xs bg-slate-100 px-1.5 py-0.5 rounded text-indigo-600 font-mono">https://redmine.aiindia.ai</code>)
          </p>
        </div>

        <button
          onClick={handleSyncNow}
          disabled={isSyncing}
          className="inline-flex items-center justify-center gap-2 w-full sm:w-auto px-4 py-2.5 sm:py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg shadow-sm transition-all disabled:opacity-60"
        >
          <RefreshCw className={`w-4 h-4 ${isSyncing ? "animate-spin" : ""}`} />
          {isSyncing ? "Syncing Redmine..." : "Sync Redmine Now"}
        </button>
      </div>

      {syncStatus && (
        <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-lg text-sm text-indigo-800 font-medium animate-fadeIn">
          {syncStatus}
        </div>
      )}

      {/* Projects Grid */}
      {isLoading ? (
        <div className="p-12 text-center text-slate-400">Loading company projects...</div>
      ) : fetchError ? (
        <div className="p-8 bg-rose-50 border border-rose-200 rounded-xl text-center space-y-3">
          <div className="flex items-center justify-center gap-2 text-rose-700 font-semibold text-sm">
            <AlertTriangle className="w-5 h-5 text-rose-600" />
            <span>Unable to Load Projects</span>
          </div>
          <p className="text-xs text-rose-600 max-w-lg mx-auto">{fetchError}</p>
          <button
            onClick={fetchProjects}
            className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-all inline-flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Retry Fetch
          </button>
        </div>
      ) : projects.length === 0 ? (
        <div className="p-12 text-center text-slate-400">No projects found. Click "Sync Redmine Now" to populate.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 sm:gap-5">
          {projects.map((proj) => (
            <div
              key={proj.id}
              className="bg-white rounded-xl border border-slate-200/80 p-4 sm:p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between min-w-0 overflow-hidden"
            >
              <div className="w-full min-w-0">
                <div className="flex items-start justify-between gap-2 mb-2 w-full min-w-0">
                  <span className="min-w-0 truncate text-xs font-mono font-semibold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100">
                    {proj.code}
                  </span>
                  {getHealthBadge(proj.health_status)}
                </div>

                <h3 className="text-base font-bold text-slate-900 line-clamp-1 mb-1" title={proj.name}>
                  {proj.name}
                </h3>
                <p className="text-xs text-slate-500 line-clamp-2 mb-4">
                  {proj.description || "No project description provided."}
                </p>

                {proj.health_reason && (
                  <div className="text-xs bg-slate-50 border border-slate-100 p-2 rounded mb-4 text-slate-600">
                    <span className="font-semibold text-slate-700">Health Indicator: </span>
                    {proj.health_reason}
                  </div>
                )}
              </div>

              <div className="pt-3 border-t border-slate-100 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-xs text-slate-600">
                  <span>Tasks ({proj.total_tasks})</span>
                  <div className="flex items-center gap-2">
                    {proj.overdue_tasks > 0 && (
                      <span className="text-rose-600 font-semibold">{proj.overdue_tasks} overdue</span>
                    )}
                    {proj.blocked_tasks > 0 && (
                      <span className="text-amber-600 font-semibold">{proj.blocked_tasks} blocked</span>
                    )}
                    <span className="text-emerald-600 font-semibold">{proj.completed_tasks} done</span>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-indigo-600 h-2 rounded-full transition-all duration-500"
                    style={{
                      width: `${proj.total_tasks > 0 ? Math.round((proj.completed_tasks / proj.total_tasks) * 100) : 0}%`
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

