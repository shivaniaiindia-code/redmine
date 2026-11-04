"use client";

import React, { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Search, FolderKanban, Users2, CheckSquare, Loader2 } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface OmniSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** Opens the view that holds the selected record ("projects" | "tasks" | "employees"). */
  onNavigate?: (view: string) => void;
}

interface Result {
  key: string;
  type: "project" | "task" | "employee";
  title: string;
  subtitle: string;
  haystack: string;
}

const ICONS = { project: FolderKanban, task: CheckSquare, employee: Users2 };
const VIEW = { project: "projects", task: "tasks", employee: "employees" };

const toResults = (projects: any[], tasks: any[], employees: any[]): Result[] => [
  ...projects.map((p) => ({
    key: `p-${p.id}`, type: "project" as const, title: String(p.name ?? "").trim(),
    subtitle: [p.code, p.status, p.health_status].filter(Boolean).join(" · "),
  })),
  ...tasks.map((t) => ({
    key: `t-${t.id}`, type: "task" as const, title: String(t.title ?? ""),
    subtitle: [t.project_name, t.status, t.assigned_to?.name ?? t.assignee_name ?? t.assigned_to].filter((x) => typeof x === "string" && x).join(" · "),
  })),
  ...employees.map((e) => ({
    key: `e-${e.id}`, type: "employee" as const, title: String(e.name ?? ""),
    subtitle: [e.job_title, (e.current_projects ?? []).map((p: any) => p.name).slice(0, 2).join(", ")].filter(Boolean).join(" · "),
  })),
].map((r) => ({ ...r, haystack: `${r.title} ${r.subtitle}`.toLowerCase() }));

export const OmniSearchModal: React.FC<OmniSearchModalProps> = ({ isOpen, onClose, onNavigate }) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [index, setIndex] = useState<Result[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Load a fresh index of real records each time search opens
  useEffect(() => {
    if (!isOpen) return;
    let alive = true;
    setError(false);
    Promise.all(["projects", "tasks", "employees"].map((p) => apiFetch(`${API_BASE_URL}/${p}/`).then((r) => (r.ok ? r.json() : []))))
      .then(([p, t, e]) => alive && setIndex(toResults(p, t, e)))
      .catch(() => alive && setError(true));
    return () => {
      alive = false;
    };
  }, [isOpen]);

  const filtered = useMemo(() => {
    if (!index) return [];
    const q = searchTerm.trim().toLowerCase();
    const terms = q.split(/\s+/).filter(Boolean);
    const hits = terms.length ? index.filter((r) => terms.every((t) => r.haystack.includes(t))) : index.filter((r) => r.type === "project");
    return hits.slice(0, 12);
  }, [index, searchTerm]);

  if (!isOpen) return null;

  const open = (r: Result) => {
    onNavigate?.(VIEW[r.type]);
    setSearchTerm("");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex items-start justify-center bg-slate-900/40 backdrop-blur-xs p-0 sm:p-4 sm:pt-24 animate-in fade-in" onClick={onClose} role="dialog" aria-modal="true" aria-label="Search">
      <div className="bg-white sm:rounded-2xl w-full max-w-xl shadow-2xl sm:border border-slate-200 overflow-hidden h-[100dvh] sm:h-auto flex flex-col pt-[env(safe-area-inset-top)] sm:pt-0" onClick={(e) => e.stopPropagation()}>
        <div className="p-3.5 border-b border-slate-100 flex items-center gap-3 bg-white">
          <Search className="w-5 h-5 text-indigo-600 flex-shrink-0" />
          <input
            type="text"
            autoFocus
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && filtered[0] && open(filtered[0])}
            placeholder="Search projects, tasks and people…"
            className="w-full text-sm text-slate-800 focus:outline-hidden placeholder:text-slate-400"
          />
          <kbd className="hidden sm:inline text-[10px] bg-slate-100 text-slate-500 font-semibold px-2 py-0.5 rounded">ESC</kbd>
          <button onClick={onClose} className="sm:hidden text-sm font-semibold text-indigo-600 px-1 py-1">Cancel</button>
        </div>

        <div className="p-2 flex-1 sm:flex-none sm:max-h-80 overflow-y-auto overscroll-contain">
          {error ? (
            <div className="py-8 text-center text-xs text-red-600">Couldn&apos;t load search data. Please try again.</div>
          ) : index === null ? (
            <div className="py-8 flex items-center justify-center gap-2 text-xs text-slate-400"><Loader2 className="w-4 h-4 animate-spin" /> Loading…</div>
          ) : filtered.length > 0 ? (
            <div className="space-y-1">
              {!searchTerm.trim() && <p className="px-2.5 pt-1 pb-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">Projects</p>}
              {filtered.map((item) => {
                const Icon = ICONS[item.type];
                return (
                  <button
                    key={item.key}
                    onClick={() => open(item)}
                    className="w-full text-left flex items-center gap-3 p-3 sm:p-2.5 rounded-xl hover:bg-indigo-50/70 active:bg-indigo-50 transition-all group"
                  >
                    <div className="w-8 h-8 rounded-lg bg-slate-100 group-hover:bg-indigo-100 text-slate-600 group-hover:text-indigo-600 flex items-center justify-center flex-shrink-0">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <h4 className="text-xs font-semibold text-slate-900 group-hover:text-indigo-900 truncate">{item.title}</h4>
                      <p className="text-[11px] text-slate-500 truncate">
                        <span className="capitalize">{item.type}</span>{item.subtitle ? ` · ${item.subtitle}` : ""}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-slate-400">No projects, tasks or people match “{searchTerm}”.</div>
          )}
        </div>
      </div>
    </div>
  );
};
