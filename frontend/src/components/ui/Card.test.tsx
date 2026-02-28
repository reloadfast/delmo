import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Card, CardHeader, CardTitle } from "./Card";

describe("Card", () => {
  it("renders children", () => {
    render(<Card>content</Card>);
    expect(screen.getByText("content")).toBeInTheDocument();
  });

  it("merges extra className", () => {
    const { container } = render(<Card className="extra">x</Card>);
    expect(container.firstChild).toHaveClass("extra");
  });
});

describe("CardHeader", () => {
  it("renders children", () => {
    render(<CardHeader>header</CardHeader>);
    expect(screen.getByText("header")).toBeInTheDocument();
  });

  it("merges extra className", () => {
    const { container } = render(<CardHeader className="my-class">h</CardHeader>);
    expect(container.firstChild).toHaveClass("my-class");
  });
});

describe("CardTitle", () => {
  it("renders title text in h3", () => {
    render(<CardTitle>My Title</CardTitle>);
    const el = screen.getByText("My Title");
    expect(el.tagName).toBe("H3");
  });
});
