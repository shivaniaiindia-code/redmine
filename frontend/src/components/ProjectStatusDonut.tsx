"use client";

import React from "react";

interface DonutSegment {
  name: string;
  count: number;
  percentage: number;
  color: string;
}

export const ProjectStatusDonut: React.FC<{
  totalProjects: number;
  segments: DonutSegment[];
}> = ({ totalProjects, segments }) => {
  // SVG Donut calculation
  const size = 150;
  const strokeWidth = 22;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  let accumulatedPercent = 0;

  return (
    <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-2xs h-full flex flex-col justify-between">
      <h3 className="font-semibold text-slate-900 text-sm mb-4">Project Status Overview</h3>

      <div className="flex items-center justify-between gap-6 my-auto">
        {/* SVG Donut Chart with Center Text */}
        <div className="relative w-36 h-36 flex-shrink-0">
          <svg className="w-full h-full -rotate-90" viewBox={`0 0 ${size} ${size}`}>
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="transparent"
              stroke="#f1f5f9"
              strokeWidth={strokeWidth}
            />
            {segments.map((seg, idx) => {
              const strokeDasharray = `${(seg.percentage / 100) * circumference} ${circumference}`;
              const strokeDashoffset = -((accumulatedPercent / 100) * circumference);
              accumulatedPercent += seg.percentage;

              return (
                <circle
                  key={idx}
                  cx={size / 2}
                  cy={size / 2}
                  r={radius}
                  fill="transparent"
                  stroke={seg.color}
                  strokeWidth={strokeWidth}
                  strokeDasharray={strokeDasharray}
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="round"
                  className="transition-all duration-500"
                />
              );
            })}
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-xl font-bold text-slate-900 leading-none">
              {totalProjects}
            </span>
            <span className="text-[10px] text-slate-500 font-medium mt-0.5">Projects</span>
          </div>
        </div>

        {/* Legend */}
        <div className="flex-1 space-y-2">
          {segments.map((seg, idx) => (
            <div key={idx} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: seg.color }}
                ></span>
                <span className="text-slate-600 font-medium">{seg.name}</span>
              </div>
              <span className="font-bold text-slate-800">
                {seg.count} <span className="font-normal text-slate-400">({seg.percentage}%)</span>
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

