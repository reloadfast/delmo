/** Base URL for all API calls. Empty string = same origin (works in both dev proxy and prod). */
const BASE = "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  delete: (path: string) => request<void>(path, { method: "DELETE" }),
};

// ── Settings ─────────────────────────────────────────────────────────────────

export interface SettingsData {
  data: Record<string, string>;
}

export const settingsApi = {
  get: () => api.get<SettingsData>("/api/settings"),
  patch: (updates: Record<string, string>) => api.patch<SettingsData>("/api/settings", { updates }),
};

// ── Dashboard ─────────────────────────────────────────────────────────────────

export interface DashboardStats {
  connected: boolean;
  daemon_version: string | null;
  error: string | null;
  total_torrents: number | null;
  matching_torrents: number | null;
  moves_today: number;
  moves_all_time: number;
}

export const dashboardApi = {
  get: () => api.get<DashboardStats>("/api/dashboard"),
};

// ── Rules ─────────────────────────────────────────────────────────────────────

export interface RuleCondition {
  id: number;
  condition_type: "extension" | "tracker";
  value: string;
}

export interface Rule {
  id: number;
  name: string;
  priority: number;
  enabled: boolean;
  destination: string;
  conditions: RuleCondition[];
}

export interface ConditionInput {
  condition_type: "extension" | "tracker";
  value: string;
}

export interface RuleCreate {
  name: string;
  priority: number;
  enabled: boolean;
  destination: string;
  conditions: ConditionInput[];
}

export interface PreviewTorrent {
  hash: string;
  name: string;
  save_path: string;
}

export interface PreviewResult {
  total_torrents: number;
  matched: PreviewTorrent[];
}

export const rulesApi = {
  list: () => api.get<Rule[]>("/api/rules"),
  create: (body: RuleCreate) => api.post<Rule>("/api/rules", body),
  update: (id: number, body: Partial<RuleCreate>) => api.patch<Rule>(`/api/rules/${id}`, body),
  delete: (id: number) => api.delete(`/api/rules/${id}`),
  preview: (id: number) => api.get<PreviewResult>(`/api/rules/${id}/preview`),
  previewEval: (conditions: ConditionInput[]) =>
    api.post<PreviewResult>("/api/rules/preview", { conditions }),
};

// ── Logs ─────────────────────────────────────────────────────────────────────

export interface MoveLog {
  id: number;
  torrent_hash: string;
  torrent_name: string;
  rule_id: number | null;
  rule_name: string | null;
  source_path: string;
  destination_path: string;
  status: "success" | "skipped" | "error";
  error_message: string | null;
  created_at: string;
}

export const logsApi = {
  list: (limit = 100, offset = 0, status?: string) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (status) params.set("status", status);
    return api.get<MoveLog[]>(`/api/logs?${params}`);
  },
};
