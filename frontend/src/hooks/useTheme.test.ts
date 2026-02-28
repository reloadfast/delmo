import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useTheme } from "./useTheme";

describe("useTheme", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("defaults to dark when no preference set and system is dark", () => {
    // matchMedia("(prefers-color-scheme: light)").matches === false → dark
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("dark");
  });

  it("defaults to light when system prefers light", () => {
    vi.spyOn(window, "matchMedia").mockReturnValue({
      matches: true,
      media: "",
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    } as unknown as MediaQueryList);
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("light");
  });

  it("reads theme from localStorage", () => {
    localStorage.setItem("delmo-theme", "light");
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("light");
  });

  it("updates theme and persists to localStorage", () => {
    const { result } = renderHook(() => useTheme());
    act(() => {
      result.current.setTheme("light");
    });
    expect(result.current.theme).toBe("light");
    expect(localStorage.getItem("delmo-theme")).toBe("light");
  });

  it("sets data-theme on documentElement", () => {
    const { result } = renderHook(() => useTheme());
    act(() => {
      result.current.setTheme("dark");
    });
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("applies initial theme to documentElement on mount", () => {
    localStorage.setItem("delmo-theme", "light");
    renderHook(() => useTheme());
    expect(document.documentElement.dataset.theme).toBe("light");
  });
});
