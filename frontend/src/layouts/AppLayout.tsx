import { Outlet } from "react-router-dom";
import Sidebar from "@/components/Sidebar";

/** Main application layout with sidebar navigation and content area. */
export default function AppLayout() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
