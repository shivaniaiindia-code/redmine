"use client";

import React from "react";
import { LayoutDashboard, FolderKanban, CheckSquare, UserCircle2, BarChart3 } from "lucide-react";

const TABS = [
  { id: "dashboard", label: "Home", icon: LayoutDashboard },
  { id: "projects", label: "Projects", icon: FolderKanban },
  { id: "tasks", label: "Tasks", icon: CheckSquare },
  { id: "employees", label: "People", icon: UserCircle2 },
  { id: "reports", label: "Reports", icon: BarChart3 },
];

/** Thumb-reach navigation for phones and tablets (the sidebar drawer holds everything else). */
export const MobileTabBar: React.FC<{ activeTab: string; onChange: (tab: string) => void }> = ({ activeTab, onChange }) => (
  <nav
    className="lg:hidden fixed bottom-0 inset-x-0 z-30 bg-white/95 backdrop-blur border-t border-slate-200 pb-[env(safe-area-inset-bottom)]"
    aria-label="Primary"
  >
    <ul className="grid grid-cols-5 max-w-lg mx-auto">
      {TABS.map(({ id, label, icon: Icon }) => {
        const active = activeTab === id;
        return (
          <li key={id}>
            <button
              onClick={() => onChange(id)}
              aria-current={active ? "page" : undefined}
              className={`w-full flex flex-col items-center gap-0.5 pt-2 pb-1.5 text-[10px] font-semibold transition-colors ${
                active ? "text-indigo-600" : "text-slate-500 active:text-slate-800"
              }`}
            >
              <span className={`flex items-center justify-center w-12 h-7 rounded-full transition-colors ${active ? "bg-indigo-50" : ""}`}>
                <Icon className="w-5 h-5" />
              </span>
              {label}
            </button>
          </li>
        );
      })}
    </ul>
  </nav>
);
