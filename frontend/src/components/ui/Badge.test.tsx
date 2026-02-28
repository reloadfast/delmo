import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Badge } from "./Badge";

describe("Badge", () => {
  it("renders children", () => {
    render(<Badge>active</Badge>);
    expect(screen.getByText("active")).toBeInTheDocument();
  });

  it("defaults to neutral variant", () => {
    render(<Badge>n/a</Badge>);
    const el = screen.getByText("n/a");
    expect(el.className).toContain("border-border");
  });

  it("applies positive variant classes", () => {
    render(<Badge variant="positive">ok</Badge>);
    expect(screen.getByText("ok").className).toContain("text-accent-positive");
  });

  it("applies warning variant classes", () => {
    render(<Badge variant="warning">warn</Badge>);
    expect(screen.getByText("warn").className).toContain("text-accent-warning");
  });

  it("applies danger variant classes", () => {
    render(<Badge variant="danger">err</Badge>);
    expect(screen.getByText("err").className).toContain("text-accent-danger");
  });

  it("merges extra className", () => {
    render(<Badge className="extra-class">x</Badge>);
    expect(screen.getByText("x").className).toContain("extra-class");
  });
});
