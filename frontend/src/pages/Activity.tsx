import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { type Column, Table } from "../components/ui/Table";
import { Badge, type BadgeVariant } from "../components/ui/Badge";
import { Skeleton } from "../components/ui/Skeleton";
import { cn } from "../lib/cn";
import { logsApi, type MoveLog } from "../lib/api";

// ── Constants ─────────────────────────────────────────────────────────────────

const PAGE_SIZE = 50;

type StatusFilter = "all" | "success" | "error" | "skipped" | "dry_run";

const STATUS_FILTERS: { label: string; value: StatusFilter }[] = [
  { label: "All", value: "all" },
  { label: "Success", value: "success" },
  { label: "Error", value: "error" },
  { label: "Skipped", value: "skipped" },
  { label: "Dry Run", value: "dry_run" },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function copyText(text: string): void {
  if (navigator.clipboard?.writeText) {
    void navigator.clipboard.writeText(text);
  } else {
    // Fallback for HTTP (non-secure) LAN contexts where Clipboard API is unavailable
    const el = document.createElement("textarea");
    el.value = text;
    el.style.cssText = "position:fixed;opacity:0;pointer-events:none";
    document.body.appendChild(el);
    el.select();
    document.execCommand("copy");
    document.body.removeChild(el);
  }
}

function statusVariant(status: string): BadgeVariant {
  if (status === "success") return "positive";
  if (status === "error") return "danger";
  if (status === "dry_run") return "warning";
  return "neutral";
}

// ── Table columns ─────────────────────────────────────────────────────────────

const COLUMNS: Column<MoveLog>[] = [
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
      <div
        className={r.error_message ? "cursor-pointer select-none" : undefined}
        title={r.error_message ? "Click to copy full error" : undefined}
        onClick={r.error_message ? () => copyText(r.error_message!) : undefined}
      >
        <Badge variant={statusVariant(r.status)}>{r.status}</Badge>
        {r.error_message && (
          <p className="text-xs text-accent-danger mt-1 max-w-xs line-clamp-4 whitespace-pre-wrap">
            {r.error_message}
          </p>
        )}
      </div>
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

// ── Live feed hook ────────────────────────────────────────────────────────────

function useLogFeed(): { entries: MoveLog[]; connected: boolean } {
  const [entries, setEntries] = useState<MoveLog[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);

  useEffect(() => {
    let unmounted = false;

    function connect() {
      if (unmounted) return;
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      const ws = new WebSocket(`${proto}//${window.location.host}/api/ws/logs`);
      wsRef.current = ws;

      ws.onopen = () => {
        retryRef.current = 0;
        setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const entry = JSON.parse(event.data as string) as MoveLog;
          setEntries((prev) => [entry, ...prev].slice(0, 200));
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (!unmounted) {
          const delay = Math.min(1000 * 2 ** retryRef.current, 30_000);
          retryRef.current += 1;
          setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      unmounted = true;
      wsRef.current?.close();
    };
  }, []);

  return { entries, connected };
}

// ── Page ─────────────────────────────────────────────────────────────────────

export function ActivityPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [page, setPage] = useState(0);
  const { entries: liveEntries, connected } = useLogFeed();

  const offset = page * PAGE_SIZE;
  const apiStatus = statusFilter === "all" ? undefined : statusFilter;

  const { data: logs = [], isLoading } = useQuery({
    queryKey: ["logs", PAGE_SIZE, offset, statusFilter],
    queryFn: () => logsApi.list(PAGE_SIZE, offset, apiStatus),
  });

  const isLastPage = logs.length < PAGE_SIZE;

  // On page 0: prepend live entries not already shown in the paginated list
  const pageIds = new Set(logs.map((l) => l.id));
  const newLive = liveEntries.filter((e) => !pageIds.has(e.id));
  const displayRows = page === 0 ? [...newLive, ...logs] : logs;

  function handleFilterChange(value: StatusFilter) {
    setStatusFilter(value);
    setPage(0);
  }

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3 justify-between">
        {/* Status filter pills */}
        <div className="flex items-center gap-1">
          {STATUS_FILTERS.map(({ label, value }) => (
            <button
              key={value}
              onClick={() => handleFilterChange(value)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                statusFilter === value
                  ? "bg-accent text-white"
                  : "text-text-secondary hover:text-text-primary hover:bg-surface-hover"
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Live indicator */}
        <div className="flex items-center gap-1.5 text-xs text-text-secondary select-none">
          <span
            className={cn(
              "h-2 w-2 rounded-full shrink-0",
              connected ? "bg-accent-positive" : "bg-accent-danger"
            )}
          />
          {connected ? "Live" : "Reconnecting…"}
          {newLive.length > 0 && (
            <span className="ml-1 text-accent-positive font-medium">+{newLive.length} new</span>
          )}
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <Skeleton className="h-64" />
      ) : (
        <Table
          columns={COLUMNS}
          rows={displayRows}
          keyFn={(r) => String(r.id)}
          emptyMessage="No log entries yet."
        />
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <button
          disabled={page === 0}
          onClick={() => setPage((p) => p - 1)}
          className="px-3 py-1.5 rounded-lg text-sm text-text-secondary hover:text-text-primary hover:bg-surface-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          ← Prev
        </button>
        <span className="text-xs text-text-secondary">Page {page + 1}</span>
        <button
          disabled={isLastPage}
          onClick={() => setPage((p) => p + 1)}
          className="px-3 py-1.5 rounded-lg text-sm text-text-secondary hover:text-text-primary hover:bg-surface-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Next →
        </button>
      </div>
    </div>
  );
}
