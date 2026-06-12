import { clsx } from "clsx";
import { Trophy } from "lucide-react";

interface BenchmarkBadgeProps {
  rank?: number | null;
  percentile?: number | null;
  className?: string;
}

/** Rank/percentile badge for benchmark displays. */
export default function BenchmarkBadge({
  rank,
  percentile,
  className,
}: BenchmarkBadgeProps) {
  const label = rank != null ? `#${rank}` : percentile != null ? `P${Math.round(percentile)}` : "—";
  const style =
    rank === 1
      ? "bg-amber-100 text-amber-800 border-amber-300"
      : rank != null && rank <= 3
        ? "bg-surface-100 text-surface-700 border-surface-300"
        : "bg-surface-50 text-surface-600 border-surface-200";

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border",
        style,
        className,
      )}
      role="status"
    >
      {rank === 1 && <Trophy className="w-3 h-3" />}
      {label}
    </span>
  );
}
