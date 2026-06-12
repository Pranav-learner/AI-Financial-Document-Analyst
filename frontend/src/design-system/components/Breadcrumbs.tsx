import { Link, useLocation } from "react-router-dom";
import { ChevronRight, Home } from "lucide-react";

const routeMap: Record<string, string> = {
  financial: "Financial Analysis",
  risks: "Risk Intelligence",
  management: "Management Tone",
  benchmark: "Benchmark Analysis",
  memos: "Investment Memos",
  agent: "Analyst Chat",
};

/**
 * Accessible, semantic Breadcrumbs component to support navigation structure.
 */
export default function Breadcrumbs() {
  const { pathname } = useLocation();
  const pathnames = pathname.split("/").filter((x) => x);

  return (
    <nav className="flex" aria-label="Breadcrumb">
      <ol className="inline-flex items-center space-x-1 md:space-x-2">
        <li className="inline-flex items-center">
          <Link
            to="/"
            className="inline-flex items-center text-xs font-medium text-surface-500 hover:text-brand-600 transition-colors"
          >
            <Home className="w-3.5 h-3.5 mr-1" aria-hidden="true" />
            Home
          </Link>
        </li>
        {pathnames.map((value, index) => {
          const to = `/${pathnames.slice(0, index + 1).join("/")}`;
          const isLast = index === pathnames.length - 1;
          const name = routeMap[value] || value;

          return (
            <li key={to} className="flex items-center">
              <ChevronRight className="w-3 h-3 text-surface-400 mx-1 shrink-0" aria-hidden="true" />
              {isLast ? (
                <span
                  className="text-xs font-semibold text-surface-800"
                  aria-current="page"
                >
                  {name}
                </span>
              ) : (
                <Link
                  to={to}
                  className="text-xs font-medium text-surface-500 hover:text-brand-600 transition-colors"
                >
                  {name}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
