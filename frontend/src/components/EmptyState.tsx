import { clsx } from "clsx";
import { Inbox } from "lucide-react";

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

/** Friendly empty state with icon and optional CTA. */
export default function EmptyState({
  title = "No data yet",
  description = "Data will appear here once available.",
  icon,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={clsx(
        "glass-panel flex flex-col items-center justify-center py-16 px-6 text-center animate-fade-in",
        className,
      )}
      role="status"
    >
      <div className="w-14 h-14 rounded-full bg-surface-100 flex items-center justify-center mb-4">
        {icon ?? <Inbox className="w-7 h-7 text-surface-400" />}
      </div>
      <h3 className="text-base font-semibold text-surface-700">{title}</h3>
      <p className="text-sm text-surface-500 mt-1 max-w-sm">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
