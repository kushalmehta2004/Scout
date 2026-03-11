"use client";

import type { Application } from "@/lib/api";
import { ApplicationCard } from "./ApplicationCard";

const COLUMNS = [
  { id: "Saved", label: "Saved" },
  { id: "Applied", label: "Applied" },
  { id: "Phone Screen", label: "Phone Screen" },
  { id: "Interview", label: "Interview" },
  { id: "Offer", label: "Offer" },
  { id: "Rejected", label: "Rejected" },
];

type KanbanBoardProps = {
  applications: Application[];
  onUpdate: () => void;
};

export function KanbanBoard({ applications, onUpdate }: KanbanBoardProps) {
  const byStatus: Record<string, Application[]> = {};
  COLUMNS.forEach((col) => {
    byStatus[col.id] = applications.filter((a) => a.status === col.id);
  });

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {COLUMNS.map((col) => (
        <div
          key={col.id}
          className="flex w-72 shrink-0 flex-col rounded-lg border border-slate-200 bg-slate-50/50 p-3"
        >
          <h3 className="mb-2 font-semibold text-slate-700">
            {col.label}
            <span className="ml-2 text-sm font-normal text-slate-500">
              ({byStatus[col.id]?.length ?? 0})
            </span>
          </h3>
          <div className="flex flex-col gap-2">
            {(byStatus[col.id] ?? []).map((app) => (
              <ApplicationCard key={app.id} application={app} onUpdate={onUpdate} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
