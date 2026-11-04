"use client";

import React, { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import {
  Users,
  Mail,
  RefreshCw,
  Plus,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Ban,
  Trash2,
  ShieldCheck,
  Hourglass,
  UserCheck,
  UserX,
} from "lucide-react";

interface UserItem {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  auth_provider: string;
  approval_status?: "APPROVED" | "PENDING" | "REJECTED" | string;
  department?: string | null;
  job_title?: string | null;
}

// Built-in root account: cannot be blocked, deleted or demoted
const ROOT_ADMIN_EMAIL = "admin@aiindia.com";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Roles Company Management may grant when approving an access request
const MANAGEMENT_GRANTABLE = ["EMPLOYEE", "TEAM_LEAD", "PROJECT_MANAGER"];

const ROLE_OPTIONS = [
  { value: "SUPER_ADMIN", label: "Super Admin" },
  { value: "COMPANY_MANAGEMENT", label: "Company Management" },
  { value: "PROJECT_MANAGER", label: "Project Manager" },
  { value: "TEAM_LEAD", label: "Team Lead" },
  { value: "EMPLOYEE", label: "Employee" },
];

export const ActiveUsersCard: React.FC<{ onOpenSignUp?: () => void; isSuperAdmin?: boolean }> = ({
  onOpenSignUp,
  isSuperAdmin = true,
}) => {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [rowError, setRowError] = useState<{ id: string; text: string } | null>(null);
  const [feedback, setFeedback] = useState<{ ok: boolean; text: string } | null>(null);
  const [approvalRole, setApprovalRole] = useState<Record<string, string>>({});

  // Decode current session token to get role and identity
  const getSessionInfo = () => {
    if (typeof window === "undefined") return { isSuper: false, isMgmt: false, email: "", id: "" };
    const token = localStorage.getItem("cip_token");
    if (!token) return { isSuper: false, isMgmt: false, email: "", id: "" };
    try {
      const parts = token.split(".");
      if (parts.length === 3) {
        const payload = JSON.parse(atob(parts[1]));
        const isSuper = payload.role === "SUPER_ADMIN";
        const isMgmt = isSuper || payload.role === "COMPANY_MANAGEMENT";
        return { isSuper, isMgmt, email: payload.email || "", id: payload.sub || "" };
      }
    } catch {}
    return { isSuper: false, isMgmt: false, email: "", id: "" };
  };

  const session = getSessionInfo();
  const effectiveIsSuperAdmin = isSuperAdmin || session.isSuper;
  const canManageAccess = effectiveIsSuperAdmin || session.isMgmt;



  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("cip_token") : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await apiFetch(`${API_BASE_URL}/auth/users`, { headers });
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      } else {
        setFeedback({ ok: false, text: "Failed to load active users directory" });
      }
    } catch {
      setFeedback({ ok: false, text: "Server unreachable" });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const toggleUserStatus = async (userId: string, currentStatus: boolean, userEmail: string) => {
    setUpdatingId(userId);
    setFeedback(null);
    const newStatus = !currentStatus;
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("cip_token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await apiFetch(`${API_BASE_URL}/auth/users/${userId}/status`, {
        method: "PUT",
        headers,
        body: JSON.stringify({ is_active: newStatus }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to update status");
      }

      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, is_active: newStatus } : u))
      );
      const actionLabel = newStatus ? "unblocked and activated" : "blocked";
      setFeedback({ ok: true, text: `User ${userEmail} ${actionLabel}.` });
    } catch (err: any) {
      setFeedback({ ok: false, text: err.message || "Could not update user status" });
    } finally {
      setUpdatingId(null);
      setTimeout(() => setFeedback(null), 4000);
    }
  };

  const deleteUser = async (userId: string, userEmail: string) => {
    setUpdatingId(userId);
    setRowError(null);
    setFeedback(null);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("cip_token") : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await apiFetch(`${API_BASE_URL}/auth/users/${userId}`, {
        method: "DELETE",
        headers,
      });

      let data: any = {};
      try {
        data = await res.json();
      } catch {
        // Safe fallback if response body is empty or non-JSON
      }

      if (!res.ok) {
        throw new Error(data.detail || data.message || `Failed to delete user (${res.status})`);
      }

      // Immediately purge from frontend state and clear confirmation
      setUsers((prev) => prev.filter((u) => u.id !== userId));
      setDeleteConfirmId(null);
      setRowError(null);
      setFeedback({ ok: true, text: data.message || `User ${userEmail} deleted successfully.` });
    } catch (err: any) {
      const msg = err.message || "Could not delete user";
      setFeedback({ ok: false, text: msg });
      setRowError({ id: userId, text: msg });
    } finally {
      setUpdatingId(null);
      setTimeout(() => setFeedback(null), 5000);
    }
  };

  const updateUserRole = async (userId: string, newRole: string) => {
    setUpdatingId(userId);
    setFeedback(null);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("cip_token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await apiFetch(`${API_BASE_URL}/auth/users/${userId}/role`, {
        method: "PUT",
        headers,
        body: JSON.stringify({ role: newRole }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to update role");
      }

      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: newRole } : u))
      );
      const roleLabel = ROLE_OPTIONS.find((r) => r.value === newRole)?.label || newRole;
      setFeedback({ ok: true, text: `Role successfully updated to "${roleLabel}"` });
    } catch (err: any) {
      setFeedback({ ok: false, text: err.message || "Could not update user role" });
    } finally {
      setUpdatingId(null);
      setTimeout(() => setFeedback(null), 4000);
    }
  };

  const reviewRequest = async (u: UserItem, approve: boolean) => {
    setUpdatingId(u.id);
    setFeedback(null);
    try {
      const role = approvalRole[u.id] || "EMPLOYEE";
      const res = await apiFetch(`${API_BASE_URL}/auth/users/${u.id}/approval`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(approve ? { approve: true, role } : { approve: false }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not review the access request");
      setUsers((prev) =>
        prev.map((x) =>
          x.id === u.id
            ? { ...x, approval_status: data.approval_status, role: data.role || x.role, is_active: approve ? true : x.is_active }
            : x
        )
      );
      const roleLabel = ROLE_OPTIONS.find((r) => r.value === role)?.label || role;
      setFeedback({
        ok: true,
        text: approve ? `${u.name} approved as ${roleLabel}. They can now open the dashboard.` : `Access request from ${u.name} declined.`,
      });
    } catch (err: any) {
      setFeedback({ ok: false, text: err.message || "Could not review the access request" });
    } finally {
      setUpdatingId(null);
      setTimeout(() => setFeedback(null), 5000);
    }
  };

  const pendingUsers = users.filter((u) => u.approval_status === "PENDING");
  const grantableRoles = ROLE_OPTIONS.filter((r) => effectiveIsSuperAdmin || MANAGEMENT_GRANTABLE.includes(r.value));

  const activeCount = users.filter((u) => u.is_active).length;
  const googleCount = users.filter((u) => u.auth_provider === "google").length;

  return (
    <section className="bg-white p-4 sm:p-6 rounded-xl border border-slate-200/80 shadow-sm space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-indigo-600" />
            <h2 className="text-base sm:text-lg font-bold text-slate-900">
              Active Users & Access Control
            </h2>
            <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 font-semibold border border-indigo-200">
              {users.length} Registered
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Manage authenticated accounts, Google Sign-In identity, and role-based permissions
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchUsers}
            disabled={isLoading}
            className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 text-xs font-medium transition-all"
            title="Refresh users"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          </button>
          {onOpenSignUp && (
            <button
              onClick={onOpenSignUp}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-sm transition-all"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add User</span>
            </button>
          )}
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
        <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
          <span className="text-[11px] text-slate-500 block">Total Users</span>
          <span className="text-lg font-bold text-slate-900">{users.length}</span>
        </div>
        <div className="bg-emerald-50/60 p-3 rounded-lg border border-emerald-100">
          <span className="text-[11px] text-emerald-700 block">Active Status</span>
          <span className="text-lg font-bold text-emerald-700">{activeCount}</span>
        </div>
        <div className="bg-blue-50/60 p-3 rounded-lg border border-blue-100">
          <span className="text-[11px] text-blue-700 block">Google OAuth</span>
          <span className="text-lg font-bold text-blue-700">{googleCount}</span>
        </div>
        <div className="bg-amber-50/60 p-3 rounded-lg border border-amber-100">
          <span className="text-[11px] text-amber-700 block">Disabled</span>
          <span className="text-lg font-bold text-amber-700">{users.length - activeCount}</span>
        </div>
        <div className={`p-3 rounded-lg border ${pendingUsers.length ? "bg-orange-50 border-orange-200" : "bg-slate-50 border-slate-100"}`}>
          <span className={`text-[11px] block ${pendingUsers.length ? "text-orange-700" : "text-slate-500"}`}>Awaiting Approval</span>
          <span className={`text-lg font-bold ${pendingUsers.length ? "text-orange-700" : "text-slate-900"}`}>{pendingUsers.length}</span>
        </div>
      </div>

      {/* Feedback Alert */}
      {feedback && (
        <div
          className={`p-2.5 rounded-lg text-xs font-medium border flex items-center gap-2 ${
            feedback.ok
              ? "bg-emerald-50 border-emerald-200 text-emerald-800"
              : "bg-red-50 border-red-200 text-red-700"
          }`}
        >
          {feedback.ok ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          )}
          <span>{feedback.text}</span>
        </div>
      )}

      {/* Access Requests: new sign-ups waiting for approval */}
      {pendingUsers.length > 0 && (
        <div className="rounded-xl border border-orange-200 bg-gradient-to-br from-orange-50 to-amber-50/40 overflow-hidden">
          <div className="px-4 py-3 border-b border-orange-200/70 flex items-center gap-2">
            <span className="relative flex w-2.5 h-2.5">
              <span className="absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75 animate-ping" />
              <span className="relative inline-flex rounded-full w-2.5 h-2.5 bg-orange-500" />
            </span>
            <h3 className="text-sm font-bold text-orange-900">Access Requests</h3>
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-orange-100 text-orange-800 border border-orange-200">
              {pendingUsers.length} waiting
            </span>
            <span className="hidden sm:inline text-[11px] text-orange-800/70 ml-auto">
              These accounts can&apos;t see any company data until approved
            </span>
          </div>
          <ul className="divide-y divide-orange-100">
            {pendingUsers.map((u) => (
              <li key={u.id} className="px-4 py-3 flex flex-col md:flex-row md:items-center gap-3">
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <div className="w-9 h-9 rounded-xl bg-white border border-orange-200 text-orange-600 flex items-center justify-center shrink-0">
                    <Hourglass className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-900 truncate">{u.name}</p>
                    <p className="text-[11px] text-slate-500 truncate">
                      {u.email} · {u.auth_provider === "google" ? "Google" : "Email / Password"} · requested {u.created_at || "recently"}
                    </p>
                  </div>
                </div>
                {canManageAccess ? (
                  <div className="flex items-center gap-2 flex-wrap">
                    <select
                      value={approvalRole[u.id] || "EMPLOYEE"}
                      onChange={(e) => setApprovalRole((prev) => ({ ...prev, [u.id]: e.target.value }))}
                      disabled={updatingId === u.id}
                      aria-label={`Role to grant ${u.name}`}
                      className="text-xs font-semibold rounded-lg px-2.5 py-1.5 border border-slate-200 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
                    >
                      {grantableRoles.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={() => reviewRequest(u, true)}
                      disabled={updatingId === u.id}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-sm transition-colors disabled:opacity-60"
                    >
                      {updatingId === u.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <UserCheck className="w-3.5 h-3.5" />}
                      Approve
                    </button>
                    <button
                      onClick={() => reviewRequest(u, false)}
                      disabled={updatingId === u.id}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-white hover:bg-rose-50 text-rose-700 border border-rose-200 text-xs font-semibold transition-colors disabled:opacity-60"
                    >
                      <UserX className="w-3.5 h-3.5" />
                      Decline
                    </button>
                  </div>
                ) : (
                  <span className="text-[11px] text-slate-400">View Only</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Users Table */}
      {isLoading && users.length === 0 ? (
        <div className="p-8 text-center text-slate-400 text-xs">
          <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-indigo-500" />
          Loading user accounts...
        </div>
      ) : (
        <div className="border border-slate-200/90 rounded-xl overflow-hidden overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3">User</th>
                <th className="py-2.5 px-3">Auth Provider</th>
                <th className="py-2.5 px-3">Assigned Role</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Created</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {users.map((u) => {
                const initials = u.name
                  .split(" ")
                  .filter(Boolean)
                  .slice(0, 2)
                  .map((n) => n[0].toUpperCase())
                  .join("");

                const isSuper = u.role === "SUPER_ADMIN";

                return (
                  <tr key={u.id} className="hover:bg-slate-50/70 transition-colors">
                    {/* User Identity */}
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center text-[10px] shrink-0">
                          {initials || "U"}
                        </div>
                        <div className="min-w-0">
                          <p className="font-semibold text-slate-900 truncate">{u.name}</p>
                          <p className="text-[11px] text-slate-400 truncate">{u.email}</p>
                        </div>
                      </div>
                    </td>

                    {/* Auth Provider */}
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      {u.auth_provider === "google" ? (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 border border-blue-200 text-[11px] font-medium">
                          <svg className="w-3 h-3" viewBox="0 0 24 24">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                          </svg>
                          Google OAuth
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200 text-[11px] font-medium">
                          <Mail className="w-3 h-3 text-slate-500" />
                          Email / Password
                        </span>
                      )}
                    </td>

                    {/* Assigned Role */}
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <select
                          value={u.role}
                          disabled={!effectiveIsSuperAdmin || updatingId === u.id || (isSuper && u.email === ROOT_ADMIN_EMAIL)}
                          onChange={(e) => updateUserRole(u.id, e.target.value)}
                          aria-label={`Change role for ${u.name}`}
                          className={`text-xs font-semibold rounded-lg px-2.5 py-1.5 border transition-all cursor-pointer shadow-2xs focus:outline-none focus:ring-2 focus:ring-indigo-500/30 ${
                            isSuper
                              ? "bg-purple-50 text-purple-800 border-purple-200 hover:bg-purple-100/70"
                              : u.role === "COMPANY_MANAGEMENT"
                              ? "bg-blue-50 text-blue-800 border-blue-200 hover:bg-blue-100/70"
                              : u.role === "PROJECT_MANAGER"
                              ? "bg-indigo-50 text-indigo-800 border-indigo-200 hover:bg-indigo-100/70"
                              : u.role === "TEAM_LEAD"
                              ? "bg-teal-50 text-teal-800 border-teal-200 hover:bg-teal-100/70"
                              : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                          } disabled:opacity-60 disabled:cursor-not-allowed`}
                        >
                          {ROLE_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                        {updatingId === u.id && (
                          <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-600 shrink-0" />
                        )}
                      </div>
                    </td>

                    {/* Status Badge */}
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      {u.approval_status === "PENDING" ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-orange-50 text-orange-700 border border-orange-200">
                          <Hourglass className="w-3.5 h-3.5 text-orange-600" /> Pending
                        </span>
                      ) : u.approval_status === "REJECTED" ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
                          <UserX className="w-3.5 h-3.5 text-slate-500" /> Declined
                        </span>
                      ) : u.is_active ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                          <Ban className="w-3.5 h-3.5 text-rose-600" /> Blocked
                        </span>
                      )}
                    </td>

                    {/* Created Date */}
                    <td className="py-2.5 px-3 whitespace-nowrap text-slate-400 text-[11px]">
                      {u.created_at || "—"}
                    </td>

                    {/* Actions */}
                    <td className="py-2.5 px-3 text-right whitespace-nowrap">
                      {deleteConfirmId === u.id ? (
                        <div className="flex items-center justify-end gap-1.5 animate-fadeIn">
                          {rowError && rowError.id === u.id ? (
                            <span className="text-[11px] text-rose-600 font-medium mr-1 max-w-[200px] truncate" title={rowError.text}>
                              {rowError.text}
                            </span>
                          ) : (
                            <span className="text-[11px] text-rose-700 font-semibold mr-1">Delete user?</span>
                          )}
                          <button
                            onClick={() => deleteUser(u.id, u.email)}
                            disabled={updatingId === u.id}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-rose-600 hover:bg-rose-700 text-white text-[11px] font-bold shadow-xs transition-colors disabled:opacity-60"
                          >
                            {updatingId === u.id ? (
                              <>
                                <Loader2 className="w-3 h-3 animate-spin" />
                                <span>Deleting…</span>
                              </>
                            ) : (
                              "Confirm"
                            )}
                          </button>
                          <button
                            onClick={() => {
                              setDeleteConfirmId(null);
                              setRowError(null);
                            }}
                            disabled={updatingId === u.id}
                            className="px-2 py-1 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-medium transition-colors"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : updatingId === u.id ? (
                        <span className="text-[11px] text-indigo-600 font-semibold inline-flex items-center gap-1">
                          <Loader2 className="w-3 h-3 animate-spin" /> Processing…
                        </span>
                      ) : u.email === ROOT_ADMIN_EMAIL || u.email === "admin@company.com" || u.email === "admin@aiindia.com" ? (
                        <span className="text-[11px] text-slate-400 font-medium inline-flex items-center gap-1">
                          <ShieldCheck className="w-3.5 h-3.5 text-slate-400" /> Root Protected
                        </span>
                      ) : session.email && u.email.toLowerCase() === session.email.toLowerCase() ? (
                        <span className="text-[11px] text-indigo-600 bg-indigo-50 border border-indigo-100 px-2 py-0.5 rounded font-medium">
                          You (Logged In)
                        </span>
                      ) : canManageAccess ? (
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Block / Unblock Button */}
                          <button
                            onClick={() => toggleUserStatus(u.id, u.is_active, u.email)}
                            disabled={updatingId === u.id}
                            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-semibold border transition-all ${
                              u.is_active
                                ? "bg-amber-50 hover:bg-amber-100 text-amber-800 border-amber-200"
                                : "bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border-emerald-200"
                            } disabled:opacity-50`}
                            title={u.is_active ? "Block this user from logging in" : "Unblock and activate account"}
                          >
                            {u.is_active ? (
                              <>
                                <Ban className="w-3 h-3 text-amber-600" /> Block
                              </>
                            ) : (
                              <>
                                <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Unblock
                              </>
                            )}
                          </button>

                          {/* Delete User Button */}
                          <button
                            onClick={() => {
                              setDeleteConfirmId(u.id);
                              setRowError(null);
                            }}
                            disabled={updatingId === u.id}
                            className="p-1 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50 border border-slate-200 hover:border-rose-300 transition-all disabled:opacity-50"
                            title="Delete user account"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ) : (
                        <span className="text-[11px] text-slate-400">View Only</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
};
