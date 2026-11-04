"use client";

import React, { useEffect, useState } from "react";
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
  Check,
  X,
} from "lucide-react";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  unreadCount?: number;
  onOpenNotifications: () => void;
  onOpenAI: () => void;
  /** Live Redmine sync indicator; null while loading */
  redmineSync?: { ok: boolean; label: string; detail: string } | null;
  /** Phones/tablets: the sidebar is a slide-in drawer */
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
  /** Whether the current user has administrator or management privileges */
  isAdmin?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  unreadCount = 0,
  onOpenNotifications,
  onOpenAI,
  redmineSync = null,
  mobileOpen = false,
  onCloseMobile,
  isAdmin = false,
}) => {
  const [integrationsOpen, setIntegrationsOpen] = useState(true);

  // Esc closes the drawer; the page behind does not scroll while it is open
  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onCloseMobile?.();
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [mobileOpen, onCloseMobile]);

  const go = (fn: () => void) => {
    fn();
    onCloseMobile?.();
  };

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "projects", label: "Projects", icon: FolderKanban },
    { id: "teams", label: "Teams", icon: Users2 },
    { id: "employees", label: "Employees", icon: UserCircle2 },
    { id: "tasks", label: "Tasks", icon: CheckSquare },
    { id: "notifications", label: "Notifications", icon: Bell, badge: unreadCount, onClick: onOpenNotifications },
    { id: "ai-assistant", label: "AI Assistant", icon: Sparkles, onClick: onOpenAI },
    { id: "reports", label: "Reports & Analytics", icon: BarChart3 },
  ];

  const itemClass = (active: boolean) =>
    `w-full flex items-center justify-between px-3.5 py-3 lg:py-2.5 rounded-xl text-sm lg:text-xs font-medium transition-all ${
      active
        ? "bg-indigo-600 text-white font-semibold shadow-lg shadow-indigo-600/30"
        : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
    }`;

  const content = (
    <>
      {/* Brand Header */}
      <div className="p-5 flex items-center gap-3 border-b border-slate-800/80">
        {/* eslint-disable-next-line @next/next/no-img-element -- static brand asset from /public */}
        <img
          src="/aii-logo.png"
          alt="AI India Innovations logo"
          width={40}
          height={40}
          className="w-10 h-10 rounded-xl bg-white p-0.5 object-contain shadow-md shadow-indigo-500/20 shrink-0"
        />
        <div className="min-w-0 flex-1">
          <h1 className="font-bold text-white text-sm tracking-tight leading-tight">Project Manager</h1>
          <p className="text-[10px] text-slate-400 font-medium leading-tight mt-0.5">AI India Innovations</p>
        </div>
        {onCloseMobile && (
          <button
            onClick={onCloseMobile}
            className="lg:hidden p-2 -mr-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto overscroll-contain">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => go(() => (item.onClick ? item.onClick() : setActiveTab(item.id)))}
              className={itemClass(isActive)}
              aria-current={isActive ? "page" : undefined}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-slate-400"}`} />
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && item.badge > 0 && (
                <span className="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">{item.badge}</span>
              )}
            </button>
          );
        })}

        {/* Integrations & Administration (Super Admin & Company Management Only) */}
        {isAdmin && (
          <>
            <div className="pt-4">
              <button
                onClick={() => setIntegrationsOpen(!integrationsOpen)}
                className="w-full flex items-center justify-between px-3.5 py-2 text-sm lg:text-xs font-medium text-slate-400 hover:text-slate-200"
                aria-expanded={integrationsOpen}
              >
                <div className="flex items-center gap-3">
                  <Sliders className="w-4 h-4 text-slate-400" />
                  <span>Integrations</span>
                </div>
                {integrationsOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>

              {integrationsOpen && (
                <div className="mt-1 ml-7 space-y-1.5 text-sm lg:text-xs">
                  <div className="flex items-center justify-between py-1.5 px-2 rounded-lg text-slate-400">
                    <span>Redmine</span>
                    {redmineSync === null ? (
                      <span className="text-[11px] text-slate-500 font-medium">Checking…</span>
                    ) : redmineSync.ok ? (
                      <span className="flex items-center gap-1 text-[11px] text-emerald-400 font-medium" title={redmineSync.detail}>
                        {redmineSync.label} <Check className="w-3 h-3" />
                      </span>
                    ) : (
                      <span className="text-[11px] text-amber-400 font-medium" title={redmineSync.detail}>{redmineSync.label}</span>
                    )}
                  </div>
                  <button
                    onClick={() => go(() => setActiveTab("admin"))}
                    className="w-full flex items-center justify-between py-1.5 px-2 rounded-lg text-slate-400 hover:bg-slate-800/40"
                    title="Email alert settings"
                  >
                    <span>Email Alerts</span>
                    <span className="text-[11px] text-indigo-300 font-medium">Settings →</span>
                  </button>
                </div>
              )}
            </div>

            {/* Administration */}
            <div className="pt-2">
              <button onClick={() => go(() => setActiveTab("admin"))} className={itemClass(activeTab === "admin")}>
                <div className="flex items-center gap-3">
                  <Sliders className={`w-4 h-4 ${activeTab === "admin" ? "text-white" : "text-slate-400"}`} />
                  <span>Administration</span>
                </div>
              </button>
            </div>
          </>
        )}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-slate-800/80 text-[11px] text-slate-500 flex items-center gap-2 pb-[max(1rem,env(safe-area-inset-bottom))]">
        <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
        <span>Version 1.0.0</span>
      </div>
    </>
  );

  return (
    <>
      {/* Desktop: fixed column */}
      <aside className="hidden lg:flex w-64 shrink-0 bg-[#0f172a] text-slate-300 flex-col h-screen sticky top-0 border-r border-slate-800 select-none">
        {content}
      </aside>

      {/* Phones & tablets: slide-in drawer */}
      <div
        className={`lg:hidden fixed inset-0 z-50 transition-opacity duration-200 ${
          mobileOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
        aria-hidden={!mobileOpen}
      >
        <div className="absolute inset-0 bg-slate-950/50 backdrop-blur-[2px]" onClick={onCloseMobile} />
        <aside
          role="dialog"
          aria-modal="true"
          aria-label="Main menu"
          className={`absolute inset-y-0 left-0 w-[82vw] max-w-[300px] bg-[#0f172a] text-slate-300 flex flex-col shadow-2xl select-none transition-transform duration-200 ease-out ${
            mobileOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          {content}
        </aside>
      </div>
    </>
  );
};
