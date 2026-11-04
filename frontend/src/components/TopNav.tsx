"use client";

import React, { useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import {
  Search,
  Sparkles,
  Bell,
  RefreshCw,
  Menu,
  Sliders,
  LogIn,
  LogOut,
  UserCheck,
  ShieldCheck,
  ChevronDown,
} from "lucide-react";

export interface CurrentUserProfile {
  id: string;
  email: string;
  role: { id: string; name: string };
  employee?: {
    first_name: string;
    last_name: string;
    job_title: string;
    department: string;
    avatar_url?: string | null;
  } | null;
  is_active: boolean;
  approval_status?: "APPROVED" | "PENDING" | "REJECTED" | string;
}

interface TopNavProps {
  unreadCount: number;
  currentUser?: CurrentUserProfile | null;
  onOpenNotifications: () => void;
  onOpenAI: () => void;
  onSearchClick: () => void;
  onSyncComplete?: () => void;
  onOpenMenu?: () => void;
  onNavigate?: (view: string) => void;
  onOpenAuthModal?: (tab?: "signin" | "signup") => void;
  onSignOut?: () => void;
  isAdmin?: boolean;
  isSuperAdmin?: boolean;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const TopNav: React.FC<TopNavProps> = ({
  unreadCount,
  currentUser,
  onOpenNotifications,
  onOpenAI,
  onSearchClick,
  onSyncComplete,
  onOpenMenu,
  onNavigate,
  onOpenAuthModal,
  onSignOut,
  isAdmin = false,
  isSuperAdmin = false,
}) => {
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close user menu on outside click
  useEffect(() => {
    if (!userMenuOpen) return;
    const onDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setUserMenuOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [userMenuOpen]);

  const handleSyncRedmine = async () => {
    setIsSyncing(true);
    setSyncStatus("Syncing…");
    try {
      const res = await apiFetch(`${API_BASE_URL}/redmine/sync/trigger`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        const pCount = data.summary?.projects_synced ?? 0;
        const tCount = data.summary?.tasks_synced ?? 0;
        setSyncStatus(`Synced ${pCount} projects, ${tCount} tasks`);
        onSyncComplete?.();
      } else {
        setSyncStatus("Sync failed — try again");
      }
    } catch {
      setSyncStatus("Couldn't reach the server");
    } finally {
      setIsSyncing(false);
      setTimeout(() => setSyncStatus(null), 5000);
    }
  };

  const displayName = currentUser?.employee
    ? `${currentUser.employee.first_name} ${currentUser.employee.last_name}`.trim()
    : currentUser?.email
    ? currentUser.email.split("@")[0].toUpperCase()
    : "";

  const initials = displayName
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((n) => n[0].toUpperCase())
    .join("") || "A";

  const ROLE_LABELS: Record<string, string> = {
    SUPER_ADMIN: "Super Admin",
    COMPANY_MANAGEMENT: "Company Management",
    PROJECT_MANAGER: "Project Manager",
    TEAM_LEAD: "Team Lead",
    EMPLOYEE: "Employee",
  };
  const roleName = ROLE_LABELS[currentUser?.role?.name ?? ""] ?? currentUser?.role?.name ?? "";

  const iconBtn =
    "relative inline-flex items-center justify-center w-10 h-10 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 active:bg-slate-200 transition-all";

  return (
    <header className="h-14 lg:h-16 bg-white/95 backdrop-blur border-b border-slate-200 sticky top-0 z-30 px-2 sm:px-4 lg:px-6 flex items-center gap-1 sm:gap-3 pt-[env(safe-area-inset-top)] box-content lg:box-border">
      {/* Menu (phones & tablets) */}
      <button onClick={onOpenMenu} className={`${iconBtn} lg:hidden`} aria-label="Open menu">
        <Menu className="w-5 h-5" />
      </button>

      {/* Brand (phones & tablets) */}
      <div className="lg:hidden flex items-center gap-2 min-w-0 mr-auto">
        {/* eslint-disable-next-line @next/next/no-img-element -- static brand asset */}
        <img src="/aii-logo.png" alt="" width={28} height={28} className="w-7 h-7 rounded-lg object-contain shrink-0" />
        <span className="font-bold text-sm text-slate-900 truncate">Project Manager</span>
      </div>

      {/* Search */}
      <div className="hidden md:block flex-1 max-w-xl">
        <button
          onClick={onSearchClick}
          className="w-full flex items-center justify-between bg-slate-50 border border-slate-200/90 hover:border-indigo-300 rounded-xl px-3.5 py-2 text-xs text-slate-500 shadow-sm transition-all"
        >
          <span className="flex items-center gap-2.5 min-w-0">
            <Search className="w-4 h-4 text-slate-400 shrink-0" />
            <span className="truncate">Search projects, employees, tasks…</span>
          </span>
          <kbd className="hidden lg:inline bg-white border border-slate-200 text-slate-500 text-[10px] font-semibold px-1.5 py-0.5 rounded">
            Ctrl + K
          </kbd>
        </button>
      </div>

      <div className="flex items-center gap-0.5 sm:gap-2 lg:gap-3 md:ml-auto">
        <button onClick={onSearchClick} className={`${iconBtn} md:hidden`} aria-label="Search">
          <Search className="w-5 h-5" />
        </button>

        {/* Sync status */}
        {syncStatus && (
          <span
            role="status"
            className="fixed lg:static top-[calc(3.75rem+env(safe-area-inset-top))] left-1/2 -translate-x-1/2 lg:translate-x-0 z-40 whitespace-nowrap text-xs px-3 py-1.5 lg:px-2.5 lg:py-1 rounded-lg bg-indigo-50 border border-indigo-200 text-indigo-700 font-medium shadow-md lg:shadow-none"
          >
            {syncStatus}
          </span>
        )}

        <button
          onClick={handleSyncRedmine}
          disabled={isSyncing}
          className="inline-flex items-center justify-center gap-1.5 w-10 h-10 lg:w-auto lg:h-auto lg:px-3 lg:py-1.5 rounded-xl lg:border border-indigo-200 lg:bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold transition-all disabled:opacity-60"
          title="Sync Redmine now"
          aria-label="Sync Redmine now"
        >
          <RefreshCw className={`w-[18px] h-[18px] lg:w-3.5 lg:h-3.5 text-indigo-600 ${isSyncing ? "animate-spin" : ""}`} />
          <span className="hidden lg:inline">{isSyncing ? "Syncing…" : "Sync Redmine Now"}</span>
        </button>

        <button
          onClick={onOpenAI}
          className="inline-flex items-center justify-center gap-2 w-10 h-10 sm:w-auto sm:h-auto sm:px-3 sm:py-1.5 rounded-xl sm:border border-purple-200 sm:bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-semibold transition-all"
          aria-label="AI Assistant"
        >
          <Sparkles className="w-[18px] h-[18px] sm:w-3.5 sm:h-3.5 text-purple-600" />
          <span className="hidden sm:inline">AI Assistant</span>
        </button>

        <button onClick={onOpenNotifications} className={iconBtn} aria-label={`Notifications (${unreadCount} unread)`}>
          <Bell className="w-5 h-5" />
          {unreadCount > 0 && (
            <span className="absolute top-1 right-1 min-w-4 h-4 px-1 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center">
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          )}
        </button>

        {/* User / Authentication Dropdown */}
        <div className="relative hidden sm:block" ref={menuRef}>
          <button
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            className="flex items-center gap-2 p-1 pl-1.5 pr-2.5 rounded-xl border border-slate-200 hover:border-indigo-300 hover:bg-slate-50 transition-all text-left"
            aria-label="User Account"
            aria-expanded={userMenuOpen}
          >
            {currentUser?.employee?.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={currentUser.employee.avatar_url}
                alt={displayName}
                className="w-8 h-8 rounded-lg object-cover border border-slate-200"
              />
            ) : (
              <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white font-bold flex items-center justify-center text-xs shadow-xs">
                {initials}
              </div>
            )}
            <div className="hidden lg:block min-w-0 text-left">
              <p className="text-xs font-bold text-slate-800 leading-tight truncate max-w-[120px]">
                {displayName}
              </p>
              <p className="text-[10px] text-indigo-600 font-semibold leading-tight">
                {roleName === "SUPER_ADMIN" ? "Super Admin" : roleName}
              </p>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          {userMenuOpen && (
            <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-xl border border-slate-200/90 py-2 z-50 text-xs animate-in fade-in zoom-in-95 duration-150">
              <div className="px-4 py-2.5 border-b border-slate-100">
                <div className="flex items-center gap-1.5 mb-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
                  <span className="font-semibold text-slate-900">{displayName}</span>
                </div>
                <p className="text-[11px] text-slate-500 truncate">{currentUser?.email}</p>
                <div className="mt-1.5 flex items-center gap-1.5">
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                    {roleName}
                  </span>
                </div>
              </div>

              <div className="py-1">
                {isAdmin && (
                  <button
                    onClick={() => {
                      setUserMenuOpen(false);
                      onNavigate?.("admin");
                    }}
                    className="w-full flex items-center gap-2 text-left px-4 py-2 text-slate-700 hover:bg-slate-50 transition-colors"
                  >
                    <Sliders className="w-3.5 h-3.5 text-slate-400" />
                    <span>Admin & Access Control</span>
                  </button>
                )}

                <button
                  onClick={() => {
                    setUserMenuOpen(false);
                    onOpenAuthModal?.("signin");
                  }}
                  className="w-full flex items-center gap-2 text-left px-4 py-2 text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  <LogIn className="w-3.5 h-3.5 text-slate-400" />
                  <span>Sign In / Switch Account</span>
                </button>

                {isSuperAdmin && (
                  <button
                    onClick={() => {
                      setUserMenuOpen(false);
                      onOpenAuthModal?.("signup");
                    }}
                    className="w-full flex items-center gap-2 text-left px-4 py-2 text-slate-700 hover:bg-slate-50 transition-colors"
                  >
                    <UserCheck className="w-3.5 h-3.5 text-slate-400" />
                    <span>Register New Account</span>
                  </button>
                )}
              </div>

              {onSignOut && (
                <div className="pt-1 border-t border-slate-100">
                  <button
                    onClick={() => {
                      setUserMenuOpen(false);
                      onSignOut();
                    }}
                    className="w-full flex items-center gap-2 text-left px-4 py-2 text-rose-600 hover:bg-rose-50 transition-colors"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Sign Out</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
