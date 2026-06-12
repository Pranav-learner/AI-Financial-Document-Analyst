import { clsx } from "clsx";
import { ChevronDown } from "lucide-react";
import { useState } from "react";

interface SectionPanelProps {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  badge?: React.ReactNode;
  className?: string;
}

/** Collapsible section panel for grouping related content. */
export default function SectionPanel({
  title,
  children,
  defaultOpen = true,
  badge,
  className,
}: SectionPanelProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={clsx("glass-panel overflow-hidden", className)}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-surface-50 transition-colors"
        aria-expanded={open}
        type="button"
      >
        <div className="flex items-center gap-3">
          <h3 className="section-title">{title}</h3>
          {badge}
        </div>
        <ChevronDown
          className={clsx(
            "w-5 h-5 text-surface-400 transition-transform duration-200",
            open && "rotate-180",
          )}
        />
      </button>
      {open && <div className="px-5 pb-5 animate-fade-in">{children}</div>}
    </div>
  );
}
