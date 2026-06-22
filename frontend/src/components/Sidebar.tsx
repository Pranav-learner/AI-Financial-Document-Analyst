import { clsx } from "clsx";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  BarChart3,
  ShieldAlert,
  Users,
  Target,
  FileText,
  MessageSquare,
  ChevronLeft,
  UploadCloud,
} from "lucide-react";
import { useState, useEffect } from "react";
import { useObservability } from "@/hooks/useObservability";

const navGroups = [
  {
    title: "OVERVIEW",
    links: [
      { to: "/", label: "Dashboard", icon: LayoutDashboard },
      { to: "/upload", label: "Upload", icon: UploadCloud },
    ],
  },
  {
    title: "ANALYSIS",
    links: [
      { to: "/financial", label: "Financial", icon: BarChart3 },
      { to: "/risks", label: "Risks", icon: ShieldAlert },
      { to: "/management", label: "Management", icon: Users },
    ],
  },
  {
    title: "TOOLS",
    links: [
      { to: "/benchmark", label: "Benchmark", icon: Target },
      { to: "/memos", label: "Memos", icon: FileText },
      { to: "/agent", label: "Analyst Chat", icon: MessageSquare },
    ],
  },
];

/** Navigation sidebar with route links and active state. */
export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const { trackInteraction } = useObservability();

  // Handle keyboard shortcut for collapsing sidebar: Ctrl + B
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === "b") {
        e.preventDefault();
        toggleCollapse();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const toggleCollapse = () => {
    setCollapsed((v) => {
      const next = !v;
      trackInteraction("Sidebar Toggle", next ? "Collapsed" : "Expanded");
      return next;
    });
  };

  return (
    <aside
      className={clsx(
        "h-screen sticky top-0 flex flex-col bg-white dark:bg-[#0f172a] border-r border-surface-200 dark:border-surface-800 transition-all duration-200 shadow-sm shrink-0",
        collapsed ? "w-[68px]" : "w-[240px]",
      )}
      role="navigation"
      aria-label="Main navigation"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-surface-100 dark:border-surface-800 mb-2">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-600 to-brand-700 flex items-center justify-center shrink-0">
          <BarChart3 className="w-4 h-4 text-white" />
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <span className="text-sm font-bold text-surface-900 dark:text-surface-50 whitespace-nowrap">
              FinAnalyst
            </span>
            <span className="block text-[10px] text-surface-400 font-medium">
              AI Document Analyst
            </span>
          </div>
        )}
      </div>

      {/* Nav Links */}
      <nav className="flex-1 py-4 overflow-y-auto space-y-6">
        {navGroups.map((group, idx) => (
          <div key={idx}>
            {!collapsed && (
              <h4 className="px-6 mb-2 text-[11px] font-bold tracking-widest text-surface-500 uppercase">
                {group.title}
              </h4>
            )}
            <div className="space-y-1">
              {group.links.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/"}
                  className={({ isActive }) =>
                    clsx(
                      "relative flex items-center gap-3 px-3 py-2.5 mx-3 text-sm font-medium transition-all duration-150 rounded-lg outline-none",
                      isActive
                        ? "bg-brand-50 text-brand-700 dark:bg-[#2d1155] dark:text-[#c084fc]"
                        : "text-surface-600 hover:bg-surface-50 hover:text-surface-900 dark:text-surface-400 dark:hover:bg-surface-800/50 dark:hover:text-surface-200",
                      collapsed && "justify-center px-2 mx-2"
                    )
                  }
                  title={label}
                  aria-label={label}
                >
                  {({ isActive }) => (
                    <>
                      {isActive && (
                        <div className="absolute left-0 top-0 bottom-0 w-1 bg-brand-500 rounded-l-lg" />
                      )}
                      <Icon className="w-[18px] h-[18px] shrink-0" />
                      {!collapsed && <span>{label}</span>}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Version Label */}
      <div className="px-3 py-2 border-t border-surface-100 dark:border-surface-700">
        {collapsed ? (
          <div className="flex justify-center">
            <span className="inline-block w-2 h-2 rounded-full bg-brand-500" title="v1.0.0" />
          </div>
        ) : (
          <span className="text-[10px] font-medium text-surface-400 dark:text-surface-500 tracking-wide">
            v1.0.0
          </span>
        )}
      </div>

      {/* Collapse Toggle */}
      <button
        onClick={toggleCollapse}
        className="flex items-center justify-center py-3 border-t border-surface-100 dark:border-surface-800 text-surface-400 hover:text-surface-600 hover:bg-surface-50 dark:text-surface-500 dark:hover:text-surface-300 dark:hover:bg-surface-800/50 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-inset"
        aria-label={collapsed ? "Expand sidebar (Ctrl+B)" : "Collapse sidebar (Ctrl+B)"}
        type="button"
      >
        <ChevronLeft
          className={clsx(
            "w-4 h-4 transition-transform duration-200",
            collapsed && "rotate-180",
          )}
        />
      </button>
    </aside>
  );
}

