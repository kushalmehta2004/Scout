"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { getApplications, exportApplicationsCsv } from "@/lib/api";
import type { Application } from "@/lib/api";
import { KanbanBoard } from "@/components/KanbanBoard";
import { ApplicationsTable } from "@/components/ApplicationsTable";

type ViewMode = "kanban" | "table";

export default function TrackerPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<ViewMode>("kanban");
  const [exporting, setExporting] = useState(false);

  const fetchApplications = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getApplications({ sort: "applied_at" });
      setApplications(res.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load applications");
      setApplications([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchApplications();
  }, [fetchApplications]);

  async function handleExportCsv() {
    setExporting(true);
    try {
      const blob = await exportApplicationsCsv();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "applications.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="text-sm font-medium text-slate-600 hover:text-slate-900"
            >
              ← Dashboard
            </Link>
            <h1 className="text-2xl font-bold text-slate-900">Application Tracker</h1>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setView("kanban")}
              className={`rounded px-3 py-1.5 text-sm font-medium ${
                view === "kanban" ? "bg-slate-800 text-white" : "bg-white text-slate-700 shadow-sm"
              }`}
            >
              Kanban
            </button>
            <button
              type="button"
              onClick={() => setView("table")}
              className={`rounded px-3 py-1.5 text-sm font-medium ${
                view === "table" ? "bg-slate-800 text-white" : "bg-white text-slate-700 shadow-sm"
              }`}
            >
              Table
            </button>
            <button
              type="button"
              onClick={handleExportCsv}
              disabled={exporting || applications.length === 0}
              className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              {exporting ? "Exporting…" : "Export CSV"}
            </button>
          </div>
        </div>

        {error && (
          <p className="mb-4 text-sm text-red-600" role="alert">
            {error}
          </p>
        )}

        {loading ? (
          <p className="text-slate-600">Loading applications…</p>
        ) : applications.length === 0 ? (
          <p className="rounded-lg border border-slate-200 bg-white p-8 text-center text-slate-600">
            No applications yet. Use &quot;Save for Later&quot; on a listing or &quot;Apply Now&quot; to add
            them here.
          </p>
        ) : view === "kanban" ? (
          <KanbanBoard applications={applications} onUpdate={fetchApplications} />
        ) : (
          <ApplicationsTable applications={applications} onUpdate={fetchApplications} />
        )}
      </div>
    </div>
  );
}
