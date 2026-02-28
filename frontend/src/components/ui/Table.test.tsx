import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Column, Table } from "./Table";

interface Row {
  id: string;
  name: string;
}

const columns: Column<Row>[] = [
  { key: "name", header: "Name", render: (r) => r.name },
];

const rows: Row[] = [
  { id: "1", name: "Alpha" },
  { id: "2", name: "Beta" },
];

describe("Table", () => {
  it("renders column headers", () => {
    render(<Table columns={columns} rows={rows} keyFn={(r) => r.id} />);
    expect(screen.getByText("Name")).toBeInTheDocument();
  });

  it("renders row data", () => {
    render(<Table columns={columns} rows={rows} keyFn={(r) => r.id} />);
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
  });

  it("shows default empty message when no rows", () => {
    render(<Table columns={columns} rows={[]} keyFn={(r) => r.id} />);
    expect(screen.getByText("No data.")).toBeInTheDocument();
  });

  it("shows custom empty message", () => {
    render(
      <Table
        columns={columns}
        rows={[]}
        keyFn={(r) => r.id}
        emptyMessage="Nothing here"
      />,
    );
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });

  it("renders all columns for each row", () => {
    const multiCol: Column<Row>[] = [
      { key: "id", header: "ID", render: (r) => r.id },
      { key: "name", header: "Name", render: (r) => r.name },
    ];
    render(<Table columns={multiCol} rows={rows} keyFn={(r) => r.id} />);
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("Alpha")).toBeInTheDocument();
  });
});
