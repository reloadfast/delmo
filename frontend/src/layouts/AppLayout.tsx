import { Outlet, useRouterState } from "@tanstack/react-router";
import { Footer } from "../components/layout/Footer";
import { Header } from "../components/layout/Header";
import { Sidebar } from "../components/layout/Sidebar";

const ROUTE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/rules": "Rules",
  "/activity": "Activity",
  "/settings": "Settings",
  "/docs": "Docs",
};

export function AppLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const title = ROUTE_TITLES[pathname] ?? "delmo";

  return (
    <div className="flex h-dvh overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
        <Header title={title} />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
        <Footer />
      </div>
    </div>
  );
}
