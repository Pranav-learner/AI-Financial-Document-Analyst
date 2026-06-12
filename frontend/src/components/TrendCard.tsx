import { clsx } from "clsx";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import ReactECharts from "echarts-for-react";
import { memo } from "react";

interface TrendCardProps {
  label: string;
  value: string | number;
  change?: number | null;
  data?: number[];
  className?: string;
}

/** MetricCard variant with an embedded sparkline chart. */
function TrendCardInner({
  label,
  value,
  change,
  data,
  className,
}: TrendCardProps) {
  const isPositive = change != null && change > 0;
  const isNegative = change != null && change < 0;
  const color = isPositive ? "#22c55e" : isNegative ? "#ef4444" : "#64748b";

  const sparkOptions = data?.length
    ? {
        grid: { top: 0, right: 0, bottom: 0, left: 0 },
        xAxis: { show: false, type: "category" as const, data: data.map((_, i) => i) },
        yAxis: { show: false, type: "value" as const },
        series: [
          {
            type: "line" as const,
            data,
            smooth: true,
            symbol: "none",
            lineStyle: { width: 2, color },
            areaStyle: { color: `${color}15` },
          },
        ],
        tooltip: { show: false },
      }
    : null;

  return (
    <div
      className={clsx("glass-panel-hover p-5 animate-fade-in", className)}
      role="figure"
      aria-label={`${label}: ${value}`}
    >
      <div className="flex items-start justify-between">
        <div className="flex flex-col gap-1">
          <span className="metric-label">{label}</span>
          <span className="metric-value">{value}</span>
          {change != null && (
            <div className="flex items-center gap-1">
              {isPositive && <TrendingUp className="w-3 h-3 text-success" />}
              {isNegative && <TrendingDown className="w-3 h-3 text-danger" />}
              {!isPositive && !isNegative && <Minus className="w-3 h-3 text-surface-400" />}
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
            </div>
          )}
        </div>
        {sparkOptions && (
          <div className="w-24 h-12">
            <ReactECharts
              option={sparkOptions}
              style={{ width: "100%", height: "100%" }}
              opts={{ renderer: "svg" }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

const TrendCard = memo(TrendCardInner);
export default TrendCard;
