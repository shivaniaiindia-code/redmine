"use client";

import React, { useState, useEffect } from "react";
import { Users, Mail, Briefcase, CheckCircle, AlertTriangle, Layers } from "lucide-react";

interface EmployeeItem {
  id: string;
  name: string;
  email: string;
  job_title: string;
  department: string;
  status: string;
  weekly_capacity_hours: number;
  total_tasks: number;
  overdue_tasks: number;
  completed_tasks: number;
}

export const EmployeesView: React.FC = () => {
  const [employees, setEmployees] = useState<EmployeeItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchEmployees = async () => {
      try {
        setIsLoading(true);
        const res = await fetch("http://localhost:8000/api/v1/employees/");
        if (res.ok) {
          const data = await res.json();
          setEmployees(data);
        }
      } catch (err) {
        console.error("Failed to load employees", err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchEmployees();
  }, []);

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm">
        <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <Users className="w-6 h-6 text-indigo-600" />
          Employee 360 & Talent Directory
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Historical project contributions, active allocations, and workload monitoring
        </p>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-slate-400">Loading team members...</div>
      ) : employees.length === 0 ? (
        <div className="p-12 text-center text-slate-400">No employees found.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {employees.map((emp) => (
            <div
              key={emp.id}
              className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm">
                    {emp.name.split(" ").map((n) => n[0]).join("")}
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">{emp.name}</h3>
                    <p className="text-xs text-slate-500 flex items-center gap-1">
                      <Briefcase className="w-3 h-3" /> {emp.job_title}
                    </p>
                  </div>
                </div>

                <div className="space-y-1.5 text-xs text-slate-600 mb-4 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                  <div className="flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-slate-400" />
                    <span className="truncate">{emp.email}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-slate-400" />
                    <span>Department: {emp.department}</span>
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 grid grid-cols-3 gap-2 text-center">
                <div className="bg-slate-50 p-2 rounded">
                  <div className="text-xs text-slate-500">Tasks</div>
                  <div className="text-sm font-bold text-slate-900">{emp.total_tasks}</div>
                </div>
                <div className="bg-amber-50 p-2 rounded">
                  <div className="text-xs text-amber-700">Overdue</div>
                  <div className="text-sm font-bold text-amber-700">{emp.overdue_tasks}</div>
                </div>
                <div className="bg-emerald-50 p-2 rounded">
                  <div className="text-xs text-emerald-700">Done</div>
                  <div className="text-sm font-bold text-emerald-700">{emp.completed_tasks}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

