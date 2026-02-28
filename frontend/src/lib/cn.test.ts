import { describe, expect, it } from "vitest";
import { cn } from "./cn";

describe("cn", () => {
  it("returns a single class unchanged", () => {
    expect(cn("foo")).toBe("foo");
  });

  it("merges multiple classes", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });

  it("resolves tailwind conflicts (last wins)", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
  });

  it("ignores falsy values", () => {
    expect(cn("foo", undefined, false, null, "bar")).toBe("foo bar");
  });

  it("supports object syntax", () => {
    expect(cn({ foo: true, bar: false })).toBe("foo");
  });

  it("returns empty string for no args", () => {
    expect(cn()).toBe("");
  });
});
