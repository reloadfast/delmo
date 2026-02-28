import { Link, useRouterState } from "@tanstack/react-router";
import { Activity, BookOpen, LayoutDashboard, ListChecks, Settings } from "lucide-react";
import { cn } from "../../lib/cn";

const NAV_ITEMS = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/rules", icon: ListChecks, label: "Rules" },
  { to: "/activity", icon: Activity, label: "Activity" },
  { to: "/settings", icon: Settings, label: "Settings" },
  { to: "/docs", icon: BookOpen, label: "Docs" },
] as const;

type To = (typeof NAV_ITEMS)[number]["to"];

function NavLink({
  to,
  icon: Icon,
  label,
}: {
  to: To;
  icon: (typeof NAV_ITEMS)[number]["icon"];
  label: string;
}) {
  const pathname = useRouterState({
    select: (s) => s.location.pathname,
  });
  const isActive = to === "/" ? pathname === "/" : pathname.startsWith(to);

  return (
    <Link
      to={to}
      className={cn(
        "flex items-center gap-3 px-4 py-2 mx-2 rounded-lg text-sm transition-colors",
        isActive
          ? "bg-surface-hover text-text-primary"
          : "text-text-secondary hover:text-text-primary hover:bg-surface-hover"
      )}
    >
      <Icon size={16} className="shrink-0" />
      {label}
    </Link>
  );
}

export function Sidebar() {
  return (
    <aside className="w-56 shrink-0 border-r border-border bg-surface h-full flex flex-col">
      <div className="flex items-center px-5 py-4 border-b border-border">
        <span className="text-lg font-bold tracking-tight text-text-primary">delmo</span>
      </div>
      <nav className="flex-1 overflow-y-auto py-3 flex flex-col gap-0.5">
        {NAV_ITEMS.map((item) => (
          <NavLink key={item.to} {...item} />
        ))}
      </nav>
    </aside>
  );
}
