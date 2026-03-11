"use client";

import { useState } from "react";
import type { Listing } from "../lib/api";
import { applyToListing, saveListingForLater } from "../lib/api";
import { ScoreBadge } from "./ScoreBadge";

type ListingCardProps = {
  listing: Listing;
  onViewCoverLetter?: (listingId: number) => void;
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return "—";
  }
}

export function ListingCard({ listing, onViewCoverLetter }: ListingCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [applying, setApplying] = useState(false);
  const [applyMessage, setApplyMessage] = useState<string | null>(null);
  const [savingForLater, setSavingForLater] = useState(false);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);
  const score = listing.score?.overall_score ?? null;

  async function handleSaveForLater() {
    setSavingForLater(true);
    setSavedMessage(null);
    try {
      await saveListingForLater(listing.id);
      setSavedMessage("Saved for later. View in Tracker.");
      setTimeout(() => setSavedMessage(null), 4000);
    } catch (e) {
      setSavedMessage(e instanceof Error ? e.message : "Save failed.");
      setTimeout(() => setSavedMessage(null), 4000);
    } finally {
      setSavingForLater(false);
    }
  }

  async function handleConfirmApply() {
    if (!listing.apply_url) return;
    setApplying(true);
    setApplyMessage(null);
    try {
      const result = await applyToListing(listing.id);
      setShowApplyModal(false);
      if (result.ok && result.method !== "manual") {
        setApplyMessage("Form filled in the browser—review and click Submit when ready.");
      } else {
        if (result.apply_url) window.open(result.apply_url, "_blank");
        if (result.cover_letter_text) {
          await navigator.clipboard.writeText(result.cover_letter_text);
          setApplyMessage("Apply page opened — cover letter copied to clipboard.");
        } else {
          setApplyMessage("Apply page opened — paste your cover letter there.");
        }
        setTimeout(() => setApplyMessage(null), 6000);
      }
    } catch (e) {
      setApplyMessage(e instanceof Error ? e.message : "Apply failed.");
      setTimeout(() => setApplyMessage(null), 5000);
    } finally {
      setApplying(false);
    }
  }

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold text-slate-900">{listing.title}</h2>
          <p className="text-sm text-slate-600">{listing.company}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span>{listing.location || "Remote"}</span>
            {listing.remote && (
              <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-emerald-800">
                Remote
              </span>
            )}
            {listing.listing_type === "internship" && (
              <span className="rounded bg-amber-100 px-1.5 py-0.5 text-amber-800">
                Internship
              </span>
            )}
            {listing.listing_type === "job" && (
              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-700">
                Job
              </span>
            )}
            <span>·</span>
            <span>{listing.source}</span>
            <span>·</span>
            <span>{formatDate(listing.date_posted)}</span>
          </div>
        </div>
        <ScoreBadge score={score} />
      </div>

      {listing.description && (
        <div className="mt-3">
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="text-sm font-medium text-slate-600 underline hover:text-slate-900"
          >
            {expanded ? "Hide description" : "Show description"}
          </button>
          {expanded && (
            <div
              className="mt-2 max-h-48 overflow-y-auto rounded border border-slate-100 bg-slate-50 p-3 text-sm text-slate-700"
              dangerouslySetInnerHTML={{ __html: listing.description }}
            />
          )}
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        {onViewCoverLetter && (
          <button
            type="button"
            onClick={() => onViewCoverLetter(listing.id)}
            className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            View Cover Letter
          </button>
        )}
        <button
          type="button"
          onClick={handleSaveForLater}
          disabled={savingForLater}
          className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {savingForLater ? "Saving…" : "Save for Later"}
        </button>
        {listing.apply_url && (
          <button
            type="button"
            onClick={() => setShowApplyModal(true)}
            className="inline-block rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-blue-600 hover:bg-slate-50"
          >
            Apply Now
          </button>
        )}
      </div>

      {savedMessage && (
        <p className="mt-2 text-sm text-slate-700" role="status">
          {savedMessage}
        </p>
      )}
      {applyMessage && (
        <p className="mt-2 text-sm text-emerald-700" role="status">
          {applyMessage}
        </p>
      )}

      {showApplyModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => !applying && setShowApplyModal(false)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="apply-modal-title"
        >
          <div
            className="w-full max-w-md rounded-lg bg-white p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 id="apply-modal-title" className="text-lg font-semibold text-slate-900">
              Submit application?
            </h3>
            <p className="mt-2 text-sm text-slate-600">
              We’ll fill in the application form (name, email, cover letter, resume) and open it in a
              browser. You review and click Submit yourself—we never auto-submit.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => !applying && setShowApplyModal(false)}
                className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmApply}
                disabled={applying}
                className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {applying ? "Applying…" : "Apply"}
              </button>
            </div>
          </div>
        </div>
      )}
    </article>
  );
}
