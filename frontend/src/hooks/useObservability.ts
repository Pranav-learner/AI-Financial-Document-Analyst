import { useEffect, useState } from "react";

interface MetricsLog {
  timestamp: string;
  category: "performance" | "error" | "interaction";
  name: string;
  value: string | number;
}

// In-memory array to store telemetry logs
const telemetryLogs: MetricsLog[] = [];
const listeners = new Set<(logs: MetricsLog[]) => void>();

function logTelemetry(log: MetricsLog) {
  telemetryLogs.push(log);
  // Keep logs at max 50
  if (telemetryLogs.length > 50) {
    telemetryLogs.shift();
  }
  listeners.forEach((listener) => listener([...telemetryLogs]));
}

/**
 * Custom telemetry hook to track frontend interaction performance and log errors.
 */
export function useObservability() {
  const [logs, setLogs] = useState<MetricsLog[]>([]);

  useEffect(() => {
    setLogs([...telemetryLogs]);
    const updateLogs = (newLogs: MetricsLog[]) => setLogs(newLogs);
    listeners.add(updateLogs);
    return () => {
      listeners.delete(updateLogs);
    };
  }, []);

  const trackPerformance = (name: string, renderTimeMs: number) => {
    logTelemetry({
      timestamp: new Date().toLocaleTimeString(),
      category: "performance",
      name,
      value: `${renderTimeMs.toFixed(1)}ms`,
    });
  };

  const trackInteraction = (name: string, actionDetails: string | number) => {
    logTelemetry({
      timestamp: new Date().toLocaleTimeString(),
      category: "interaction",
      name,
      value: actionDetails,
    });
  };

  const trackError = (name: string, errorMessage: string) => {
    logTelemetry({
      timestamp: new Date().toLocaleTimeString(),
      category: "error",
      name,
      value: errorMessage,
    });
  };

  return {
    logs,
    trackPerformance,
    trackInteraction,
    trackError,
  };
}

/**
 * Tracks component render latency on mount.
 */
export function usePerformanceTimer(componentName: string) {
  useEffect(() => {
    const start = performance.now();
    return () => {
      const duration = performance.now() - start;
      // Capture transition/rendering duration
      logTelemetry({
        timestamp: new Date().toLocaleTimeString(),
        category: "performance",
        name: componentName,
        value: `${duration.toFixed(1)}ms`,
      });
    };
  }, [componentName]);
}
