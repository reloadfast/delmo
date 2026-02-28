import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProgressBar } from "./ProgressBar";

describe("ProgressBar", () => {
  it("renders with correct aria attributes", () => {
    render(<ProgressBar value={60} />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "60");
    expect(bar).toHaveAttribute("aria-valuemin", "0");
    expect(bar).toHaveAttribute("aria-valuemax", "100");
  });

  it("clamps value below 0 to 0", () => {
    render(<ProgressBar value={-10} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0");
  });

  it("clamps value above 100 to 100", () => {
    render(<ProgressBar value={110} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
  });

  it("uses positive color at 100%", () => {
    render(<ProgressBar value={100} />);
    expect(screen.getByRole("progressbar").className).toContain("bg-accent-positive");
  });

  it("uses warning color at 50%", () => {
    render(<ProgressBar value={50} />);
    expect(screen.getByRole("progressbar").className).toContain("bg-accent-warning");
  });

  it("uses danger color below 50%", () => {
    render(<ProgressBar value={25} />);
    expect(screen.getByRole("progressbar").className).toContain("bg-accent-danger");
  });

  it("merges extra className on wrapper", () => {
    const { container } = render(<ProgressBar value={50} className="extra" />);
    expect(container.firstChild).toHaveClass("extra");
  });
});
