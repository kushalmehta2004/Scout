"use client";

export type FilterState = {
  sort: "date" | "company" | "score";
  min_score: string;
  max_score: string;
  remote: "" | "true" | "false";
  source: string;
  listing_type: string;
  limit: number;
};

type FilterBarProps = {
  filters: FilterState;
  onFiltersChange: (f: FilterState) => void;
  total: number;
  showing: number;
};

const SOURCES = [
  { value: "", label: "All sources" },
  { value: "indeed", label: "Indeed" },
  { value: "hacker_news", label: "Hacker News" },
  { value: "ai_jobs", label: "AIJobs.net" },
  { value: "huggingface", label: "Hugging Face" },
  { value: "ycombinator", label: "Y Combinator" },
];

export function FilterBar({ filters, onFiltersChange, total, showing }: FilterBarProps) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-6">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Sort by</label>
          <select
            value={filters.sort}
            onChange={(e) =>
              onFiltersChange({ ...filters, sort: e.target.value as FilterState["sort"] })
            }
            className="w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="date">Date (newest)</option>
            <option value="score">Match score</option>
            <option value="company">Company</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Min score (0–100)</label>
          <input
            type="number"
            min={0}
            max={100}
            placeholder="Any"
            value={filters.min_score}
            onChange={(e) => onFiltersChange({ ...filters, min_score: e.target.value })}
            className="w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Max score (0–100)</label>
          <input
            type="number"
            min={0}
            max={100}
            placeholder="Any"
            value={filters.max_score}
            onChange={(e) => onFiltersChange({ ...filters, max_score: e.target.value })}
            className="w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Remote</label>
          <select
            value={filters.remote}
            onChange={(e) =>
              onFiltersChange({
                ...filters,
                remote: e.target.value as FilterState["remote"],
              })
            }
            className="w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">Any</option>
            <option value="true">Remote only</option>
            <option value="false">On-site / hybrid</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Type</label>
          <select
            value={filters.listing_type}
            onChange={(e) => onFiltersChange({ ...filters, listing_type: e.target.value })}
            className="w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All (jobs + internships)</option>
            <option value="job">Jobs only</option>
            <option value="internship">Internships only</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Source</label>
          <select
            value={filters.source}
            onChange={(e) => onFiltersChange({ ...filters, source: e.target.value })}
            className="w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {SOURCES.map((s) => (
              <option key={s.value || "all"} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm text-slate-600">
          Showing {showing} of {total} listings
        </span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Per page:</span>
          <select
            value={filters.limit}
            onChange={(e) =>
              onFiltersChange({ ...filters, limit: Number(e.target.value) })
            }
            className="rounded border border-slate-300 px-2 py-1 text-sm"
          >
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </div>
    </div>
  );
}
