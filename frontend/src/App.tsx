import { Routes, Route } from "react-router-dom";
import AppLayout from "@/layouts/AppLayout";
import DashboardPage from "@/features/dashboard/DashboardPage";
import FinancialPage from "@/features/financial/FinancialPage";
import RiskPage from "@/features/risk/RiskPage";
import ManagementPage from "@/features/management/ManagementPage";
import BenchmarkPage from "@/features/benchmark/BenchmarkPage";
import MemoPage from "@/features/memo/MemoPage";
import AgentPage from "@/features/agent/AgentPage";

/**
 * Main application router configuration linking all Phase 10A dashboards.
 */
export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/financial" element={<FinancialPage />} />
        <Route path="/risks" element={<RiskPage />} />
        <Route path="/management" element={<ManagementPage />} />
        <Route path="/benchmark" element={<BenchmarkPage />} />
        <Route path="/memos" element={<MemoPage />} />
        <Route path="/agent" element={<AgentPage />} />
        {/* Fallback route */}
        <Route path="*" element={<DashboardPage />} />
      </Route>
    </Routes>
  );
}
