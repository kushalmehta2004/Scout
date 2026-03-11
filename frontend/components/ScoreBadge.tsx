"use client";

type ScoreBadgeProps = {
  score: number | null;
  label?: boolean;
};

export function ScoreBadge({ score, label = true }: ScoreBadgeProps) {
  if (score === null || score === undefined) {
    return (
      <span className="inline-flex items-center rounded-full bg-slate-200 px-2.5 py-0.5 text-xs font-medium text-slate-600">
        {label ? "No score" : "—"}
      </span>
    );
  }

  const clamped = Math.max(0, Math.min(100, score));
  let bg = "bg-red-100 text-red-800";
  if (clamped >= 70) bg = "bg-green-100 text-green-800";
  else if (clamped >= 40) bg = "bg-amber-100 text-amber-800";

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${bg}`}
      title={`Match score: ${clamped}`}
    >
      {label ? `${clamped}%` : clamped}
    </span>
  );
}
