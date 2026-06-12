import { clsx } from "clsx";

interface ScoreCardProps {
  label: string;
  score: number | null;
  maxScore?: number;
  size?: "sm" | "md" | "lg";
  className?: string;
}

function scoreColor(score: number, max: number): string {
  const pct = score / max;
  if (pct >= 0.7) return "text-success";
  if (pct >= 0.4) return "text-warning";
  return "text-danger";
}

function scoreBg(score: number, max: number): string {
  const pct = score / max;
  if (pct >= 0.7) return "bg-success/10";
  if (pct >= 0.4) return "bg-warning/10";
  return "bg-danger/10";
}

/** Circular score display (0–100) with color coding. */
export default function ScoreCard({
  label,
  score,
  maxScore = 100,
  size = "md",
  className,
}: ScoreCardProps) {
  const displayScore = score != null ? Math.round(score) : "—";
  const dims = { sm: "w-16 h-16", md: "w-20 h-20", lg: "w-28 h-28" };
  const textSizes = { sm: "text-lg", md: "text-2xl", lg: "text-4xl" };

  return (
    <div
      className={clsx("flex flex-col items-center gap-2 animate-fade-in", className)}
      role="figure"
      aria-label={`${label}: ${displayScore}`}
    >
      <div
        className={clsx(
          "rounded-full flex items-center justify-center font-bold",
          dims[size],
          score != null
            ? [scoreColor(score, maxScore), scoreBg(score, maxScore)]
            : "bg-surface-100 text-surface-400",
          textSizes[size],
        )}
      >
        {displayScore}
      </div>
      <span className="metric-label text-center">{label}</span>
    </div>
  );
}
