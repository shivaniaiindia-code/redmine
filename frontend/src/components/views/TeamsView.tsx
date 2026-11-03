"use client";

import React, { useState, useEffect } from "react";
import { Layers, Users, FolderGit2, CheckCircle2 } from "lucide-react";

interface TeamItem {
  id: string;
  name: string;
  department: string;
  description: string | null;
  is_active: boolean;
  members_count: number;
  projects_count: number;
  projects: { id: string; name: string; health_status: string }[];
}

export const TeamsView: React.FC = () => {
  const [teams, setTeams] = useState<TeamItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchTeams = async () => {
      try {
        setIsLoading(true);
        const res = await fetch("http://localhost:8000/api/v1/teams/");
        if (res.ok) {
          const data = await res.json();
          setTeams(data);
        }
      } catch (err) {
        console.error("Failed to load teams", err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchTeams();
  }, []);

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm">
        <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <Layers className="w-6 h-6 text-indigo-600" />
          Organizational Teams & Capacity
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Workload capacity, cross-functional project assignments, and team health
        </p>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-slate-400">Loading company teams...</div>
      ) : teams.length === 0 ? (
        <div className="p-12 text-center text-slate-400">No teams found.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {teams.map((team) => (
            <div
              key={team.id}
              className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                    {team.department}
                  </span>
                  <span className="inline-flex items-center gap-1 text-xs text-emerald-600 font-semibold">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Active
                  </span>
                </div>

                <h3 className="text-base font-bold text-slate-900 mb-1">{team.name}</h3>
                <p className="text-xs text-slate-500 line-clamp-2 mb-4">
                  {team.description || "Core operational delivery team"}
                </p>

                <div className="space-y-2 mb-4">
                  <div className="text-xs font-semibold text-slate-700">Assigned Projects:</div>
                  {team.projects.length === 0 ? (
                    <div className="text-xs text-slate-400 italic">No assigned projects</div>
                  ) : (
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
                  )}
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
                <div className="flex items-center gap-1">
                  <Users className="w-3.5 h-3.5 text-slate-400" />
                  <span>{team.members_count} Members</span>
                </div>
                <div className="flex items-center gap-1">
                  <FolderGit2 className="w-3.5 h-3.5 text-slate-400" />
                  <span>{team.projects_count} Projects</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

