import { clsx } from "clsx";
import {
  AlertTriangle,
  Info,
  AlertCircle,
  CheckCircle,
} from "lucide-react";

interface InsightCardProps {
  title: string;
  description: string;
  severity?: "info" | "warning" | "danger" | "success";
  className?: string;
}

const icons = {
  info: <Info className="w-4 h-4" />,
  warning: <AlertTriangle className="w-4 h-4" />,
  danger: <AlertCircle className="w-4 h-4" />,
  success: <CheckCircle className="w-4 h-4" />,
};

const styles = {
  info: "border-info/30 bg-info-light/30",
  warning: "border-warning/30 bg-warning-light/30",
  danger: "border-danger/30 bg-danger-light/30",
  success: "border-success/30 bg-success-light/30",
};

const iconColors = {
  info: "text-info",
  warning: "text-warning",
  danger: "text-danger",
  success: "text-success",
};

/** Text card for qualitative insights with severity indicator. */
export default function InsightCard({
  title,
  description,
  severity = "info",
  className,
}: InsightCardProps) {
  return (
    <div
      className={clsx(
        "rounded-xl border p-4 animate-fade-in",
        styles[severity],
        className,
      )}
      role="article"
      aria-label={title}
    >
      <div className="flex items-start gap-3">
        <span className={clsx("mt-0.5 shrink-0", iconColors[severity])}>
          {icons[severity]}
        </span>
        <div>
          <h4 className="text-sm font-semibold text-surface-800">{title}</h4>
          <p className="text-sm text-surface-600 mt-1 leading-relaxed">
            {description}
          </p>
        </div>
      </div>
    </div>
  );
}
