import { useQuery } from "@tanstack/react-query";
import { type Column, Table } from "../components/ui/Table";
import { Badge } from "../components/ui/Badge";
import { Card, CardHeader, CardTitle } from "../components/ui/Card";
import { Skeleton } from "../components/ui/Skeleton";
import { dashboardApi, logsApi, type DashboardStats, type MoveLog } from "../lib/api";

// ── Sub-components ────────────────────────────────────────────────────────────

function ConnectionWidget({
  stats,
  loading,
}: {
  stats: DashboardStats | undefined;
  loading: boolean;
}) {
  if (loading) return <Skeleton className="h-14" />;

  const connected = stats?.connected ?? false;
  const label = connected
    ? `Connected · Deluge ${stats?.daemon_version ?? "unknown"}`
    : (stats?.error ?? "Not connected");

  return (
    <div className="flex items-center gap-3 px-5 py-3 rounded-xl border border-border bg-surface">
      <span
        className={`h-3 w-3 rounded-full shrink-0 ${
          connected ? "bg-accent-positive" : "bg-accent-danger"
        }`}
      />
      <span
        className={`text-sm font-medium ${connected ? "text-text-primary" : "text-accent-danger"}`}
      >
        {label}
      </span>
    </div>
  );
}

function StatCard({
  label,
  value,
  loading,
}: {
  label: string;
  value: number | string;
  loading: boolean;
}) {
  return (
    <Card>
      {loading ? (
        <>
          <Skeleton className="h-4 w-24 mb-3" />
          <Skeleton className="h-8 w-16" />
        </>
      ) : (
        <>
          <p className="text-xs font-medium text-text-secondary uppercase tracking-wide mb-1">
            {label}
          </p>
          <p className="text-3xl font-bold text-text-primary">{value}</p>
        </>
      )}
    </Card>
  );
}

const LOG_COLUMNS: Column<MoveLog>[] = [
  {
    key: "torrent_name",
    header: "Torrent",
    render: (r) => <span className="font-medium truncate max-w-xs block">{r.torrent_name}</span>,
  },
  {
    key: "rule_name",
    header: "Rule",
    render: (r) => <span className="text-text-secondary">{r.rule_name ?? "—"}</span>,
  },
  {
    key: "destination_path",
    header: "Destination",
    render: (r) => (
      <span className="font-mono text-xs text-text-secondary">{r.destination_path}</span>
    ),
  },
  {
    key: "status",
    header: "Status",
    render: (r) => (
      <Badge
        variant={r.status === "success" ? "positive" : r.status === "error" ? "danger" : "neutral"}
      >
        {r.status}
      </Badge>
    ),
  },
  {
    key: "created_at",
    header: "When",
    render: (r) => (
      <span className="text-text-secondary text-xs">{new Date(r.created_at).toLocaleString()}</span>
    ),
  },
];

// ── Page ─────────────────────────────────────────────────────────────────────

export function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: dashboardApi.get,
    refetchInterval: 30_000,
  });

  const { data: logs = [], isLoading: logsLoading } = useQuery({
    queryKey: ["logs", 10],
    queryFn: () => logsApi.list(10),
    refetchInterval: 30_000,
  });

  const na = "—";

  return (
    <div className="space-y-6">
      <ConnectionWidget stats={stats} loading={statsLoading} />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Torrents"
          value={stats?.total_torrents ?? na}
          loading={statsLoading}
        />
        <StatCard
          label="Matching Rules"
          value={stats?.matching_torrents ?? na}
          loading={statsLoading}
        />
        <StatCard label="Moves Today" value={stats?.moves_today ?? 0} loading={statsLoading} />
        <StatCard
          label="Moves All Time"
          value={stats?.moves_all_time ?? 0}
          loading={statsLoading}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Moves</CardTitle>
        </CardHeader>
        {logsLoading ? (
          <Skeleton className="h-32" />
        ) : (
          <Table
            columns={LOG_COLUMNS}
            rows={logs}
            keyFn={(r) => String(r.id)}
            emptyMessage="No moves recorded yet."
          />
        )}
      </Card>
    </div>
  );
}
