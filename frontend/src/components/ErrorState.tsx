import { clsx } from "clsx";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

/** Error display with retry button. */
export default function ErrorState({
  title = "Something went wrong",
  message = "We couldn't load the data. Please try again.",
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      className={clsx(
        "glass-panel border-danger/20 flex flex-col items-center justify-center py-14 px-6 text-center animate-fade-in",
        className,
      )}
      role="alert"
    >
      <div className="w-14 h-14 rounded-full bg-danger-light dark:bg-danger/20 flex items-center justify-center mb-4">
        <AlertTriangle className="w-7 h-7 text-danger" />
      </div>
      <h3 className="text-base font-semibold text-surface-800 dark:text-surface-200">{title}</h3>
      <p className="text-sm text-surface-500 dark:text-surface-400 mt-1 max-w-sm">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 flex items-center gap-2 px-4 py-2 text-sm font-medium text-brand-700 dark:text-brand-400 bg-brand-50 dark:bg-brand-950 rounded-lg hover:bg-brand-100 dark:hover:bg-brand-900 transition-colors"
          type="button"
        >
          <RefreshCw className="w-4 h-4" />
          Try again
        </button>
      )}
    </div>
  );
}
