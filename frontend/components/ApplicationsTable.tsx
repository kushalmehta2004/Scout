"use client";

import { useState, useMemo } from "react";
import type { Application } from "@/lib/api";
import { updateApplication } from "@/lib/api";

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return "—";
  }
}

type SortKey = "listing_title" | "listing_company" | "status" | "applied_at" | "follow_up_date";

type ApplicationsTableProps = {
  applications: Application[];
  onUpdate: () => void;
};

export function ApplicationsTable({ applications, onUpdate }: ApplicationsTableProps) {
  const [sortBy, setSortBy] = useState<SortKey>("applied_at");
  const [sortDesc, setSortDesc] = useState(true);

  const sorted = useMemo(() => {
    const list = [...applications];
    list.sort((a, b) => {
      let va: string | number | null = (a as Record<string, unknown>)[sortBy] as string | null;
      let vb: string | number | null = (b as Record<string, unknown>)[sortBy] as string | null;
      if (sortBy === "applied_at" || sortBy === "follow_up_date") {
        const da = va ? new Date(va).getTime() : 0;
        const db = vb ? new Date(vb as string).getTime() : 0;
        return sortDesc ? db - da : da - db;
      }
      const sa = String(va ?? "");
      const sb = String(vb ?? "");
      const c = sa.localeCompare(sb);
      return sortDesc ? -c : c;
    });
    return list;
  }, [applications, sortBy, sortDesc]);

  function toggleSort(key: SortKey) {
    if (sortBy === key) setSortDesc((d) => !d);
    else {
      setSortBy(key);
      setSortDesc(true);
    }
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-100 text-slate-700">
          <tr>
            <th>
              <button
                type="button"
                onClick={() => toggleSort("listing_title")}
                className="px-3 py-2 font-medium hover:bg-slate-200"
              >
                Title {sortBy === "listing_title" && (sortDesc ? "↓" : "↑")}
              </button>
            </th>
            <th>
              <button
                type="button"
                onClick={() => toggleSort("listing_company")}
                className="px-3 py-2 font-medium hover:bg-slate-200"
              >
                Company {sortBy === "listing_company" && (sortDesc ? "↓" : "↑")}
              </button>
            </th>
            <th>
              <button
                type="button"
                onClick={() => toggleSort("status")}
                className="px-3 py-2 font-medium hover:bg-slate-200"
              >
                Status {sortBy === "status" && (sortDesc ? "↓" : "↑")}
              </button>
            </th>
            <th>
              <button
                type="button"
                onClick={() => toggleSort("applied_at")}
                className="px-3 py-2 font-medium hover:bg-slate-200"
              >
                Applied {sortBy === "applied_at" && (sortDesc ? "↓" : "↑")}
              </button>
            </th>
            <th>
              <button
                type="button"
                onClick={() => toggleSort("follow_up_date")}
                className="px-3 py-2 font-medium hover:bg-slate-200"
              >
                Follow-up {sortBy === "follow_up_date" && (sortDesc ? "↓" : "↑")}
              </button>
            </th>
            <th className="px-3 py-2 font-medium">Notes</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((app) => (
            <TableRow key={app.id} application={app} onUpdate={onUpdate} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TableRow({ application, onUpdate }: { application: Application; onUpdate: () => void }) {
  const [notes, setNotes] = useState(application.notes);
  const [followUp, setFollowUp] = useState(
    application.follow_up_date ? application.follow_up_date.slice(0, 10) : ""
  );
  const [status, setStatus] = useState(application.status);
  const [saving, setSaving] = useState(false);

  const STATUSES = ["Saved", "Applied", "Phone Screen", "Interview", "Offer", "Rejected"];

  async function saveStatus(newStatus: string) {
    setSaving(true);
    try {
      await updateApplication(application.id, { status: newStatus });
      setStatus(newStatus);
      onUpdate();
    } finally {
      setSaving(false);
    }
  }

  async function saveNotes() {
    setSaving(true);
    try {
      await updateApplication(application.id, { notes: notes || "" });
      onUpdate();
    } finally {
      setSaving(false);
    }
  }

  async function saveFollowUp() {
    setSaving(true);
    try {
      await updateApplication(application.id, {
        follow_up_date: followUp ? `${followUp}T12:00:00Z` : "",
      });
      onUpdate();
    } finally {
      setSaving(false);
    }
  }

  return (
    <tr className="border-t border-slate-100 hover:bg-slate-50/50">
      <td className="px-3 py-2">
        <a
          href={application.apply_url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-blue-600 hover:underline"
        >
          {application.listing_title}
        </a>
      </td>
      <td className="px-3 py-2 text-slate-700">{application.listing_company}</td>
      <td className="px-3 py-2">
        <select
          value={status}
          onChange={(e) => saveStatus(e.target.value)}
          disabled={saving}
          className="rounded border border-slate-200 bg-white px-2 py-1 text-sm"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </td>
      <td className="px-3 py-2 text-slate-600">{formatDate(application.applied_at)}</td>
      <td className="px-3 py-2">
        <input
          type="date"
          value={followUp}
          onChange={(e) => setFollowUp(e.target.value)}
          onBlur={saveFollowUp}
          className="rounded border border-slate-200 px-2 py-1 text-sm"
        />
      </td>
      <td className="px-3 py-2">
        <input
          type="text"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          onBlur={saveNotes}
          placeholder="Notes"
          className="min-w-[120px] rounded border border-slate-200 px-2 py-1 text-sm"
        />
      </td>
    </tr>
  );
}
