import { clsx } from "clsx";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string | number;
  change?: number | null;
  changeLabel?: string;
  icon?: React.ReactNode;
  className?: string;
}

/** Displays a single KPI with label, value, and optional trend indicator. */
export default function MetricCard({
  label,
  value,
  change,
  changeLabel,
  icon,
  className,
}: MetricCardProps) {
  const isPositive = change != null && change > 0;
  const isNegative = change != null && change < 0;

  return (
    <div
      className={clsx(
        "glass-panel-hover p-5 flex flex-col gap-2 animate-fade-in",
        className,
      )}
      role="figure"
      aria-label={`${label}: ${value}`}
    >
      <div className="flex items-center justify-between">
        <span className="metric-label">{label}</span>
        {icon && (
          <span className="text-surface-400" aria-hidden="true">
            {icon}
          </span>
        )}
      </div>
      <span className="metric-value">{value}</span>
      {change != null && (
        <div className="flex items-center gap-1.5">
          {isPositive && <TrendingUp className="w-3.5 h-3.5 text-success" aria-hidden="true" />}
          {isNegative && <TrendingDown className="w-3.5 h-3.5 text-danger" aria-hidden="true" />}
          {!isPositive && !isNegative && <Minus className="w-3.5 h-3.5 text-surface-400" aria-hidden="true" />}
          <span
            className={clsx("text-xs font-medium", {
              "text-success-dark": isPositive,
              "text-danger-dark": isNegative,
              "text-surface-500": !isPositive && !isNegative,
            })}
          >
            {isPositive ? "+" : ""}
            {change.toFixed(1)}%
          </span>
          {changeLabel && (
            <span className="text-xs text-surface-400">{changeLabel}</span>
          )}
        </div>
      )}
    </div>
  );
}
