import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Toggle } from "./Toggle";

describe("Toggle", () => {
  it("renders label when provided", () => {
    render(<Toggle checked={false} onCheckedChange={vi.fn()} label="Enable" />);
    expect(screen.getByText("Enable")).toBeInTheDocument();
  });

  it("renders without label", () => {
    render(<Toggle checked={false} onCheckedChange={vi.fn()} />);
    expect(screen.queryByRole("heading")).toBeNull();
  });

  it("calls onCheckedChange when clicked", async () => {
    const handler = vi.fn();
    render(<Toggle checked={false} onCheckedChange={handler} />);
    await userEvent.click(screen.getByRole("switch"));
    expect(handler).toHaveBeenCalledWith(true);
  });

  it("reflects checked state", () => {
    render(<Toggle checked={true} onCheckedChange={vi.fn()} />);
    expect(screen.getByRole("switch")).toHaveAttribute("data-state", "checked");
  });

  it("reflects unchecked state", () => {
    render(<Toggle checked={false} onCheckedChange={vi.fn()} />);
    expect(screen.getByRole("switch")).toHaveAttribute("data-state", "unchecked");
  });

  it("is disabled when disabled prop is set", () => {
    render(<Toggle checked={false} onCheckedChange={vi.fn()} disabled />);
    expect(screen.getByRole("switch")).toBeDisabled();
  });
});
