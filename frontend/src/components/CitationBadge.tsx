import { clsx } from "clsx";
import { FileText } from "lucide-react";

interface CitationBadgeProps {
  sectionName?: string | null;
  pageNumber?: number | null;
  sourceType?: string;
  onClick?: () => void;
  className?: string;
}

/** Clickable badge showing citation source details. */
export default function CitationBadge({
  sectionName,
  pageNumber,
  sourceType,
  onClick,
  className,
}: CitationBadgeProps) {
  const parts: string[] = [];
  if (sourceType) parts.push(sourceType);
  if (sectionName) parts.push(sectionName);
  if (pageNumber != null) parts.push(`p.${pageNumber}`);

  const label = parts.join(" · ") || "Citation";

  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium",
        "bg-brand-50 text-brand-700 hover:bg-brand-100 transition-colors",
        "border border-brand-200/50",
        className,
      )}
      title={label}
      aria-label={`Citation: ${label}`}
    >
      <FileText className="w-3 h-3" />
      {label}
    </button>
  );
}
