import { useQuery } from "@tanstack/react-query";
import { settingsApi } from "./lib/api";
import { version } from "../package.json";

/**
 * Temporary scaffold — replaced by full routed layout in Phase 4.
 * Verifies the API connection is working end-to-end.
 */
export default function App() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["settings"],
    queryFn: settingsApi.get,
  });

  return (
    <div
      style={{
        minHeight: "100dvh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "1rem",
        padding: "2rem",
        fontFamily: "ui-sans-serif, system-ui, sans-serif",
      }}
    >
      <h1 style={{ fontSize: "2rem", fontWeight: 700, letterSpacing: "-0.02em" }}>delmo</h1>
      <p style={{ color: "var(--color-text-secondary)", fontSize: "0.875rem" }}>
        Automatic torrent data mover · Phase 1 scaffold
      </p>

      <div
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "0.75rem",
          padding: "1.25rem 1.75rem",
          minWidth: "280px",
          textAlign: "center",
        }}
      >
        {isLoading && <span>Connecting to API…</span>}
        {isError && (
          <span style={{ color: "var(--color-accent-danger)" }}>
            API unavailable — start the backend
          </span>
        )}
        {data && (
          <span style={{ color: "var(--color-accent-positive)" }}>
            API connected · {Object.keys(data.data).length} settings loaded
          </span>
        )}
      </div>

      <footer
        style={{
          position: "fixed",
          bottom: "1rem",
          color: "var(--color-text-secondary)",
          fontSize: "0.75rem",
        }}
      >
        v{version}
      </footer>
    </div>
  );
}
