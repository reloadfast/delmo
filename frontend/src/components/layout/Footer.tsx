import { version } from "../../../package.json";

export function Footer() {
  return (
    <footer className="h-9 border-t border-border flex items-center justify-end px-6 shrink-0">
      <span className="text-xs text-text-secondary">v{version}</span>
    </footer>
  );
}
