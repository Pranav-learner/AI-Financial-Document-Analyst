/**
 * Design system tokens defining spacing, typography, colors, border-radii,
 * transitions, shadows, and layout constants.
 */
export const TOKENS = {
  // Spacing Scale (rem)
  spacing: {
    xs: "0.25rem",   // 4px
    sm: "0.5rem",    // 8px
    md: "1rem",      // 16px
    lg: "1.5rem",    // 24px
    xl: "2rem",      // 32px
    xxl: "3rem",     // 48px
  },

  // Typography Hierarchy
  typography: {
    fontFamily: "Inter, system-ui, sans-serif",
    fontSize: {
      xs: "0.75rem",   // 12px
      sm: "0.875rem",  // 14px
      base: "1rem",    // 16px
      lg: "1.125rem",  // 18px
      xl: "1.25rem",   // 20px
      xxl: "1.5rem",   // 24px
      h1: "2rem",      // 32px
    },
    fontWeight: {
      light: 300,
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
  },

  // Border Radius Scale
  borderRadius: {
    sm: "0.25rem",   // 4px
    md: "0.5rem",    // 8px
    lg: "0.75rem",   // 12px
    xl: "1rem",      // 16px
    full: "9999px",
  },

  // Shadow/Elevation Levels
  elevation: {
    none: "none",
    sm: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    md: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    lg: "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
    xl: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
  },

  // Transition durations
  transitions: {
    fast: "100ms cubic-bezier(0.4, 0, 0.2, 1)",
    normal: "200ms cubic-bezier(0.4, 0, 0.2, 1)",
    slow: "300ms cubic-bezier(0.4, 0, 0.2, 1)",
  },

  // Standard layouts properties
  layout: {
    sidebarWidth: "240px",
    sidebarCollapsedWidth: "68px",
    maxContentWidth: "1280px",
    headerHeight: "64px",
  },

  // Palette theme mapping (RGB/Hex)
  colors: {
    brand: {
      50: "#eef2ff",
      100: "#e0e7ff",
      500: "#6366f1",
      600: "#4f46e5",
      700: "#4338ca",
    },
    surface: {
      50: "#f8fafc",
      100: "#f1f5f9",
      200: "#e2e8f0",
      500: "#64748b",
      800: "#1e293b",
      900: "#0f172a",
    },
    success: {
      light: "#ecfdf5",
      dark: "#047857",
      default: "#10b981",
    },
    danger: {
      light: "#fef2f2",
      dark: "#b91c1c",
      default: "#ef4444",
    },
    warning: {
      light: "#fffbeb",
      dark: "#b45309",
      default: "#f59e0b",
    },
  },
} as const;
