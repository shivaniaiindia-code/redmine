"use client";

import React from "react";
import { AlertTriangle, AlertCircle, Info, Calendar, ArrowRight, Check } from "lucide-react";

interface NotificationItem {
  id: string;
  title: string;
  subtitle: string;
  time_ago: string;
  severity: string;
  deep_link: string;
  is_mirrored_to_admin_chat?: boolean;
}

export const NotificationsFeed: React.FC<{
  notifications: NotificationItem[];
  unreadCount?: number;
  onViewAll?: () => void;
}> = ({ notifications, unreadCount = 12, onViewAll }) => {
  const getIcon = (severity: string, title: string) => {
    if (title.toLowerCase().includes("meeting")) {
      return (
        <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center text-purple-600">
          <Calendar className="w-4 h-4" />
        </div>
      );
    }

    switch (severity) {
      case "CRITICAL":
        return (
          <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center text-red-500">
            <AlertTriangle className="w-4 h-4" />
          </div>
        );
      case "WARNING":
        return (
          <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center text-amber-600">
            <AlertCircle className="w-4 h-4" />
          </div>
        );
      default:
        return (
          <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600">
            <Info className="w-4 h-4" />
          </div>
        );
    }
  };

  return (
    <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-2xs h-full flex flex-col justify-between">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-slate-900 text-sm">Notifications</h3>
          {unreadCount > 0 && (
            <span className="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
              {unreadCount}
            </span>
          )}
        </div>
        <button
          onClick={onViewAll}
          className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold flex items-center gap-1 transition-colors"
        >
          View All <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="space-y-3.5">
        {notifications.map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between p-2 rounded-xl hover:bg-slate-50 border border-transparent hover:border-slate-100 transition-all cursor-pointer"
          >
            <div className="flex items-center gap-3">
              {getIcon(item.severity, item.title)}
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

      {/* Admin Google Chat Mirroring Pill */}
      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
        <span className="flex items-center gap-1.5 font-medium text-emerald-700">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          1:1 Admin Google Chat Mirroring
        </span>
        <span className="text-[10px] bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full font-semibold border border-emerald-200/60">
          Active ✓
        </span>
      </div>
    </div>
  );
};

