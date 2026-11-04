"use client";

import React, { useEffect, useState } from "react";
import { Hourglass, ShieldCheck, UserCheck, LayoutDashboard, CheckCircle2, LogOut, RefreshCw, ShieldX, Lock } from "lucide-react";
import type { CurrentUserProfile } from "@/components/TopNav";

const POLL_MS = 20000;

interface Props {
  user: CurrentUserProfile;
  /** Re-reads /auth/me; once approved the parent swaps this screen for the dashboard. */
  onCheckStatus: () => Promise<void>;
  onSignOut: () => void;
}

/** Shown to a signed-in account that a Super Admin / Company Management has not approved yet. */
export const PendingApprovalScreen: React.FC<Props> = ({ user, onCheckStatus, onSignOut }) => {
  const [checking, setChecking] = useState(false);
  const [lastChecked, setLastChecked] = useState<Date>(new Date());
  const rejected = user.approval_status === "REJECTED";

  const name = user.employee
    ? `${user.employee.first_name} ${user.employee.last_name}`.trim()
    : user.email.split("@")[0];
  const firstName = name.split(" ")[0] || name;

  const check = async () => {
    setChecking(true);
    try {
      await onCheckStatus();
    } finally {
      setLastChecked(new Date());
      setChecking(false);
    }
  };

  // Keep checking in the background so access opens the moment it is approved
  useEffect(() => {
    if (rejected) return;
    const t = window.setInterval(check, POLL_MS);
    return () => window.clearInterval(t);
  }, [rejected]);

  const steps = [
    { icon: UserCheck, title: "Account created", detail: user.email, state: "done" as const },
    {
      icon: ShieldCheck,
      title: rejected ? "Request declined" : "Administrator review",
      detail: rejected
        ? "An administrator declined this access request"
        : "Super Admin or Company Management is reviewing your request",
      state: rejected ? ("failed" as const) : ("active" as const),
    },
    {
      icon: LayoutDashboard,
      title: "Dashboard access",
      detail: "Projects, teams, reports and AI assistant",
      state: "locked" as const,
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-950 via-slate-900 to-indigo-900 flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-2xl border border-slate-200/90 overflow-hidden">
          {/* Header */}
          <div className="relative px-6 pt-8 pb-6 bg-gradient-to-br from-indigo-900 via-indigo-800 to-slate-900 text-white text-center">
            <div className="relative mx-auto w-16 h-16 mb-4">
              {!rejected && <span className="absolute inset-0 rounded-2xl bg-amber-400/30 animate-ping" />}
              <div
                className={`relative w-16 h-16 rounded-2xl flex items-center justify-center border ${
                  rejected ? "bg-rose-500/20 border-rose-300/40" : "bg-amber-400/20 border-amber-300/40"
                }`}
              >
                {rejected ? (
                  <ShieldX className="w-8 h-8 text-rose-200" />
                ) : (
                  <Hourglass className="w-8 h-8 text-amber-200" />
                )}
              </div>
            </div>
            <p className="text-[11px] uppercase tracking-wider text-indigo-200 font-semibold">Intelligent Projects Manager</p>
            <h1 className="text-xl font-bold tracking-tight mt-1">
              {rejected ? "Access request declined" : `Thanks for signing up, ${firstName}!`}
            </h1>
            <p className="text-xs text-indigo-100/80 mt-2 leading-relaxed max-w-xs mx-auto">
              {rejected
                ? "Your account was not approved for access to company data. If you think this is a mistake, contact your administrator."
                : "Your account is waiting for approval from a Super Admin or Company Management. You'll get access to the dashboard as soon as it's approved."}
            </p>
          </div>

          {/* Progress */}
          <div className="p-6 space-y-5">
            <ol className="space-y-0">
              {steps.map((s, i) => {
                const Icon = s.icon;
                const last = i === steps.length - 1;
                const tone =
                  s.state === "done"
                    ? "bg-emerald-50 text-emerald-600 border-emerald-200"
                    : s.state === "active"
                    ? "bg-amber-50 text-amber-600 border-amber-200"
                    : s.state === "failed"
                    ? "bg-rose-50 text-rose-600 border-rose-200"
                    : "bg-slate-50 text-slate-400 border-slate-200";
                return (
                  <li key={s.title} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className={`w-9 h-9 rounded-xl border flex items-center justify-center shrink-0 ${tone}`}>
                        {s.state === "done" ? (
                          <CheckCircle2 className="w-5 h-5" />
                        ) : s.state === "locked" ? (
                          <Lock className="w-4 h-4" />
                        ) : (
                          <Icon className={`w-4 h-4 ${s.state === "active" ? "animate-pulse" : ""}`} />
                        )}
                      </div>
                      {!last && <div className="w-px flex-1 min-h-[18px] bg-slate-200 my-1" />}
                    </div>
                    <div className={`pb-4 min-w-0 ${last ? "pb-0" : ""}`}>
                      <p className={`text-sm font-semibold ${s.state === "locked" ? "text-slate-400" : "text-slate-900"}`}>
                        {s.title}
                        {s.state === "active" && (
                          <span className="ml-2 align-middle text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">
                            In progress
                          </span>
                        )}
                      </p>
                      <p className="text-xs text-slate-500 truncate">{s.detail}</p>
                    </div>
                  </li>
                );
              })}
            </ol>

            {!rejected && (
              <div className="rounded-xl bg-indigo-50/70 border border-indigo-100 p-3 text-[11px] text-indigo-900 leading-relaxed">
                <span className="font-semibold">Why the wait?</span> Company project and employee data is internal.
                Every new account is checked by an administrator before it can see anything.
              </div>
            )}

            <div className="flex flex-col sm:flex-row gap-2">
              {!rejected && (
                <button
                  onClick={check}
                  disabled={checking}
                  className="flex-1 inline-flex items-center justify-center gap-1.5 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-md shadow-indigo-600/20 transition-all disabled:opacity-60"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${checking ? "animate-spin" : ""}`} />
                  {checking ? "Checking…" : "Check approval status"}
                </button>
              )}
              <button
                onClick={onSignOut}
                className="flex-1 inline-flex items-center justify-center gap-1.5 py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition-all"
              >
                <LogOut className="w-3.5 h-3.5" />
                Sign out
              </button>
            </div>

            {!rejected && (
              <p className="text-center text-[11px] text-slate-400">
                Checks automatically every {POLL_MS / 1000} seconds · last checked{" "}
                {lastChecked.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
