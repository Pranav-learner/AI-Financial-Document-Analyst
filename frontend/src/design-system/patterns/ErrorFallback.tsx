import { AlertTriangle, RefreshCw } from "lucide-react";
import Button from "../components/Button";

interface ErrorFallbackProps {
  error?: Error | string | null;
  resetErrorBoundary?: () => void;
  title?: string;
  message?: string;
}

/**
 * High-fidelity, user-friendly Error Panel displaying helpful instructions and retry logic.
 */
export default function ErrorFallback({
  error,
  resetErrorBoundary,
  title = "Analysis Connection Error",
  message = "We encountered an issue communicating with the financial database or intelligence pipelines.",
}: ErrorFallbackProps) {
  return (
    <div
      className="glass-panel border-danger/20 p-6 flex flex-col items-center justify-center text-center max-w-lg mx-auto my-8 animate-fade-in"
      role="alert"
    >
      <div className="w-12 h-12 rounded-full bg-danger/10 flex items-center justify-center mb-4 text-danger-dark">
        <AlertTriangle className="w-6 h-6" aria-hidden="true" />
      </div>
      <h3 className="text-base font-bold text-surface-950 mb-1">{title}</h3>
      <p className="text-sm text-surface-600 mb-4">{message}</p>

      {error && (
        <div className="w-full text-left bg-surface-50 border border-surface-200 rounded p-3 mb-5 overflow-auto max-h-24">
          <p className="text-xs font-mono text-surface-700">
            {typeof error === "string" ? error : error.message}
          </p>
        </div>
      )}

      <div className="flex gap-3">
        {resetErrorBoundary && (
          <Button
            variant="outline"
            onClick={resetErrorBoundary}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Retry Connection
          </Button>
        )}
        <Button
          variant="secondary"
          onClick={() => window.location.reload()}
        >
          Refresh Workspace
        </Button>
      </div>
    </div>
  );
}
