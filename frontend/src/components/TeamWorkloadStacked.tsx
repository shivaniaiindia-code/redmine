"use client";

import React from "react";

interface TeamWorkloadItem {
  team_name: string;
  completed: number;
  in_progress: number;
  overdue: number;
  total_tasks: number;
}

export const TeamWorkloadStacked: React.FC<{ items: TeamWorkloadItem[] }> = ({ items }) => {
  return (
    <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-2xs h-full flex flex-col justify-between">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-slate-900 text-sm">Team Workload</h3>
      </div>

      <div className="space-y-3.5 my-auto">
        {items.map((team, idx) => {
          const total = team.total_tasks || 1;
          const completedPct = (team.completed / total) * 100;
          const inProgressPct = (team.in_progress / total) * 100;
          const overduePct = (team.overdue / total) * 100;

          return (
            <div key={idx} className="space-y-1">
              <div className="flex justify-between items-center text-xs">
                <span className="font-medium text-slate-700">{team.team_name}</span>
                <span className="font-bold text-slate-900 text-[11px]">{team.total_tasks}</span>
              </div>
              <div className="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden flex">
                <div
                  className="bg-emerald-500 transition-all duration-500"
                  style={{ width: `${completedPct}%` }}
                  title={`Completed: ${team.completed}`}
                />
                <div
                  className="bg-blue-500 transition-all duration-500"
                  style={{ width: `${inProgressPct}%` }}
                  title={`In Progress: ${team.in_progress}`}
                />
                <div
                  className="bg-red-500 transition-all duration-500"
                  style={{ width: `${overduePct}%` }}
                  title={`Overdue: ${team.overdue}`}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-5 pt-3 border-t border-slate-100 text-[11px]">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
          <span className="text-slate-600">Completed</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500"></span>
          <span className="text-slate-600">In Progress</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
          <span className="text-slate-600">Overdue</span>
        </div>
      </div>
    </div>
  );
};

