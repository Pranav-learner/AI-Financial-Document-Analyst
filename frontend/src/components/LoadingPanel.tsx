import { clsx } from "clsx";

interface LoadingPanelProps {
  rows?: number;
  className?: string;
}

/** Skeleton loading state with shimmer animation. */
export default function LoadingPanel({
  rows = 4,
  className,
}: LoadingPanelProps) {
  return (
    <div
      className={clsx("glass-panel p-6 space-y-4", className)}
      role="status"
      aria-label="Loading"
    >
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="space-y-2">
          <div
            className="h-4 rounded-lg bg-gradient-to-r from-surface-100 via-surface-200 to-surface-100 dark:from-surface-800 dark:via-surface-700 dark:to-surface-800 animate-shimmer"
            style={{
              backgroundSize: "200% 100%",
              width: `${70 + Math.random() * 30}%`,
            }}
          />
          {i === 0 && (
            <div
              className="h-3 rounded-lg bg-gradient-to-r from-surface-100 via-surface-200 to-surface-100 dark:from-surface-800 dark:via-surface-700 dark:to-surface-800 animate-shimmer"
              style={{ backgroundSize: "200% 100%", width: "40%" }}
            />
          )}
        </div>
      ))}
      <span className="sr-only">Loading content…</span>
    </div>
  );
}
