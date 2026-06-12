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
} from "lucide-react";
import { useState } from "react";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/financial", label: "Financial", icon: BarChart3 },
  { to: "/risks", label: "Risks", icon: ShieldAlert },
  { to: "/management", label: "Management", icon: Users },
  { to: "/benchmark", label: "Benchmark", icon: Target },
  { to: "/memos", label: "Memos", icon: FileText },
  { to: "/agent", label: "Analyst Chat", icon: MessageSquare },
] as const;

/** Navigation sidebar with route links and active state. */
export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={clsx(
        "h-screen sticky top-0 flex flex-col border-r border-surface-200 bg-white transition-all duration-200",
        collapsed ? "w-[68px]" : "w-[var(--sidebar-width)]",
      )}
      role="navigation"
      aria-label="Main navigation"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-surface-100">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shrink-0">
          <BarChart3 className="w-4 h-4 text-white" />
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <span className="text-sm font-bold text-surface-900 whitespace-nowrap">
              FinAnalyst
            </span>
            <span className="block text-[10px] text-surface-400 font-medium">
              AI Document Analyst
            </span>
          </div>
        )}
      </div>

      {/* Nav Links */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              clsx(isActive ? "nav-link-active" : "nav-link", collapsed && "justify-center px-2")
            }
            title={label}
            aria-label={label}
          >
            <Icon className="w-[18px] h-[18px] shrink-0" />
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Collapse Toggle */}
      <button
        onClick={() => setCollapsed((v) => !v)}
        className="flex items-center justify-center py-3 border-t border-surface-100 text-surface-400 hover:text-surface-600 transition-colors"
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
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
