import { clsx } from "clsx";

interface ConfidenceBadgeProps {
  score: number;
  className?: string;
}

/** Confidence score indicator with color gradient. */
export default function ConfidenceBadge({
  score,
  className,
}: ConfidenceBadgeProps) {
  const pct = Math.round(score * 100);
  const style =
    pct >= 80
      ? "badge-success"
      : pct >= 50
        ? "badge-warning"
        : "badge-danger";

  return (
    <span className={clsx(style, className)} role="status" aria-label={`Confidence: ${pct}%`}>
      {pct}%
    </span>
  );
}
