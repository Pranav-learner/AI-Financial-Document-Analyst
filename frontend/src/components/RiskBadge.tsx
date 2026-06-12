import { clsx } from "clsx";

interface RiskBadgeProps {
  severity: string;
  className?: string;
}

const severityStyles: Record<string, string> = {
  HIGH: "badge-danger",
  CRITICAL: "badge-danger",
  MEDIUM: "badge-warning",
  MODERATE: "badge-warning",
  LOW: "badge-success",
  MINIMAL: "badge-success",
};

/** Severity-colored risk badge (HIGH/MEDIUM/LOW). */
export default function RiskBadge({ severity, className }: RiskBadgeProps) {
  const style = severityStyles[severity.toUpperCase()] ?? "badge-neutral";
  return (
    <span className={clsx(style, className)} role="status">
      {severity}
    </span>
  );
}
