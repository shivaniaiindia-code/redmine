"use client";

import React from "react";

interface TaskDistItem {
  status: string;
  count: number;
  color: string;
}

export const TaskDistributionBar: React.FC<{ items: TaskDistItem[] }> = ({ items }) => {
  const maxCount = Math.max(...items.map((i) => i.count), 80);

  return (
    <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-2xs h-full flex flex-col justify-between">
      <h3 className="font-semibold text-slate-900 text-sm mb-4">Task Distribution</h3>

      <div className="flex items-end justify-between gap-3 h-44 pt-6 pb-2 border-b border-slate-100">
        {items.map((item, idx) => {
          const heightPercent = Math.min(100, Math.round((item.count / maxCount) * 100));

          return (
            <div key={idx} className="flex-1 flex flex-col items-center h-full justify-end group">
              <span className="text-[11px] font-bold text-slate-700 mb-1 opacity-90 group-hover:opacity-100">
                {item.count}
              </span>
              <div className="w-full max-w-[34px] bg-slate-100 rounded-t-lg overflow-hidden flex items-end h-full">
                <div
                  className="w-full rounded-t-lg transition-all duration-500 group-hover:brightness-95"
                  style={{
                    height: `${heightPercent}%`,
                    backgroundColor: item.color
                  }}
                ></div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Status Labels */}
      <div className="flex justify-between gap-3 pt-2">
        {items.map((item, idx) => (
          <span
            key={idx}
            className="flex-1 text-center text-[10px] font-medium text-slate-500 truncate"
            title={item.status}
          >
            {item.status}
          </span>
        ))}
      </div>
    </div>
  );
};

