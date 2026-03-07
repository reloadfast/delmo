import React, { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

// ── Collapsible section ───────────────────────────────────────────────────────

function Section({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border border-border rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-4 bg-surface hover:bg-surface-hover transition-colors text-left"
      >
        <span className="font-semibold text-sm text-text-primary">{title}</span>
        {open ? (
          <ChevronDown size={16} className="text-text-secondary shrink-0" />
        ) : (
          <ChevronRight size={16} className="text-text-secondary shrink-0" />
        )}
      </button>
      {open && (
        <div className="px-5 py-4 bg-background border-t border-border space-y-3 text-sm text-text-primary leading-relaxed">
          {children}
        </div>
      )}
    </div>
  );
}

function Code({ children }: { children: React.ReactNode }) {
  return (
    <code className="px-1.5 py-0.5 rounded bg-surface border border-border font-mono text-xs text-text-primary">
      {children}
    </code>
  );
}

function Pre({ children }: { children: string }) {
  return (
    <pre className="p-4 rounded-lg bg-surface border border-border font-mono text-xs text-text-primary overflow-x-auto whitespace-pre">
      {children}
    </pre>
  );
}

function Kv({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex gap-3">
      <Code>{k}</Code>
      <span className="text-text-secondary">{v}</span>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export function DocsPage() {
  return (
    <div className="space-y-3 max-w-2xl">
      <Section title="How delmo works" defaultOpen>
        <p>
          delmo polls your Deluge daemon on a configurable interval, evaluates each torrent against
          your rules, and calls <Code>core.move_storage</Code> for any match. All configuration
          lives in a local SQLite database — no environment variables required.
        </p>
        <Pre>{`Browser
  │  :8000
  ▼
FastAPI + Uvicorn
  ├─ /api/*     REST handlers
  ├─ /api/ws/logs  WebSocket (live log feed)
  └─ /*         React SPA (built into image)
       │
       ├─ SQLite  /data/delmo.db
       └─ Deluge daemon  (TCP RPC)`}</Pre>
        <p>
          A single Docker image runs everything. The React SPA is built at image-build time and
          served as static files — no separate web server needed.
        </p>
      </Section>

      <Section title="Rule logic">
        <p>
          Rules are evaluated in priority order (lower number = higher priority). For each torrent:
        </p>
        <ul className="list-disc list-inside space-y-1 text-text-secondary">
          <li>The rule engine walks rules from lowest to highest priority.</li>
          <li>
            A rule matches if <em className="text-text-primary">all</em> of its conditions match
            (AND logic).
          </li>
          <li>Each torrent is matched against only the first matching rule (first-match wins).</li>
          <li>
            A torrent is skipped if its <Code>save_path</Code> already equals the rule destination
            (idempotency guard — prevents move loops).
          </li>
          <li>Moves are performed via Deluge RPC and do not interrupt seeding.</li>
        </ul>

        <p className="font-medium text-text-primary mt-2">Condition types</p>
        <div className="space-y-2">
          <Kv
            k="extension"
            v="Matches if any file in the torrent has the given extension, e.g. .mkv or mkv (dot optional)."
          />
          <Kv
            k="tracker"
            v="Matches if any tracker URL's domain contains the value as a case-insensitive substring, e.g. passthepopcorn."
          />
        </div>
      </Section>

      <Section title="Configuration reference">
        <p>All settings are persisted in SQLite and managed via the Settings page.</p>
        <div className="space-y-2">
          <Kv k="deluge_host" v="Hostname or IP of the Deluge daemon. Required." />
          <Kv k="deluge_port" v="RPC port (default: 58846)." />
          <Kv k="deluge_username" v="Daemon login username (leave blank for no-auth setups)." />
          <Kv k="deluge_password" v="Daemon login password." />
          <Kv
            k="polling_interval_seconds"
            v="How often the rule engine runs, in seconds (default: 300, minimum: 10)."
          />
        </div>
        <p className="mt-2">
          The only optional environment variable is <Code>DELMO_DATA_DIR</Code> (default:{" "}
          <Code>/data</Code>), which controls where the SQLite file is stored.
        </p>
      </Section>

      <Section title="Deluge RPC notes">
        <p>
          delmo communicates with Deluge over its native MessagePack RPC protocol (TCP, default port
          58846). The daemon must be running and reachable from the delmo container.
        </p>
        <ul className="list-disc list-inside space-y-1 text-text-secondary">
          <li>
            Use <strong className="text-text-primary">Test Connection</strong> in Settings to verify
            credentials before saving.
          </li>
          <li>
            The RPC timeout is 5 seconds — if your daemon is slow to respond, check network routing
            between containers.
          </li>
          <li>
            Moves use <Code>core.move_storage</Code>. Deluge handles the physical file move and
            updates its internal path; seeding continues uninterrupted.
          </li>
          <li>
            Deluge 2.x authentication: the username is typically <Code>localclient</Code> and the
            password can be found in <Code>~/.config/deluge/auth</Code>.
          </li>
        </ul>
      </Section>

      <Section title="Troubleshooting">
        <div className="space-y-4">
          <div>
            <p className="font-medium">Dashboard shows "Not connected"</p>
            <ul className="list-disc list-inside text-text-secondary space-y-0.5 mt-1">
              <li>Verify the host and port in Settings → Test Connection.</li>
              <li>Ensure the Deluge daemon is running and its RPC port is open.</li>
              <li>Check Docker network settings if delmo and Deluge are in separate containers.</li>
            </ul>
          </div>
          <div>
            <p className="font-medium">Rules match in Preview but moves don't happen</p>
            <ul className="list-disc list-inside text-text-secondary space-y-0.5 mt-1">
              <li>Confirm the rule is enabled (toggle in the Rules page).</li>
              <li>
                Check the Activity log for <Code>error</Code> entries — the error message will show
                the RPC failure reason.
              </li>
              <li>
                The torrent may already be at the destination path (idempotency guard skips it).
              </li>
            </ul>
          </div>
          <div>
            <p className="font-medium">Activity log shows no entries</p>
            <ul className="list-disc list-inside text-text-secondary space-y-0.5 mt-1">
              <li>
                No rules have matched yet — use Settings → Run Now to trigger an immediate cycle.
              </li>
              <li>No enabled rules exist — create a rule in the Rules page.</li>
            </ul>
          </div>
          <div>
            <p className="font-medium">Live feed dot is red</p>
            <p className="text-text-secondary mt-1">
              The WebSocket connection dropped. delmo automatically reconnects with exponential
              backoff — the dot will turn green within 30 seconds once the server is reachable.
            </p>
          </div>
        </div>
      </Section>
    </div>
  );
}
