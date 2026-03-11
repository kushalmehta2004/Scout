"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getListingDetail,
  generateCoverLetter,
  updateCoverLetter,
  type CoverLetter as CoverLetterType,
  type ListingDetail,
} from "../lib/api";

const TONES = ["Professional", "Conversational", "Technical", "Enthusiastic"];

type CoverLetterEditorProps = {
  listingId: number;
  onClose: () => void;
};

export function CoverLetterEditor({ listingId, onClose }: CoverLetterEditorProps) {
  const [detail, setDetail] = useState<ListingDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedLetter, setSelectedLetter] = useState<CoverLetterType | null>(null);
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [tone, setTone] = useState("Professional");
  const [copyDone, setCopyDone] = useState(false);

  const fetchDetail = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const d = await getListingDetail(listingId);
      setDetail(d);
      const letters = d.cover_letters || [];
      if (letters.length > 0) {
        setSelectedLetter(letters[0]);
        setContent(letters[0].content);
      } else {
        setSelectedLetter(null);
        setContent("");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [listingId]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  useEffect(() => {
    if (selectedLetter) setContent(selectedLetter.content);
  }, [selectedLetter]);

  const handleRegenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      await generateCoverLetter(listingId, tone);
      await fetchDetail();
      const d = await getListingDetail(listingId);
      if (d.cover_letters?.length) {
        setSelectedLetter(d.cover_letters[0]);
        setContent(d.cover_letters[0].content);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generate failed");
    } finally {
      setGenerating(false);
    }
  };

  const handleSave = async () => {
    if (!selectedLetter) return;
    setSaving(true);
    setError(null);
    try {
      await updateCoverLetter(selectedLetter.id, content);
      await fetchDetail();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopyDone(true);
      setTimeout(() => setCopyDone(false), 2000);
    } catch {
      setError("Copy failed");
    }
  };

  const handleDownloadPdf = () => {
    const w = window.open("", "_blank");
    if (!w) return;
    w.document.write(`
      <!DOCTYPE html><html><head><title>Cover Letter</title></head>
      <body style="font-family: sans-serif; max-width: 700px; margin: 2rem auto; padding: 1rem;">
        <pre style="white-space: pre-wrap;">${content.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre>
      </body></html>
    `);
    w.document.close();
    w.print();
    w.close();
  };

  const handleDownloadDocx = () => {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `cover-letter-${detail?.company ?? "listing"}-v${selectedLetter?.version ?? 1}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) return <p className="p-4 text-slate-600">Loading…</p>;
  if (error && !detail) return <p className="p-4 text-red-600">{error}</p>;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-slate-200 p-4">
        <h2 className="text-lg font-semibold text-slate-900">
          Cover letter — {detail?.company} · {detail?.title}
        </h2>
        <button
          type="button"
          onClick={onClose}
          className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-50"
        >
          Close
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 p-4">
        {detail?.cover_letters && detail.cover_letters.length > 0 && (
          <select
            value={selectedLetter?.id ?? ""}
            onChange={(e) => {
              const id = Number(e.target.value);
              const letter = detail.cover_letters.find((c) => c.id === id);
              setSelectedLetter(letter ?? null);
            }}
            className="rounded border border-slate-300 px-3 py-1.5 text-sm"
          >
            {detail.cover_letters.map((c) => (
              <option key={c.id} value={c.id}>
                Version {c.version} {c.edited_by_user ? "(edited)" : ""}
              </option>
            ))}
          </select>
        )}
        <select
          value={tone}
          onChange={(e) => setTone(e.target.value)}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm"
        >
          {TONES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={handleRegenerate}
          disabled={generating}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50 hover:bg-blue-700"
        >
          {generating ? "Generating…" : "Regenerate"}
        </button>
        {selectedLetter && (
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save edits"}
          </button>
        )}
        <button
          type="button"
          onClick={handleCopy}
          className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-50"
        >
          {copyDone ? "Copied!" : "Copy"}
        </button>
        <button
          type="button"
          onClick={handleDownloadPdf}
          className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-50"
        >
          Download PDF
        </button>
        <button
          type="button"
          onClick={handleDownloadDocx}
          className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-50"
        >
          Download (.txt)
        </button>
      </div>

      {error && <p className="px-4 py-2 text-sm text-red-600">{error}</p>}

      <div className="flex-1 overflow-auto p-4">
        {detail?.cover_letters?.length === 0 && !generating ? (
          <p className="text-slate-500">
            No cover letter yet. Choose a tone and click Regenerate.
          </p>
        ) : (
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="min-h-[300px] w-full rounded border border-slate-300 p-3 text-sm leading-relaxed focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="Cover letter content…"
            spellCheck
          />
        )}
      </div>
    </div>
  );
}
