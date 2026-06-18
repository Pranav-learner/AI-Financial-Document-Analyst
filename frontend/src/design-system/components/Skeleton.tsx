import { clsx } from "clsx";

interface SkeletonProps {
  className?: string;
  variant?: "text" | "rectangular" | "circular" | "card" | "table" | "chart" | "memo" | "chat";
}

/**
 * High-fidelity Skeleton/Shimmer loader component to replace standard spinners.
 */
export default function Skeleton({ className, variant = "rectangular" }: SkeletonProps) {
  const baseClass = "bg-surface-200/80 dark:bg-surface-700/80 animate-shimmer relative overflow-hidden rounded";

  if (variant === "text") {
    return <div className={clsx(baseClass, "h-4 w-3/4", className)} />;
  }

  if (variant === "circular") {
    return <div className={clsx(baseClass, "rounded-full", className)} />;
  }

  if (variant === "card") {
    return (
      <div className={clsx("glass-panel p-5 space-y-4 animate-pulse", className)}>
        <div className="flex justify-between items-center">
          <div className="h-4 w-1/3 bg-surface-200 dark:bg-surface-700 rounded" />
          <div className="h-5 w-5 bg-surface-200 dark:bg-surface-700 rounded-full" />
        </div>
        <div className="h-8 w-2/3 bg-surface-200 dark:bg-surface-700 rounded" />
        <div className="h-3 w-1/2 bg-surface-200 dark:bg-surface-700 rounded" />
      </div>
    );
  }

  if (variant === "table") {
    return (
      <div className={clsx("glass-panel p-4 space-y-3 animate-pulse", className)}>
        <div className="grid grid-cols-4 gap-4 pb-2 border-b border-surface-150">
          <div className="h-4 bg-surface-200 rounded" />
          <div className="h-4 bg-surface-200 rounded" />
          <div className="h-4 bg-surface-200 rounded" />
          <div className="h-4 bg-surface-200 rounded" />
        </div>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="grid grid-cols-4 gap-4 py-2">
            <div className="h-3 bg-surface-100 rounded" />
            <div className="h-3 bg-surface-100 rounded" />
            <div className="h-3 bg-surface-100 rounded" />
            <div className="h-3 bg-surface-100 rounded" />
          </div>
        ))}
      </div>
    );
  }

  if (variant === "chart") {
    return (
      <div className={clsx("glass-panel p-5 flex flex-col justify-between h-[300px] animate-pulse", className)}>
        <div className="h-4 w-1/4 bg-surface-200 rounded" />
        <div className="flex items-end gap-3 h-48 px-4">
          <div className="h-[20%] w-full bg-surface-100 rounded-t" />
          <div className="h-[40%] w-full bg-surface-100 rounded-t" />
          <div className="h-[75%] w-full bg-surface-100 rounded-t" />
          <div className="h-[50%] w-full bg-surface-100 rounded-t" />
          <div className="h-[90%] w-full bg-surface-100 rounded-t" />
        </div>
        <div className="flex justify-between px-4">
          <div className="h-2 w-8 bg-surface-100 rounded" />
          <div className="h-2 w-8 bg-surface-100 rounded" />
          <div className="h-2 w-8 bg-surface-100 rounded" />
          <div className="h-2 w-8 bg-surface-100 rounded" />
          <div className="h-2 w-8 bg-surface-100 rounded" />
        </div>
      </div>
    );
  }

  if (variant === "memo") {
    return (
      <div className={clsx("glass-panel p-6 space-y-6 animate-pulse", className)}>
        <div className="space-y-2">
          <div className="h-6 w-1/2 bg-surface-200 rounded" />
          <div className="h-3 w-1/4 bg-surface-200 rounded" />
        </div>
        <div className="space-y-3">
          <div className="h-4 w-full bg-surface-100 rounded" />
          <div className="h-4 w-[95%] bg-surface-100 rounded" />
          <div className="h-4 w-[98%] bg-surface-100 rounded" />
          <div className="h-4 w-[90%] bg-surface-100 rounded" />
        </div>
      </div>
    );
  }

  if (variant === "chat") {
    return (
      <div className={clsx("space-y-4 animate-pulse", className)}>
        <div className="flex items-start gap-3">
          <div className="h-8 w-8 rounded-full bg-surface-200 shrink-0" />
          <div className="space-y-2 bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-xl px-4 py-3 max-w-[70%] flex-1">
            <div className="h-3 bg-surface-200 rounded w-5/6" />
            <div className="h-3 bg-surface-200 rounded w-full" />
            <div className="h-3 bg-surface-200 rounded w-4/5" />
          </div>
        </div>
      </div>
    );
  }

  return <div className={clsx(baseClass, "h-10 w-full", className)} />;
}
