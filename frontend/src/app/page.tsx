"use client";

import React, { useState, useEffect } from "react";
import { Sidebar } from "@/components/Sidebar";
import { TopNav } from "@/components/TopNav";
import { KPICards } from "@/components/KPICards";
import { ProjectStatusDonut } from "@/components/ProjectStatusDonut";
import { TaskDistributionBar } from "@/components/TaskDistributionBar";
import { TeamWorkloadStacked } from "@/components/TeamWorkloadStacked";
import { DeadlinesFeed } from "@/components/DeadlinesFeed";
import { ActivitiesFeed } from "@/components/ActivitiesFeed";
import { NotificationsFeed } from "@/components/NotificationsFeed";
import { AIAssistantDrawer } from "@/components/AIAssistantDrawer";
import { NotificationModal } from "@/components/NotificationModal";
import { OmniSearchModal } from "@/components/OmniSearchModal";
import { ProjectsView } from "@/components/views/ProjectsView";
import { TasksView } from "@/components/views/TasksView";
import { TeamsView } from "@/components/views/TeamsView";
import { EmployeesView } from "@/components/views/EmployeesView";
import { AdminView } from "@/components/views/AdminView";
import { ChevronDown, RefreshCw } from "lucide-react";

export default function Home() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [isAIModalOpen, setIsAIModalOpen] = useState(false);
  const [isNotifModalOpen, setIsNotifModalOpen] = useState(false);
  const [isSearchModalOpen, setIsSearchModalOpen] = useState(false);
  const [dateRange, setDateRange] = useState("Last 7 Days");
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Initial dashboard metrics loaded dynamically from Redmine
  const [dashboardData, setDashboardData] = useState({
    kpis: [
      { id: "active_projects", label: "Active Projects", value: "0", trend: "Live from Redmine", trend_type: "up", icon: "folder" },
      { id: "open_tasks", label: "Open Tasks", value: "0", trend: "Redmine issues", trend_type: "neutral", icon: "check_square" },
      { id: "projects_at_risk", label: "Projects at Risk", value: "0", trend: "Health scan active", trend_type: "neutral", icon: "alert_triangle" },
      { id: "total_employees", label: "Total Employees", value: "0", trend: "Synced members", trend_type: "neutral", icon: "users" },
      { id: "teams", label: "Teams", value: "0", trend: "Active units", trend_type: "neutral", icon: "layers" },
      { id: "task_completion", label: "Task Completion", value: "0%", trend: "Calculated", trend_type: "neutral", icon: "check_circle" }
    ],
    project_status: {
      total_projects: 0,
      segments: [] as { name: string; count: number; percentage: number; color: string }[]
    },
    task_distribution: [] as { status: string; count: number; color: string }[],
    team_workload: [] as { team_name: string; completed: number; in_progress: number; overdue: number; total_tasks: number }[],
    upcoming_deadlines: [] as { id: string; project_name: string; team_name: string; deadline_text: string; severity_pill: string; severity_type: string }[],
    recent_activities: [] as { id: string; title: string; subtitle: string; time_ago: string; activity_type: string }[],
    notifications: [] as { id: string; title: string; subtitle: string; time_ago: string; severity: string; deep_link: string }[]
  });

  // Fetch live metrics from FastAPI
  const loadLiveMetrics = async () => {
    try {
      setIsRefreshing(true);
      const res = await fetch("http://localhost:8000/api/v1/company/dashboard");
      if (res.ok) {
        const liveData = await res.json();
        setDashboardData(liveData);
      }
    } catch {
      // Graceful fallback
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadLiveMetrics();
  }, []);

  return (
    <div className="flex min-h-screen bg-[#f8fafc]">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        unreadCount={dashboardData.notifications.length}
        onOpenNotifications={() => setIsNotifModalOpen(true)}
        onOpenAI={() => setIsAIModalOpen(true)}
      />

      {/* Main Content Viewport */}
      <div className="flex-1 flex flex-col min-w-0">
        <TopNav
          unreadCount={dashboardData.notifications.length}
          onOpenNotifications={() => setIsNotifModalOpen(true)}
          onOpenAI={() => setIsAIModalOpen(true)}
          onSearchClick={() => setIsSearchModalOpen(true)}
        />

        <main className="flex-1 p-6 space-y-6 max-w-7xl mx-auto w-full">
          {activeTab === "dashboard" && (
            <>
              {/* Header Greeting & Date Filter */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
                    Good Morning, Admin 👋
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Here&apos;s what&apos;s happening across the company today. Connected to <span className="font-semibold text-indigo-600">Redmine (https://redmine.aiindia.ai)</span>.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={loadLiveMetrics}
                    disabled={isRefreshing}
                    className="flex items-center gap-1.5 bg-white border border-slate-200 hover:border-slate-300 text-xs font-semibold text-slate-700 px-3 py-2 rounded-xl shadow-2xs transition-all disabled:opacity-60"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-indigo-600" : "text-slate-500"}`} />
                    <span>Refresh</span>
                  </button>

                  <button className="flex items-center gap-2 bg-white border border-slate-200 hover:border-slate-300 text-xs font-semibold text-slate-700 px-3.5 py-2 rounded-xl shadow-2xs transition-all">
                    <span>{dateRange}</span>
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                  </button>
                </div>
              </div>

              {/* Row 1: 6 Top KPI Metric Cards */}
              <KPICards kpis={dashboardData.kpis} />

              {/* Row 2: Visual Analytics (3 Columns: Donut, Task Bars, Workload) */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <ProjectStatusDonut
                  totalProjects={dashboardData.project_status.total_projects}
                  segments={dashboardData.project_status.segments}
                />
                <TaskDistributionBar items={dashboardData.task_distribution} />
                <TeamWorkloadStacked items={dashboardData.team_workload} />
              </div>

              {/* Row 3: Operational Feeds (3 Columns: Deadlines, Activity, Notifications) */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <DeadlinesFeed
                  deadlines={dashboardData.upcoming_deadlines}
                  onViewAll={() => setActiveTab("projects")}
                />
                <ActivitiesFeed
                  activities={dashboardData.recent_activities}
                  onViewAll={() => setActiveTab("tasks")}
                />
                <NotificationsFeed
                  notifications={dashboardData.notifications}
                  unreadCount={dashboardData.notifications.length}
                  onViewAll={() => setIsNotifModalOpen(true)}
                />
              </div>
            </>
          )}

          {activeTab === "projects" && <ProjectsView />}
          {activeTab === "tasks" && <TasksView />}
          {activeTab === "teams" && <TeamsView />}
          {activeTab === "employees" && <EmployeesView />}
          {(activeTab === "admin" || activeTab === "administration") && <AdminView />}
        </main>
      </div>

      {/* Interactive Modals & Drawers */}
      <AIAssistantDrawer
        isOpen={isAIModalOpen}
        onClose={() => setIsAIModalOpen(false)}
      />
      <NotificationModal
        isOpen={isNotifModalOpen}
        onClose={() => setIsNotifModalOpen(false)}
        onNewNotificationTriggered={loadLiveMetrics}
      />
      <OmniSearchModal
        isOpen={isSearchModalOpen}
        onClose={() => setIsSearchModalOpen(false)}
      />
    </div>
  );
}
