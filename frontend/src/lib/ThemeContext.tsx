import { createContext, useContext, ReactNode } from "react";
import { useTheme, Theme } from "@/hooks/useTheme";

interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

/** Wraps the app and provides theme state to all children. */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const themeState = useTheme();
  return (
    <ThemeContext.Provider value={themeState}>{children}</ThemeContext.Provider>
  );
}

/** Consumes theme context; must be used inside <ThemeProvider>. */
export function useThemeContext(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useThemeContext must be used within ThemeProvider");
  return ctx;
}
