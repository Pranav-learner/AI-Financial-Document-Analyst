import { useState, useEffect, useCallback } from "react";

export type Theme = "light" | "dark";

/**
 * Hook for managing the application color theme (light / dark).
 * Persists the user's preference to localStorage and syncs the
 * `dark` class on the <html> element for Tailwind's class-based dark mode.
 */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    // Check localStorage first, then system preference
    const stored = localStorage.getItem("fin-analyst-theme") as Theme | null;
    if (stored === "dark" || stored === "light") return stored;
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  });

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    localStorage.setItem("fin-analyst-theme", theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  return { theme, toggleTheme };
}
