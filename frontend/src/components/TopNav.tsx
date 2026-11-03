"use client";

import React, { useState } from "react";
import { Search, Sparkles, Bell } from "lucide-react";

interface TopNavProps {
  unreadCount: number;
  onOpenNotifications: () => void;
  onOpenAI: () => void;
  onSearchClick: () => void;
}

export const TopNav: React.FC<TopNavProps> = ({
  unreadCount,
  onOpenNotifications,
  onOpenAI,
  onSearchClick
}) => {
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  return (
    <header className="h-16 bg-white border-b border-slate-200 sticky top-0 z-30 px-6 flex items-center justify-between">
      {/* Omni-Search Bar */}
      <div className="flex-1 max-w-xl">
        <div
          onClick={onSearchClick}
          className="cursor-pointer flex items-center justify-between bg-slate-50 border border-slate-200/90 hover:border-indigo-300 rounded-xl px-3.5 py-2 text-xs text-slate-500 shadow-sm transition-all"
        >
          <div className="flex items-center gap-2.5">
            <Search className="w-4 h-4 text-slate-400" />
            <span>Search projects, employees, tasks...</span>
          </div>
          <kbd className="bg-white border border-slate-200 text-slate-500 text-[10px] font-semibold px-1.5 py-0.5 rounded shadow-2xs">
            Ctrl + K
          </kbd>
        </div>
      </div>

      {/* Right Action Icons */}
      <div className="flex items-center gap-3">
        {/* AI Assistant Button */}
        <button
          onClick={onOpenAI}
          className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-purple-200 bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-semibold shadow-2xs transition-all hover:shadow-sm"
        >
          <Sparkles className="w-3.5 h-3.5 text-purple-600 animate-pulse" />
          <span>AI Assistant</span>
        </button>

        {/* System Notification Bell */}
        <button
          onClick={onOpenNotifications}
          className="relative p-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-all"
          title="System Notification Bar (Mirrored to Admin Google Chat)"
        >
          <Bell className="w-5 h-5" />
          {unreadCount > 0 && (
            <span className="absolute top-1.5 right-1.5 w-4 h-4 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center animate-bounce">
              {unreadCount}
            </span>
          )}
        </button>

        {/* User Profile Avatar */}
        <div className="relative">
          <button
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            className="w-9 h-9 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold flex items-center justify-center shadow-md shadow-indigo-600/20 text-sm transition-all"
          >
            A
          </button>

          {userMenuOpen && (
            <div className="absolute right-0 mt-2 w-52 bg-white rounded-xl shadow-xl border border-slate-100 py-2 z-50 text-xs">
              <div className="px-4 py-2 border-b border-slate-100">
                <p className="font-semibold text-slate-900">Anil Abhange</p>
                <p className="text-[11px] text-slate-500">Super Administrator</p>
                <p className="text-[10px] text-slate-400">admin@company.com</p>
              </div>
              <button
                onClick={() => setUserMenuOpen(false)}
                className="w-full text-left px-4 py-2 text-slate-600 hover:bg-slate-50 transition-colors"
              >
                Profile & Settings
              </button>
              <button
                onClick={() => setUserMenuOpen(false)}
                className="w-full text-left px-4 py-2 text-red-600 hover:bg-red-50 transition-colors"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

