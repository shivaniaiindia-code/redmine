"use client";

import React from "react";
import { CheckCircle2, FileText, AlertCircle, UserPlus, ArrowRight } from "lucide-react";

interface ActivityItem {
  id: string;
  title: string;
  subtitle: string;
  time_ago: string;
  activity_type: string;
}

export const ActivitiesFeed: React.FC<{
  activities: ActivityItem[];
  onViewAll?: () => void;
}> = ({ activities, onViewAll }) => {
  const getIcon = (type: string) => {
    switch (type) {
      case "task_completed":
        return (
          <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600">
            <CheckCircle2 className="w-4 h-4" />
          </div>
        );
      case "task_assigned":
        return (
          <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600">
            <FileText className="w-4 h-4" />
          </div>
        );
      case "status_updated":
        return (
          <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center text-purple-600">
            <AlertCircle className="w-4 h-4" />
          </div>
        );
      default:
        return (
          <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600">
            <UserPlus className="w-4 h-4" />
          </div>
        );
    }
  };

  return (
    <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-2xs h-full flex flex-col justify-between">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-slate-900 text-sm">Recent Activities</h3>
        <button
          onClick={onViewAll}
          className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold flex items-center gap-1 transition-colors"
        >
          View All <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="space-y-3.5">
        {activities.map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between p-2 rounded-xl hover:bg-slate-50 border border-transparent hover:border-slate-100 transition-all"
          >
            <div className="flex items-center gap-3">
              {getIcon(item.activity_type)}
              <div>
                <h4 className="text-xs font-semibold text-slate-900 leading-tight">{item.title}</h4>
                <p className="text-[10px] text-slate-500 mt-0.5">{item.subtitle}</p>
              </div>
            </div>
            <span className="text-[10px] text-slate-400 font-medium whitespace-nowrap ml-2">
              {item.time_ago}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

