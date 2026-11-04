"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { ShieldAlert, Loader2, WifiOff } from "lucide-react";
import { API_BASE_URL, apiFetch, getToken, clearToken, UNAUTHORIZED_EVENT } from "@/lib/api";
import { Sidebar } from "@/components/Sidebar";
import { TopNav, type CurrentUserProfile } from "@/components/TopNav";
import { MobileTabBar } from "@/components/MobileTabBar";
import { AIAssistantDrawer } from "@/components/AIAssistantDrawer";
import { NotificationModal } from "@/components/NotificationModal";
import { OmniSearchModal } from "@/components/OmniSearchModal";
import { AuthModal } from "@/components/AuthModal";
import { PendingApprovalScreen } from "@/components/PendingApprovalScreen";
import { ProjectsView } from "@/components/views/ProjectsView";
import { TasksView } from "@/components/views/TasksView";
import { TeamsView } from "@/components/views/TeamsView";
import { EmployeesView } from "@/components/views/EmployeesView";
import { AdminView } from "@/components/views/AdminView";
import { ReportsView } from "@/components/views/ReportsView";
import { DashboardView } from "@/components/views/DashboardView";
import type { NotificationCategory } from "@/components/NotificationModal";

type AuthState = "checking" | "signedIn" | "signedOut" | "offline";

export default function Home() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [isAIModalOpen, setIsAIModalOpen] = useState(false);
  const [isNotifModalOpen, setIsNotifModalOpen] = useState(false);
  const [isSearchModalOpen, setIsSearchModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalTab, setAuthModalTab] = useState<"signin" | "signup">("signin");
  const [currentUser, setCurrentUser] = useState<CurrentUserProfile | null>(null);
  const [authState, setAuthState] = useState<AuthState>("checking");
  // Deep link from an alert email, applied once the user is signed in
  const pendingDeepLink = useRef<URLSearchParams | null>(null);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);
  const [redmineSync, setRedmineSync] = useState<{ ok: boolean; label: string; detail: string } | null>(null);
  const [notifDeepLink, setNotifDeepLink] = useState<{ category: NotificationCategory; id: string | null }>({
    category: "all",
    id: null,
  });

  // Role-Based Access Control:
  // Super Admin: Full system access, credentials, user roles and activation
  // Company Management: High-level overview, talent/team analytics, user directory visibility
  // Project Manager / Team Lead / Employee: Workspace delivery views only (Administration locked)
  const userRole = currentUser?.role?.name || "";
  const isSuperAdmin = userRole === "SUPER_ADMIN";
  const hasAdminAccess = isSuperAdmin || userRole === "COMPANY_MANAGEMENT";
  // New sign-ups see nothing until a Super Admin / Company Management approves them
  const isApproved = (currentUser?.approval_status ?? "APPROVED") === "APPROVED";

  // Load current authenticated user profile
  const loadCurrentUser = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setCurrentUser(null);
      setAuthState("signedOut");
      return;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        setCurrentUser(await res.json());
        setAuthState("signedIn");
      } else {
        // Expired / invalid token or deactivated account
        clearToken();
        setCurrentUser(null);
        setAuthState("signedOut");
      }
    } catch {
      setAuthState("offline");
    }
  }, []);

  // Unread badge (bell + sidebar) — refreshed every 15 s so new alerts appear without reloading
  const loadLiveMetrics = async () => {
    try {
      const [summaryRes, syncRes] = await Promise.all([
        apiFetch(`${API_BASE_URL}/notifications/summary`),
        apiFetch(`${API_BASE_URL}/redmine/status`),
      ]);
      if (summaryRes.ok) {
        const summary = await summaryRes.json();
        setUnreadCount(summary?.all?.unread ?? 0);
      }
      if (syncRes.ok) {
        const s = await syncRes.json();
        const last = s.last_synced_at && s.last_synced_at !== "Never"
          ? new Date(String(s.last_synced_at).replace(" UTC", "Z").replace(" ", "T"))
          : null;
        const mins = last ? Math.round((Date.now() - last.getTime()) / 60000) : null;
        const stale = mins === null || mins > Math.max(3, ((s.auto_sync_interval_seconds ?? 60) / 60) * 3);
        setRedmineSync({
          ok: !!s.connected && !stale,
          label: !s.connected ? "Offline" : s.syncing_now ? "Syncing…" : mins === null ? "Never synced" : mins < 1 ? "Synced now" : `Synced ${mins}m ago`,
          detail: `Last sync ${s.last_synced_at}`,
        });
      }
    } catch {
      setRedmineSync({ ok: false, label: "Offline", detail: "Server not reachable" });
    }
  };

  const handleSignOut = useCallback(() => {
    clearToken();
    setCurrentUser(null);
    setAuthState("signedOut");
    // Reset the workspace so the next user starts clean on the dashboard
    setActiveTab("dashboard");
    setIsAIModalOpen(false);
    setIsNotifModalOpen(false);
    setIsSearchModalOpen(false);
    setIsAuthModalOpen(false);
    setMobileNavOpen(false);
    setUnreadCount(0);
    setRedmineSync(null);
    setNotifDeepLink({ category: "all", id: null });
    pendingDeepLink.current = null;
    if (window.location.search) window.history.replaceState(null, "", window.location.pathname);
  }, []);

  // Initial session check; remember any deep link until the user has signed in
  useEffect(() => {
    if (window.location.search) pendingDeepLink.current = new URLSearchParams(window.location.search);
    loadCurrentUser();
  }, [loadCurrentUser]);

  // Any API call rejected with 401 (expired token, account deactivated) ends the session
  useEffect(() => {
    const onUnauthorized = () => handleSignOut();
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, [handleSignOut]);

  useEffect(() => {
    if (authState !== "signedIn" || !isApproved) return;
    loadLiveMetrics();
    const badgeTimer = window.setInterval(loadLiveMetrics, 15000);

    // Deep links from alert emails: /?notifications=open&category=critical&id=<uuid>  or  /?view=admin
    const params = pendingDeepLink.current;
    pendingDeepLink.current = null;
    if (!params) return () => window.clearInterval(badgeTimer);
    const view = params.get("view");
    if (view) setActiveTab(view);
    if (params.get("notifications") === "open") {
      const cat = params.get("category");
      const allowed: NotificationCategory[] = ["all", "critical", "urgent", "completed", "info"];
      setNotifDeepLink({
        category: allowed.includes(cat as NotificationCategory) ? (cat as NotificationCategory) : "all",
        id: params.get("id"),
      });
      setIsNotifModalOpen(true);
    }
    return () => window.clearInterval(badgeTimer);
  }, [authState, isApproved]);

  // New screen starts at the top (matters on phones, where pages are long)
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [activeTab]);

  const handleGlobalSyncComplete = async () => {
    await loadLiveMetrics();
    setRefreshKey((prev) => prev + 1);
  };

  const handleAuthSuccess = (_token: string, user: CurrentUserProfile | null) => {
    if (user) {
      setCurrentUser(user);
      setAuthState("signedIn");
    } else {
      loadCurrentUser();
    }
    setActiveTab("dashboard");
    setRefreshKey((prev) => prev + 1);
  };

  if (authState === "checking") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f8fafc]">
        <Loader2 className="w-6 h-6 text-indigo-600 animate-spin" aria-label="Checking your session" />
      </div>
    );
  }

  if (authState === "offline") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f8fafc] p-4">
        <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center space-y-3 max-w-sm shadow-sm">
          <WifiOff className="w-8 h-8 text-slate-400 mx-auto" />
          <h2 className="text-base font-bold text-slate-900">Server not reachable</h2>
          <p className="text-xs text-slate-500">We couldn&apos;t verify your session. Check that the backend is running, then retry.</p>
          <button
            onClick={() => {
              setAuthState("checking");
              loadCurrentUser();
            }}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Signed out: the sign-in / sign-up page is the only thing rendered
  if (authState === "signedOut" || !currentUser) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-950 via-slate-900 to-indigo-900">
        <AuthModal
          key="login-page"
          isOpen
          dismissible={false}
          onClose={() => {}}
          onAuthSuccess={handleAuthSuccess}
          initialTab="signin"
        />
      </div>
    );
  }

  // Signed in but not approved yet (or declined): no company data is loaded
  if (!isApproved) {
    return <PendingApprovalScreen user={currentUser} onCheckStatus={loadCurrentUser} onSignOut={handleSignOut} />;
  }

  return (
    <div className="flex min-h-screen bg-[#f8fafc]">
      {/* Sidebar Navigation (Integrations & Admin conditionally visible to Admins & Mgmt only) */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        unreadCount={unreadCount}
        onOpenNotifications={() => setIsNotifModalOpen(true)}
        onOpenAI={() => setIsAIModalOpen(true)}
        redmineSync={redmineSync}
        mobileOpen={mobileNavOpen}
        onCloseMobile={() => setMobileNavOpen(false)}
        isAdmin={hasAdminAccess}
      />

      {/* Main Content Viewport */}
      <div className="flex-1 flex flex-col min-w-0">
        <TopNav
          unreadCount={unreadCount}
          currentUser={currentUser}
          onOpenNotifications={() => setIsNotifModalOpen(true)}
          onOpenAI={() => setIsAIModalOpen(true)}
          onSearchClick={() => setIsSearchModalOpen(true)}
          onSyncComplete={handleGlobalSyncComplete}
          onOpenMenu={() => setMobileNavOpen(true)}
          onNavigate={setActiveTab}
          onOpenAuthModal={(tab = "signin") => {
            setAuthModalTab(tab);
            setIsAuthModalOpen(true);
          }}
          onSignOut={handleSignOut}
          isAdmin={hasAdminAccess}
          isSuperAdmin={isSuperAdmin}
        />

        <main className="flex-1 px-3 py-4 sm:p-5 lg:p-6 pb-24 lg:pb-6 space-y-4 sm:space-y-6 max-w-7xl mx-auto w-full min-w-0">
          {activeTab === "dashboard" && (
            <DashboardView
              refreshKey={refreshKey}
              onNavigate={setActiveTab}
              onOpenNotifications={(category) => {
                setNotifDeepLink({ category, id: null });
                setIsNotifModalOpen(true);
              }}
            />
          )}

          {activeTab === "projects" && <ProjectsView key={refreshKey} />}
          {activeTab === "tasks" && <TasksView key={refreshKey} />}
          {activeTab === "teams" && <TeamsView key={refreshKey} />}
          {activeTab === "employees" && <EmployeesView key={refreshKey} />}
          {activeTab === "reports" && <ReportsView key={refreshKey} />}

          {/* Administration Section: Strictly Protected by RBAC */}
          {(activeTab === "admin" || activeTab === "administration") && (
            hasAdminAccess ? (
              <AdminView
                key={refreshKey}
                isSuperAdmin={isSuperAdmin}
                onOpenSignUp={isSuperAdmin ? () => {
                  setAuthModalTab("signup");
                  setIsAuthModalOpen(true);
                } : undefined}
              />
            ) : (
              <div className="bg-white p-8 sm:p-12 rounded-2xl border border-slate-200/90 text-center space-y-4 max-w-lg mx-auto shadow-sm my-8">
                <div className="w-14 h-14 rounded-2xl bg-amber-50 border border-amber-200 text-amber-600 flex items-center justify-center mx-auto shadow-xs">
                  <ShieldAlert className="w-7 h-7" />
                </div>
                <h2 className="text-lg font-bold text-slate-900">Administrator Access Required</h2>
                <p className="text-xs text-slate-500 leading-relaxed max-w-sm mx-auto">
                  Administration settings and user management are strictly reserved for Super Administrators and Company Management. Your current role is <span className="font-semibold text-slate-700">{userRole || "Team Member"}</span>.
                </p>
                <div className="pt-2 flex justify-center gap-3">
                  <button
                    onClick={() => setActiveTab("dashboard")}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-all"
                  >
                    Return to Dashboard
                  </button>
                  <button
                    onClick={() => {
                      setAuthModalTab("signin");
                      setIsAuthModalOpen(true);
                    }}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition-all"
                  >
                    Sign In with Admin Account
                  </button>
                </div>
              </div>
            )
          )}
        </main>
      </div>

      <MobileTabBar activeTab={activeTab} onChange={setActiveTab} />

      {/* Interactive Modals & Drawers */}
      <AIAssistantDrawer
        isOpen={isAIModalOpen}
        onClose={() => setIsAIModalOpen(false)}
        onNavigate={(view) => {
          setActiveTab(view);
          setIsAIModalOpen(false);
        }}
      />
      <NotificationModal
        isOpen={isNotifModalOpen}
        onClose={() => {
          setIsNotifModalOpen(false);
          setNotifDeepLink({ category: "all", id: null });
        }}
        onNotificationsChanged={loadLiveMetrics}
        initialCategory={notifDeepLink.category}
        highlightId={notifDeepLink.id}
      />
      <OmniSearchModal
        isOpen={isSearchModalOpen}
        onClose={() => setIsSearchModalOpen(false)}
        onNavigate={setActiveTab}
      />
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onAuthSuccess={handleAuthSuccess}
        initialTab={authModalTab}
        registerOnly={isSuperAdmin && authModalTab === "signup"}
        onRegistered={() => setRefreshKey((prev) => prev + 1)}
      />
    </div>
  );
}
