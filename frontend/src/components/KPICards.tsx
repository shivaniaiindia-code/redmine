"use client";

import React from "react";
import {
  FolderKanban,
  CheckSquare,
  AlertTriangle,
  Users2,
  Layers,
  CheckCircle2
} from "lucide-react";

interface KPIData {
  id: string;
  label: string;
  value: string;
  trend: string;
  trend_type: string;
  icon: string;
}

export const KPICards: React.FC<{ kpis: KPIData[] }> = ({ kpis }) => {
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case "folder":
        return <FolderKanban className="w-5 h-5 text-purple-600" />;
      case "check_square":
        return <CheckSquare className="w-5 h-5 text-blue-600" />;
      case "alert_triangle":
        return <AlertTriangle className="w-5 h-5 text-red-500" />;
      case "users":
        return <Users2 className="w-5 h-5 text-indigo-600" />;
      case "layers":
        return <Layers className="w-5 h-5 text-purple-600" />;
      case "check_circle":
        return <CheckCircle2 className="w-5 h-5 text-emerald-600" />;
      default:
        return <FolderKanban className="w-5 h-5 text-indigo-600" />;
    }
  };

  const getIconBg = (iconName: string) => {
    switch (iconName) {
      case "folder":
        return "bg-purple-50";
      case "check_square":
        return "bg-blue-50";
      case "alert_triangle":
        return "bg-red-50";
      case "users":
        return "bg-indigo-50";
      case "layers":
        return "bg-purple-50";
      case "check_circle":
        return "bg-emerald-50";
      default:
        return "bg-slate-50";
    }
  };

  const getTrendColor = (type: string) => {
    switch (type) {
      case "up":
        return "text-emerald-600";
      case "danger":
        return "text-red-600 font-semibold";
      default:
        return "text-slate-400";
    }
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      {kpis.map((kpi) => (
        <div
          key={kpi.id}
          className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-2xs hover:shadow-md transition-shadow"
        >
          <div className="flex items-center justify-between mb-3">
            <div className={`w-9 h-9 rounded-xl ${getIconBg(kpi.icon)} flex items-center justify-center`}>
              {getIcon(kpi.icon)}
            </div>
          </div>
          <div>
            <p className="text-[11px] font-medium text-slate-500 mb-1">{kpi.label}</p>
            <h3 className="text-2xl font-bold text-slate-900 tracking-tight">{kpi.value}</h3>
            <p className={`text-[10px] mt-1.5 ${getTrendColor(kpi.trend_type)}`}>
              {kpi.trend}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
};

