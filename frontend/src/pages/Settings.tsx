import React, { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff, Play } from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { Card, CardHeader, CardTitle } from "../components/ui/Card";
import { Skeleton } from "../components/ui/Skeleton";
import { cn } from "../lib/cn";
import { connectionApi, schedulerApi, settingsApi, type ConnectionStatus } from "../lib/api";

// ── Shared field component ────────────────────────────────────────────────────

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-text-secondary uppercase tracking-wide">
        {label}
      </label>
      {children}
    </div>
  );
}

function Input({
  value,
  onChange,
  type = "text",
  placeholder,
  className,
}: {
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
  className?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={cn(
        "w-full px-3 py-2 rounded-lg border border-border bg-background text-text-primary text-sm",
        "focus:outline-none focus:ring-2 focus:ring-accent/40 focus:border-accent",
        "placeholder:text-text-secondary/50",
        className
      )}
    />
  );
}

// ── Deluge connection section ─────────────────────────────────────────────────

interface ConnForm {
  host: string;
  port: string;
  username: string;
  password: string;
}

function ConnectionCard({ settings }: { settings: Record<string, string> }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<ConnForm>({
    host: "",
    port: "58846",
    username: "",
    password: "",
  });
  const [showPw, setShowPw] = useState(false);
  const [testStatus, setTestStatus] = useState<ConnectionStatus | null>(null);
  const [testing, setTesting] = useState(false);
  const [saved, setSaved] = useState(false);

  // Populate form from loaded settings
  useEffect(() => {
    setForm({
      host: settings.deluge_host ?? "",
      port: settings.deluge_port ?? "58846",
      username: settings.deluge_username ?? "",
      password: settings.deluge_password ?? "",
    });
  }, [settings]);

  function set(key: keyof ConnForm) {
    return (v: string) => {
      setForm((f) => ({ ...f, [key]: v }));
      setTestStatus(null);
      setSaved(false);
    };
  }

  async function handleTest() {
    setTesting(true);
    setTestStatus(null);
    try {
      const result = await connectionApi.test({
        host: form.host,
        port: Number(form.port) || 58846,
        username: form.username,
        password: form.password,
      });
      setTestStatus(result);
    } catch {
      setTestStatus({ connected: false, daemon_version: null, error: "Request failed." });
    } finally {
      setTesting(false);
    }
  }

  const saveMutation = useMutation({
    mutationFn: () =>
      settingsApi.patch({
        deluge_host: form.host,
        deluge_port: form.port,
        deluge_username: form.username,
        deluge_password: form.password,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settings"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      setSaved(true);
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Deluge Connection</CardTitle>
      </CardHeader>
      <div className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="sm:col-span-2">
            <Field label="Host">
              <Input value={form.host} onChange={set("host")} placeholder="127.0.0.1" />
            </Field>
          </div>
          <Field label="Port">
            <Input value={form.port} onChange={set("port")} placeholder="58846" />
          </Field>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Username">
            <Input value={form.username} onChange={set("username")} placeholder="localclient" />
          </Field>
          <Field label="Password">
            <div className="relative">
              <Input
                value={form.password}
                onChange={set("password")}
                type={showPw ? "text" : "password"}
                placeholder="••••••••"
                className="pr-10"
              />
              <button
                onClick={() => setShowPw((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary transition-colors"
                aria-label={showPw ? "Hide password" : "Show password"}
              >
                {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </Field>
        </div>

        {/* Test + result row */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleTest}
            disabled={testing || !form.host}
            className="px-4 py-2 rounded-lg text-sm font-medium border border-border text-text-primary hover:bg-surface-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {testing ? "Testing…" : "Test Connection"}
          </button>
          {testStatus && (
            <span className="flex items-center gap-2 text-sm">
              <Badge variant={testStatus.connected ? "positive" : "danger"}>
                {testStatus.connected ? "Connected" : "Failed"}
              </Badge>
              <span className="text-text-secondary">
                {testStatus.connected
                  ? `Deluge ${testStatus.daemon_version ?? "unknown"}`
                  : (testStatus.error ?? "Unknown error")}
              </span>
            </span>
          )}
        </div>

        {/* Save row */}
        <div className="flex items-center gap-3 pt-1">
          <button
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
          >
            {saveMutation.isPending ? "Saving…" : "Save Credentials"}
          </button>
          {saved && !saveMutation.isPending && (
            <span className="text-xs text-accent-positive">Saved.</span>
          )}
          {saveMutation.isError && <span className="text-xs text-accent-danger">Save failed.</span>}
        </div>
      </div>
    </Card>
  );
}

// ── Scheduler section ─────────────────────────────────────────────────────────

function SchedulerCard({ settings }: { settings: Record<string, string> }) {
  const qc = useQueryClient();
  const [interval, setInterval] = useState("300");
  const [intervalSaved, setIntervalSaved] = useState(false);
  const [runFeedback, setRunFeedback] = useState("");

  useEffect(() => {
    setInterval(settings.polling_interval_seconds ?? "300");
  }, [settings]);

  const saveIntervalMutation = useMutation({
    mutationFn: () => settingsApi.patch({ polling_interval_seconds: interval }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settings"] });
      setIntervalSaved(true);
    },
  });

  const runNowMutation = useMutation({
    mutationFn: schedulerApi.runNow,
    onSuccess: () => {
      setRunFeedback("Poll cycle triggered.");
      setTimeout(() => setRunFeedback(""), 3000);
    },
    onError: () => {
      setRunFeedback("Failed to trigger.");
      setTimeout(() => setRunFeedback(""), 3000);
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Scheduler</CardTitle>
      </CardHeader>
      <div className="space-y-4">
        <Field label="Polling Interval (seconds)">
          <div className="flex items-center gap-3">
            <Input
              value={interval}
              onChange={(v) => {
                setInterval(v);
                setIntervalSaved(false);
              }}
              placeholder="300"
              className="max-w-32"
            />
            <button
              onClick={() => saveIntervalMutation.mutate()}
              disabled={saveIntervalMutation.isPending}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
            >
              {saveIntervalMutation.isPending ? "Saving…" : "Save"}
            </button>
            {intervalSaved && !saveIntervalMutation.isPending && (
              <span className="text-xs text-accent-positive">Saved.</span>
            )}
          </div>
          <p className="text-xs text-text-secondary">Minimum: 10 seconds.</p>
        </Field>

        <div className="flex items-center gap-3 pt-1">
          <button
            onClick={() => runNowMutation.mutate()}
            disabled={runNowMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-border text-text-primary hover:bg-surface-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Play size={14} />
            {runNowMutation.isPending ? "Triggering…" : "Run Now"}
          </button>
          {runFeedback && <span className="text-xs text-text-secondary">{runFeedback}</span>}
        </div>
      </div>
    </Card>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export function SettingsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: settingsApi.get,
  });

  const settings = data?.data ?? {};

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-64" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <ConnectionCard settings={settings} />
      <SchedulerCard settings={settings} />
    </div>
  );
}
