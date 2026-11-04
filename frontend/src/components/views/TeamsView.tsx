"use client";

import React, { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { Layers, Users, CheckCircle2, ShieldCheck, Mail, AlertTriangle, RefreshCw } from "lucide-react";

interface TeamMemberInfo {
  employee_id: string;
  name: string;
  email: string;
  role: string;
}

interface TeamItem {
  id: string;
  name: string;
  department: string;
  description: string | null;
  is_active: boolean;
  members_count: number;
  projects_count: number;
  projects: { id: string; name: string; health_status: string }[];
  project_id?: string;
  project_name?: string;
  project_code?: string;
  status?: string;
  members?: TeamMemberInfo[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const TeamsView: React.FC = () => {
  const [teams, setTeams] = useState<TeamItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const fetchTeams = async () => {
    try {
      setIsLoading(true);
      setFetchError(null);
      const res = await apiFetch(`${API_BASE_URL}/teams/`);
      if (res.ok) {
        const data = await res.json();
        setTeams(data);
      } else {
        setFetchError(`Couldn't load teams (error ${res.status}). Please try again.`);
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "Service unavailable";
      console.error("Failed to load teams", err);
      setFetchError(`Network error: Unable to load teams (${errMsg})`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTeams();
  }, []);

  const visibleTeams = teams.filter(
    (t) => (t.members_count || t.members?.length || 0) > 0
  );

  const getRoleBadgeColor = (role: string) => {
    const r = role.toLowerCase();
    if (r.includes("speech") || r.includes("asr")) {
      return "bg-purple-50 text-purple-700 border-purple-200";
    }
    if (r.includes("invoice") || r.includes("ai")) {
      return "bg-indigo-50 text-indigo-700 border-indigo-200";
    }
    if (r.includes("admin") || r.includes("lead") || r.includes("manager")) {
      return "bg-rose-50 text-rose-700 border-rose-200";
    }
    if (r.includes("dev") || r.includes("engineer")) {
      return "bg-blue-50 text-blue-700 border-blue-200";
    }
    return "bg-slate-100 text-slate-700 border-slate-200";
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="bg-white p-4 sm:p-5 rounded-xl border border-slate-200/80 shadow-sm">
        <h1 className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">
          <Layers className="w-5 h-5 sm:w-6 sm:h-6 text-indigo-600 shrink-0" />
          Project Delivery Teams & Role Allocations
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Project-wise teams based on live Redmine project memberships and functional role allocations
        </p>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-slate-400">Loading delivery teams...</div>
      ) : fetchError ? (
        <div className="p-8 bg-rose-50 border border-rose-200 rounded-xl text-center space-y-3">
          <div className="flex items-center justify-center gap-2 text-rose-700 font-semibold text-sm">
            <AlertTriangle className="w-5 h-5 text-rose-600" />
            <span>Unable to Load Teams</span>
          </div>
          <p className="text-xs text-rose-600 max-w-lg mx-auto">{fetchError}</p>
          <button
            onClick={fetchTeams}
            className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-all inline-flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Retry Fetch
          </button>
        </div>
      ) : visibleTeams.length === 0 ? (
        <div className="p-12 text-center text-slate-400">No teams found. Click &quot;Sync Redmine Now&quot; to populate.</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-5">
          {visibleTeams.map((team) => (
            <div
              key={team.id}
              className="bg-white rounded-xl border border-slate-200/80 p-4 sm:p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between min-w-0 overflow-hidden"
            >
              <div className="w-full min-w-0">
                <div className="flex items-center justify-between gap-2 mb-2 w-full min-w-0">
                  <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-100">
                    {team.project_code || team.department}
                  </span>
                  <span className="inline-flex shrink-0 whitespace-nowrap items-center gap-1 text-xs text-emerald-600 font-semibold">
                    <CheckCircle2 className="w-3.5 h-3.5" /> {team.status || (team.is_active ? "Active" : "Archived")}
                  </span>
                </div>

                <h3 className="text-base font-bold text-slate-900 mb-1">
                  {team.project_name || team.name}
                </h3>
                <p className="text-xs text-slate-500 line-clamp-2 mb-4">
                  {team.description || `Delivery team assigned to ${team.project_name || team.name}`}
                </p>

                {/* Team Members List & Redmine Roles */}
                <div className="space-y-2 mb-4">
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-700 border-b border-slate-100 pb-1.5">
                    <span>Allocated Members ({team.members?.length ?? team.members_count}):</span>
                    <span className="text-[11px] text-slate-400">Redmine Role</span>
                  </div>

                  {team.members && team.members.length > 0 ? (
                    <div className="space-y-1.5 max-h-60 overflow-y-auto pr-1">
                      {team.members.map((member) => (
                        <div
                          key={member.employee_id}
                          className="flex items-center justify-between gap-2 p-2 bg-slate-50/80 hover:bg-slate-100/80 rounded-lg border border-slate-100 transition-colors"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <div className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 font-bold text-[10px] flex items-center justify-center shrink-0">
                              {member.name.split(" ").map((n) => n[0]).join("")}
                            </div>
                            <div className="min-w-0">
                              <p className="text-xs font-semibold text-slate-800 truncate">{member.name}</p>
                              <p className="text-[10px] text-slate-400 truncate flex items-center gap-1">
                                <Mail className="w-2.5 h-2.5" />
                                {member.email}
                              </p>
                            </div>
                          </div>
                          <span
                            className={`text-[11px] font-medium px-2 py-0.5 rounded border shrink-0 ${getRoleBadgeColor(
                              member.role
                            )}`}
                          >
                            {member.role}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : team.projects && team.projects.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {team.projects.map((p) => (
                        <span
                          key={p.id}
                          className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded border border-indigo-100 font-medium"
                        >
                          {p.name}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-slate-400 italic py-2">No team members allocated to this project yet.</div>
                  )}
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
                <div className="flex items-center gap-1.5 font-medium">
                  <Users className="w-4 h-4 text-slate-400" />
                  <span>{team.members?.length ?? team.members_count} Members</span>
                </div>
                <div className="flex items-center gap-1 text-slate-500">
                  <ShieldCheck className="w-4 h-4 text-indigo-500" />
                  <span>Synced from Redmine</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

