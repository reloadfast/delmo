import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, dashboardApi, logsApi, rulesApi, settingsApi } from "./api";

// Stub global fetch
const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.restoreAllMocks();
});

function mockOk(body: unknown) {
  fetchMock.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(body),
  });
}

function mockErr(status: number, text: string) {
  fetchMock.mockResolvedValueOnce({
    ok: false,
    status,
    statusText: text,
    text: () => Promise.resolve(text),
  });
}

describe("api.get", () => {
  it("fetches and returns parsed JSON", async () => {
    mockOk({ hello: "world" });
    const result = await api.get<{ hello: string }>("/api/test");
    expect(result).toEqual({ hello: "world" });
    expect(fetchMock).toHaveBeenCalledWith("/api/test", expect.objectContaining({}));
  });

  it("throws on non-ok response", async () => {
    mockErr(503, "Service Unavailable");
    await expect(api.get("/api/test")).rejects.toThrow("503");
  });
});

describe("api.patch", () => {
  it("sends PATCH with JSON body", async () => {
    mockOk({});
    await api.patch("/api/settings", { updates: { key: "val" } });
    const call = fetchMock.mock.calls[0];
    expect(call[1].method).toBe("PATCH");
    expect(JSON.parse(call[1].body)).toEqual({ updates: { key: "val" } });
  });
});

describe("api.post", () => {
  it("sends POST with body", async () => {
    mockOk({});
    await api.post("/api/test", { foo: "bar" });
    const call = fetchMock.mock.calls[0];
    expect(call[1].method).toBe("POST");
  });

  it("sends POST without body", async () => {
    mockOk({});
    await api.post("/api/test");
    const call = fetchMock.mock.calls[0];
    expect(call[1].body).toBeUndefined();
  });
});

describe("api.delete", () => {
  it("sends DELETE", async () => {
    mockOk({});
    await api.delete("/api/rules/1");
    expect(fetchMock.mock.calls[0][1].method).toBe("DELETE");
  });
});

describe("settingsApi", () => {
  it("get calls /api/settings", async () => {
    mockOk({ data: {} });
    await settingsApi.get();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/settings");
  });

  it("patch calls /api/settings with PATCH", async () => {
    mockOk({ data: {} });
    await settingsApi.patch({ key: "value" });
    expect(fetchMock.mock.calls[0][1].method).toBe("PATCH");
  });
});

describe("dashboardApi", () => {
  it("get calls /api/dashboard", async () => {
    mockOk({ connected: false, moves_today: 0, moves_all_time: 0 });
    await dashboardApi.get();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/dashboard");
  });
});

describe("rulesApi", () => {
  it("list calls GET /api/rules", async () => {
    mockOk([]);
    await rulesApi.list();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/rules");
  });

  it("create calls POST /api/rules", async () => {
    mockOk({ id: 1 });
    await rulesApi.create({
      name: "R",
      priority: 100,
      enabled: true,
      destination: "/d",
      conditions: [],
    });
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/rules");
  });

  it("update calls PATCH /api/rules/:id", async () => {
    mockOk({ id: 1 });
    await rulesApi.update(1, { enabled: false });
    expect(fetchMock.mock.calls[0][1].method).toBe("PATCH");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/rules/1");
  });

  it("delete calls DELETE /api/rules/:id", async () => {
    mockOk({});
    await rulesApi.delete(2);
    expect(fetchMock.mock.calls[0][1].method).toBe("DELETE");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/rules/2");
  });

  it("preview calls GET /api/rules/:id/preview", async () => {
    mockOk({ total_torrents: 0, matched: [] });
    await rulesApi.preview(3);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/rules/3/preview");
  });

  it("previewEval calls POST /api/rules/preview", async () => {
    mockOk({ total_torrents: 0, matched: [] });
    await rulesApi.previewEval([{ condition_type: "extension", value: "mkv" }]);
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/rules/preview");
  });
});

describe("logsApi", () => {
  it("list calls GET /api/logs with limit", async () => {
    mockOk([]);
    await logsApi.list(10);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/logs?limit=10");
  });

  it("list uses default limit 100", async () => {
    mockOk([]);
    await logsApi.list();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/logs?limit=100");
  });
});
