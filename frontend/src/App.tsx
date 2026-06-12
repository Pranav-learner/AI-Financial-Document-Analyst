import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import AppLayout from "@/layouts/AppLayout";
import Skeleton from "@/design-system/components/Skeleton";

// Lazy-loaded feature pages for route splitting
const DashboardPage = lazy(() => import("@/features/dashboard/DashboardPage"));
const FinancialPage = lazy(() => import("@/features/financial/FinancialPage"));
const RiskPage = lazy(() => import("@/features/risk/RiskPage"));
const ManagementPage = lazy(() => import("@/features/management/ManagementPage"));
const BenchmarkPage = lazy(() => import("@/features/benchmark/BenchmarkPage"));
const MemoPage = lazy(() => import("@/features/memo/MemoPage"));
const AgentPage = lazy(() => import("@/features/agent/AgentPage"));

const PageLoader = () => (
  <div className="space-y-6">
    <Skeleton className="h-8 w-1/3" variant="text" />
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <Skeleton variant="card" />
      <Skeleton variant="card" />
      <Skeleton variant="card" />
    </div>
    <Skeleton className="h-[350px]" variant="table" />
  </div>
);

/**
 * Main application router configuration linking all lazy-loaded dashboards.
 */
export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route
          path="/"
          element={
            <Suspense fallback={<PageLoader />}>
              <DashboardPage />
            </Suspense>
          }
        />
        <Route
          path="/financial"
          element={
            <Suspense fallback={<PageLoader />}>
              <FinancialPage />
            </Suspense>
          }
        />
        <Route
          path="/risks"
          element={
            <Suspense fallback={<PageLoader />}>
              <RiskPage />
            </Suspense>
          }
        />
        <Route
          path="/management"
          element={
            <Suspense fallback={<PageLoader />}>
              <ManagementPage />
            </Suspense>
          }
        />
        <Route
          path="/benchmark"
          element={
            <Suspense fallback={<PageLoader />}>
              <BenchmarkPage />
            </Suspense>
          }
        />
        <Route
          path="/memos"
          element={
            <Suspense fallback={<PageLoader />}>
              <MemoPage />
            </Suspense>
          }
        />
        <Route
          path="/agent"
          element={
            <Suspense fallback={<PageLoader />}>
              <AgentPage />
            </Suspense>
          }
        />
        {/* Fallback route */}
        <Route
          path="*"
          element={
            <Suspense fallback={<PageLoader />}>
              <DashboardPage />
            </Suspense>
          }
        />
      </Route>
    </Routes>
  );
}
