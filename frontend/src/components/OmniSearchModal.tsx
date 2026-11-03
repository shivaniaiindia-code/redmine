"use client";

import React, { useState, useEffect } from "react";
import { Search, X, FolderKanban, Users2, CheckSquare } from "lucide-react";

interface OmniSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const OmniSearchModal: React.FC<OmniSearchModalProps> = ({ isOpen, onClose }) => {
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        // toggle or open
      } else if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const mockResults = [
    { type: "project", title: "ANPR System", subtitle: "Project Code: PRJ-ANPR · AI Team", icon: FolderKanban },
    { type: "project", title: "Document AI", subtitle: "Project Code: PRJ-DOCAI · Research", icon: FolderKanban },
    { type: "task", title: "Payment Gateway 3DS Auth Failure", subtitle: "Task #1042 · Bug · Blocked", icon: CheckSquare },
    { type: "employee", title: "Anil Abhange", subtitle: "Lead Architect · Engineering · Admin", icon: Users2 },
    { type: "team", title: "Development Team", subtitle: "52 active tasks · 24 completed", icon: Users2 }
  ];

  const filtered = mockResults.filter(
    (r) =>
      r.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.subtitle.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex items-start justify-center pt-24 bg-slate-900/40 backdrop-blur-xs p-4 animate-in fade-in">
      <div className="bg-white rounded-2xl w-full max-w-xl shadow-2xl border border-slate-200 overflow-hidden">
        {/* Search Input Header */}
        <div className="p-3.5 border-b border-slate-100 flex items-center gap-3 bg-white">
          <Search className="w-5 h-5 text-indigo-600 flex-shrink-0" />
          <input
            type="text"
            autoFocus
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search projects, tasks, employees, teams..."
            className="w-full text-sm text-slate-800 focus:outline-hidden placeholder:text-slate-400"
          />
          <kbd className="text-[10px] bg-slate-100 text-slate-500 font-semibold px-2 py-0.5 rounded">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="p-2 max-h-80 overflow-y-auto">
          {filtered.length > 0 ? (
            <div className="space-y-1">
              {filtered.map((item, idx) => {
                const Icon = item.icon;
                return (
                  <div
                    key={idx}
                    onClick={onClose}
                    className="flex items-center gap-3 p-2.5 rounded-xl hover:bg-indigo-50/70 cursor-pointer transition-all group"
                  >
                    <div className="w-8 h-8 rounded-lg bg-slate-100 group-hover:bg-indigo-100 text-slate-600 group-hover:text-indigo-600 flex items-center justify-center flex-shrink-0">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-xs font-semibold text-slate-900 group-hover:text-indigo-900">
                        {item.title}
                      </h4>
                      <p className="text-[11px] text-slate-500">{item.subtitle}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-slate-400">
              No matching projects or tasks found.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

