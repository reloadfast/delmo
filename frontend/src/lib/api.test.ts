import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, settingsApi } from "./api";

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
