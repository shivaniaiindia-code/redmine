"use client";

import React, { useState } from "react";
import {
  LayoutDashboard,
  FolderKanban,
  Users2,
  UserCircle2,
  CheckSquare,
  Bell,
  Sparkles,
  BarChart3,
  Sliders,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Check
} from "lucide-react";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  unreadCount?: number;
  onOpenNotifications: () => void;
  onOpenAI: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  unreadCount = 12,
  onOpenNotifications,
  onOpenAI
}) => {
  const [integrationsOpen, setIntegrationsOpen] = useState(true);

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "projects", label: "Projects", icon: FolderKanban },
    { id: "teams", label: "Teams", icon: Users2 },
    { id: "employees", label: "Employees", icon: UserCircle2 },
    { id: "tasks", label: "Tasks", icon: CheckSquare },
    {
      id: "notifications",
      label: "Notifications",
      icon: Bell,
      badge: unreadCount,
      onClick: onOpenNotifications
    },
    {
      id: "ai-assistant",
      label: "AI Assistant",
      icon: Sparkles,
      onClick: onOpenAI
    },
    { id: "reports", label: "Reports & Analytics", icon: BarChart3 }
  ];

  return (
    <aside className="w-64 bg-[#0f172a] text-slate-300 flex flex-col h-screen sticky top-0 border-r border-slate-800 select-none">
      {/* Brand Header */}
      <div className="p-5 flex items-center gap-3 border-b border-slate-800/80">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-500 flex items-center justify-center text-white font-bold shadow-md shadow-indigo-500/20">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div>
          <h1 className="font-semibold text-white text-sm tracking-tight">
            Company Intelligence
          </h1>
          <p className="text-[10px] text-slate-400 font-medium">
            Projects · Team · Employee · Growth · AI
          </p>
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;

          return (
            <button
              key={item.id}
              onClick={() => {
                if (item.onClick) {
                  item.onClick();
                } else {
                  setActiveTab(item.id);
                }
              }}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all ${
                isActive
                  ? "bg-indigo-600 text-white font-semibold shadow-lg shadow-indigo-600/30"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-slate-400"}`} />
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && item.badge > 0 && (
                <span className="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}

        {/* Integrations Section */}
        <div className="pt-4">
          <button
            onClick={() => setIntegrationsOpen(!integrationsOpen)}
            className="w-full flex items-center justify-between px-3.5 py-2 text-xs font-medium text-slate-400 hover:text-slate-200"
          >
            <div className="flex items-center gap-3">
              <Sliders className="w-4 h-4 text-slate-400" />
              <span>Integrations</span>
            </div>
            {integrationsOpen ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>

          {integrationsOpen && (
            <div className="mt-1 ml-7 space-y-1.5 text-xs">
              <div className="flex items-center justify-between py-1 px-2 rounded-lg text-slate-400 hover:bg-slate-800/40">
                <span>Redmine</span>
                <span className="flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
                  Synced <Check className="w-3 h-3" />
                </span>
              </div>
              <div className="flex items-center justify-between py-1 px-2 rounded-lg text-slate-400 hover:bg-slate-800/40">
                <span>Google Chat</span>
                <span className="flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
                  Connected <Check className="w-3 h-3" />
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Administration */}
        <div className="pt-2">
          <button
            onClick={() => setActiveTab("admin")}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all ${
              activeTab === "admin"
                ? "bg-indigo-600 text-white font-semibold shadow-lg shadow-indigo-600/30"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
            }`}
          >
            <Sliders className="w-4 h-4 text-slate-400" />
            <span>Administration</span>
          </button>
        </div>
      </nav>

      {/* Footer Version Tag */}
      <div className="p-4 border-t border-slate-800/80 text-[11px] text-slate-500 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
        <span>CIP v1.0.0</span>
      </div>
    </aside>
  );
};

