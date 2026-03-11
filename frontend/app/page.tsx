"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getListings, getListingScore, getResume, uploadResume, getProfile, updateProfile } from "@/lib/api";
import type { Listing } from "@/lib/api";
import { CoverLetterEditor } from "@/components/CoverLetterEditor";
import { FilterBar, type FilterState } from "@/components/FilterBar";
import { ListingCard } from "@/components/ListingCard";

const defaultFilters: FilterState = {
  sort: "date",
  min_score: "",
  max_score: "",
  remote: "",
  source: "",
  listing_type: "",
  limit: 25,
};

export default function DashboardPage() {
  const [filters, setFilters] = useState<FilterState>(defaultFilters);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{ total: number; items: Listing[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [coverLetterListingId, setCoverLetterListingId] = useState<number | null>(null);
  const [scoringInProgress, setScoringInProgress] = useState(false);
  const [scoreMessage, setScoreMessage] = useState<string | null>(null);
  const [hasResume, setHasResume] = useState<boolean | null>(null);
  const [resumeUploading, setResumeUploading] = useState(false);
  const [resumeMessage, setResumeMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [profileSkills, setProfileSkills] = useState("");
  const [profileAbout, setProfileAbout] = useState("");
  const [profileRoles, setProfileRoles] = useState("");
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileMessage, setProfileMessage] = useState<string | null>(null);

  const fetchListings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const min = filters.min_score ? parseInt(filters.min_score, 10) : undefined;
      const max = filters.max_score ? parseInt(filters.max_score, 10) : undefined;
      const remote =
        filters.remote === ""
          ? undefined
          : filters.remote === "true";

      const res = await getListings({
        page,
        limit: filters.limit,
        sort: filters.sort,
        min_score: min !== undefined && !Number.isNaN(min) ? min : undefined,
        max_score: max !== undefined && !Number.isNaN(max) ? max : undefined,
        remote,
        source: filters.source || undefined,
        listing_type: filters.listing_type || undefined,
      });
      setData({ total: res.total, items: res.items });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load listings");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  useEffect(() => {
    getResume()
      .then((r) => setHasResume(r.resume != null))
      .catch(() => setHasResume(false));
  }, []);

  useEffect(() => {
    fetchListings();
  }, [fetchListings]);

  const onFiltersChange = useCallback((newFilters: FilterState) => {
    setFilters(newFilters);
    setPage(1);
  }, []);

  const totalPages = data && filters.limit > 0 ? Math.ceil(data.total / filters.limit) : 0;

  async function handleResumeUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const fn = file.name.toLowerCase();
    if (!fn.endsWith(".pdf") && !fn.endsWith(".docx") && !fn.endsWith(".doc")) {
      setResumeMessage("Only PDF and DOCX are supported.");
      setTimeout(() => setResumeMessage(null), 4000);
      e.target.value = "";
      return;
    }
    setResumeUploading(true);
    setResumeMessage(null);
    try {
      const result = await uploadResume(file);
      if (result.ok) {
        setHasResume(true);
        setResumeMessage("Resume uploaded. You can score listings now.");
      } else {
        setResumeMessage(result.error || "Upload failed.");
      }
    } catch (err) {
      setResumeMessage(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setResumeUploading(false);
      e.target.value = "";
    }
    setTimeout(() => setResumeMessage(null), 5000);
  }

  async function openProfileModal() {
    setShowProfileModal(true);
    setProfileMessage(null);
    try {
      const { profile } = await getProfile();
      setProfileSkills((profile.custom_skills || []).join(", "));
      setProfileAbout(profile.about_me || "");
      setProfileRoles((profile.preferred_roles || []).join(", "));
    } catch {
      setProfileSkills("");
      setProfileAbout("");
      setProfileRoles("");
    }
  }

  async function handleSaveProfile() {
    setProfileSaving(true);
    setProfileMessage(null);
    try {
      const custom_skills = profileSkills
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const preferred_roles = profileRoles
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      await updateProfile({
        custom_skills,
        about_me: profileAbout.trim(),
        preferred_roles,
      });
      setProfileMessage("Profile saved. Scoring and cover letters will use resume + this info.");
      setTimeout(() => setProfileMessage(null), 4000);
    } catch (e) {
      setProfileMessage(e instanceof Error ? e.message : "Save failed.");
    } finally {
      setProfileSaving(false);
    }
  }

  async function handleScoreThisPage() {
    if (!data?.items.length) return;
    const withoutScore = data.items.filter(
      (l) => !l.score || l.score.overall_score == null || l.score.overall_score === 0
    );
    if (withoutScore.length === 0) {
      setScoreMessage("All visible listings already have scores.");
      setTimeout(() => setScoreMessage(null), 3000);
      return;
    }
    setScoringInProgress(true);
    setScoreMessage(null);
    let done = 0;
    let lastError: string | null = null;
    for (const listing of withoutScore) {
      try {
        const hasCachedZero = listing.score?.overall_score === 0;
        await getListingScore(listing.id, { refresh: hasCachedZero });
        done++;
      } catch (e) {
        lastError = e instanceof Error ? e.message : String(e);
        if (lastError.toLowerCase().includes("resume")) break;
      }
      await new Promise((r) => setTimeout(r, 300));
    }
    setScoringInProgress(false);
    if (lastError && done === 0) setScoreMessage(lastError);
    else if (done > 0) setScoreMessage(`Scored ${done} listing(s). Refreshing…`);
    if (done > 0) await fetchListings();
    setTimeout(() => setScoreMessage(null), 5000);
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-slate-900">Scout — Job Listings</h1>
        <div className="flex flex-wrap items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.doc,.docx"
            className="hidden"
            onChange={handleResumeUpload}
            disabled={resumeUploading}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={resumeUploading}
            className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {resumeUploading ? "Uploading…" : hasResume ? "Replace resume" : "Upload resume"}
          </button>
          <button
            type="button"
            onClick={openProfileModal}
            className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            My profile
          </button>
          {hasResume === true && (
            <span className="text-xs text-slate-500">PDF/DOCX • Used with profile for scores</span>
          )}
          <Link
            href="/tracker"
            className="text-sm font-medium text-slate-600 hover:text-slate-900"
          >
            Application Tracker →
          </Link>
        </div>
      </div>

      {resumeMessage && (
        <p
          className={`mb-4 text-sm ${resumeMessage.startsWith("Resume uploaded") ? "text-emerald-700" : "text-amber-700"}`}
          role="status"
        >
          {resumeMessage}
        </p>
      )}

      <FilterBar
        filters={filters}
        onFiltersChange={onFiltersChange}
        total={data?.total ?? 0}
        showing={data?.items?.length ?? 0}
      />

      {!loading && data && data.items.length > 0 && (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={handleScoreThisPage}
            disabled={scoringInProgress}
            className="rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {scoringInProgress ? "Scoring…" : "Score this page"}
          </button>
          <span className="text-xs text-slate-500">
            Match scores use resume + profile (My profile). Add both for best results; GROQ_API_KEY required.
          </span>
        </div>
      )}

      {scoreMessage && (
        <p className={`mt-2 text-sm ${scoreMessage.startsWith("Scored") ? "text-emerald-700" : "text-amber-700"}`} role="status">
          {scoreMessage}
        </p>
      )}

      {loading && (
        <p className="mt-6 text-center text-slate-500">Loading listings…</p>
      )}

      {error && (
        <p className="mt-6 text-center text-red-600">{error}</p>
      )}

      {!loading && !error && data && data.items.length === 0 && (
        <p className="mt-6 text-center text-slate-500">No listings match your filters.</p>
      )}

      {!loading && !error && data && data.items.length > 0 && (
        <>
          <ul className="mt-6 space-y-4">
            {data.items.map((listing) => (
              <li key={listing.id}>
                <ListingCard
                  listing={listing}
                  onViewCoverLetter={setCoverLetterListingId}
                />
              </li>
            ))}
          </ul>

          <div className="mt-8 flex items-center justify-center gap-4">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="rounded border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-50 hover:bg-slate-50"
            >
              Previous
            </button>
            <span className="text-sm text-slate-600">
              Page {page} of {totalPages || 1}
            </span>
            <button
              type="button"
              onClick={() => setPage((p) => p + 1)}
              disabled={page >= totalPages}
              className="rounded border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-50 hover:bg-slate-50"
            >
              Next
            </button>
          </div>
        </>
      )}

      {coverLetterListingId != null && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="dialog"
          aria-modal="true"
          onClick={() => setCoverLetterListingId(null)}
        >
          <div
            className="h-[85vh] w-full max-w-3xl overflow-hidden rounded-lg bg-white shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <CoverLetterEditor
              listingId={coverLetterListingId}
              onClose={() => setCoverLetterListingId(null)}
            />
          </div>
        </div>
      )}

      {showProfileModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="profile-modal-title"
          onClick={() => !profileSaving && setShowProfileModal(false)}
        >
          <div
            className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="profile-modal-title" className="text-lg font-semibold text-slate-900">
              My profile
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Add skills and info not on your resume. Used with your resume for match scores and cover letters.
            </p>
            <div className="mt-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700">Additional skills (comma-separated)</label>
                <input
                  type="text"
                  value={profileSkills}
                  onChange={(e) => setProfileSkills(e.target.value)}
                  placeholder="e.g. Python, React, AWS, leadership"
                  className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">About me / extra info</label>
                <textarea
                  value={profileAbout}
                  onChange={(e) => setProfileAbout(e.target.value)}
                  placeholder="Short bio, what you're looking for, key achievements..."
                  rows={4}
                  className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">Preferred roles (comma-separated)</label>
                <input
                  type="text"
                  value={profileRoles}
                  onChange={(e) => setProfileRoles(e.target.value)}
                  placeholder="e.g. Software Engineer, Frontend Developer"
                  className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
            {profileMessage && (
              <p className={`mt-3 text-sm ${profileMessage.startsWith("Profile saved") ? "text-emerald-700" : "text-amber-700"}`}>
                {profileMessage}
              </p>
            )}
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => !profileSaving && setShowProfileModal(false)}
                className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Close
              </button>
              <button
                type="button"
                onClick={handleSaveProfile}
                disabled={profileSaving}
                className="rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
              >
                {profileSaving ? "Saving…" : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
