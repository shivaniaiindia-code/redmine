"use client";

import React from "react";
import { FolderKanban, ArrowRight } from "lucide-react";

interface DeadlineItem {
  id: string;
  project_name: string;
  team_name: string;
  deadline_text: string;
  severity_pill: string;
  severity_type: string;
}

export const DeadlinesFeed: React.FC<{
  deadlines: DeadlineItem[];
  onViewAll?: () => void;
}> = ({ deadlines, onViewAll }) => {
  const getPillStyle = (type: string) => {
    switch (type) {
      case "critical":
        return "bg-red-50 text-red-600 border border-red-200/80 font-semibold";
      case "warning":
        return "bg-amber-50 text-amber-700 border border-amber-200/80 font-semibold";
      default:
        return "bg-indigo-50 text-indigo-700 border border-indigo-200/80 font-medium";
    }
  };

  return (
    <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-2xs h-full flex flex-col justify-between">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-slate-900 text-sm">Upcoming Deadlines</h3>
        <button
          onClick={onViewAll}
          className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold flex items-center gap-1 transition-colors"
        >
          View All <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="space-y-3.5">
        {deadlines.map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between p-2.5 rounded-xl hover:bg-slate-50 border border-transparent hover:border-slate-100 transition-all"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600 flex-shrink-0">
                <FolderKanban className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-slate-900">{item.project_name}</h4>
                <p className="text-[10px] text-slate-500">
                  {item.team_name} · <span className="text-slate-600 font-medium">{item.deadline_text}</span>
                </p>
              </div>
            </div>
            <span className={`text-[10px] px-2.5 py-0.5 rounded-full ${getPillStyle(item.severity_type)}`}>
              {item.severity_pill}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

