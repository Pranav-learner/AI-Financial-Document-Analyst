import { clsx } from "clsx";
import { ArrowUpDown } from "lucide-react";
import { useState, useMemo } from "react";

export interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
  sortable?: boolean;
  align?: "left" | "center" | "right";
  width?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T) => string;
  className?: string;
  emptyMessage?: string;
}

/** Sortable, accessible data table with column definitions. */
export default function DataTable<T>({
  columns,
  data,
  keyExtractor,
  className,
  emptyMessage = "No data available",
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const sorted = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const va = (a as Record<string, unknown>)[sortKey];
      const vb = (b as Record<string, unknown>)[sortKey];
      if (va == null) return 1;
      if (vb == null) return -1;
      const cmp = va > vb ? 1 : va < vb ? -1 : 0;
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  function toggleSort(key: string) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const aligns = { left: "text-left", center: "text-center", right: "text-right" };

  if (!data.length) {
    return (
      <div className="glass-panel px-6 py-10 text-center text-sm text-surface-500">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className={clsx("glass-panel overflow-hidden", className)}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm" role="table">
          <thead>
            <tr className="border-b border-surface-200 dark:border-surface-700 bg-surface-50/60 dark:bg-surface-800/60">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={clsx(
                    "px-4 py-3 font-medium text-xs uppercase tracking-wider text-surface-500 dark:text-surface-400",
                    aligns[col.align ?? "left"],
                    col.width,
                  )}
                  scope="col"
                >
                  {col.sortable ? (
                    <button
                      onClick={() => toggleSort(col.key)}
                      className="inline-flex items-center gap-1 hover:text-surface-800 dark:hover:text-surface-200 transition-colors"
                      type="button"
                      aria-sort={
                        sortKey === col.key
                          ? sortDir === "asc"
                            ? "ascending"
                            : "descending"
                          : "none"
                      }
                    >
                      {col.header}
                      <ArrowUpDown className="w-3 h-3" />
                    </button>
                  ) : (
                    col.header
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-100 dark:divide-surface-700">
            {sorted.map((item) => (
              <tr
                key={keyExtractor(item)}
                className="hover:bg-surface-50/80 dark:hover:bg-surface-800/60 transition-colors"
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={clsx(
                      "px-4 py-3 text-surface-700 dark:text-surface-300",
                      aligns[col.align ?? "left"],
                    )}
                  >
                    {col.render
                      ? col.render(item)
                      : String(
                          (item as Record<string, unknown>)[col.key] ?? "—",
                        )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
