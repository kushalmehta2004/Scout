"use client";

import { useState } from "react";
import type { Application } from "@/lib/api";
import { updateApplication } from "@/lib/api";

const STATUSES = ["Saved", "Applied", "Phone Screen", "Interview", "Offer", "Rejected"] as const;

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return "—";
  }
}

type ApplicationCardProps = {
  application: Application;
  onUpdate: () => void;
};

export function ApplicationCard({ application, onUpdate }: ApplicationCardProps) {
  const [notes, setNotes] = useState(application.notes);
  const [followUp, setFollowUp] = useState(
    application.follow_up_date ? application.follow_up_date.slice(0, 10) : ""
  );
  const [saving, setSaving] = useState(false);

  async function handleStatusChange(newStatus: string) {
    setSaving(true);
    try {
      await updateApplication(application.id, { status: newStatus });
      onUpdate();
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveNotes() {
    setSaving(true);
    try {
      await updateApplication(application.id, { notes: notes || "" });
      onUpdate();
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveFollowUp() {
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
    <article className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h3 className="font-medium text-slate-900">{application.listing_title}</h3>
          <p className="text-sm text-slate-600">{application.listing_company}</p>
          <p className="mt-0.5 text-xs text-slate-500">
            {application.applied_at ? formatDate(application.applied_at) : "Not applied yet"}
          </p>
        </div>
        <select
          value={application.status}
          onChange={(e) => handleStatusChange(e.target.value)}
          disabled={saving}
          className="rounded border border-slate-300 bg-white px-2 py-1 text-xs font-medium text-slate-700"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>
      <div className="mt-2">
        <label className="text-xs font-medium text-slate-500">Notes</label>
        <div className="flex gap-1">
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            onBlur={handleSaveNotes}
            placeholder="Add notes…"
            className="min-w-0 flex-1 rounded border border-slate-200 px-2 py-1 text-sm"
          />
        </div>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <label className="text-xs font-medium text-slate-500">Follow-up</label>
        <input
          type="date"
          value={followUp}
          onChange={(e) => setFollowUp(e.target.value)}
          onBlur={handleSaveFollowUp}
          className="rounded border border-slate-200 px-2 py-1 text-sm"
        />
      </div>
      {application.apply_url && (
        <a
          href={application.apply_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 inline-block text-xs text-blue-600 hover:underline"
        >
          Open apply link →
        </a>
      )}
    </article>
  );
}
