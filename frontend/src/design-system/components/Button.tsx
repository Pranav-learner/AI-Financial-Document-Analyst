import { clsx } from "clsx";
import { Loader2 } from "lucide-react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  icon?: React.ReactNode;
}

/**
 * Custom design system button incorporating focus ring states, spacing, and loading indicators.
 */
export default function Button({
  children,
  className,
  variant = "primary",
  size = "md",
  loading = false,
  disabled = false,
  icon,
  type = "button",
  ...props
}: ButtonProps) {
  const baseStyles =
    "inline-flex items-center justify-center font-medium rounded-lg transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none select-none";

  const variants = {
    primary: "bg-brand-600 hover:bg-brand-700 text-white shadow-sm",
    secondary: "bg-surface-100 hover:bg-surface-200 text-surface-800",
    outline: "border border-surface-200 hover:bg-surface-50 text-surface-600",
    danger: "bg-danger hover:bg-danger/90 text-white shadow-sm",
    ghost: "hover:bg-surface-50 text-surface-600 focus:ring-offset-0",
  };

  const sizes = {
    sm: "px-3 py-1.5 text-xs gap-1.5",
    md: "px-4 py-2 text-sm gap-2",
    lg: "px-5 py-2.5 text-base gap-2",
  };

  return (
    <button
      type={type}
      className={clsx(baseStyles, variants[variant], sizes[size], className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin shrink-0" aria-hidden="true" />
      ) : (
        icon && <span className="shrink-0" aria-hidden="true">{icon}</span>
      )}
      {children}
    </button>
  );
}
