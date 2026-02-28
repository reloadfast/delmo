import { ThemeToggle } from "../ThemeToggle";

interface HeaderProps {
  title: string;
}

export function Header({ title }: HeaderProps) {
  return (
    <header className="h-14 border-b border-border flex items-center justify-between px-6 shrink-0">
      <h1 className="text-base font-semibold text-text-primary">{title}</h1>
      <ThemeToggle />
    </header>
  );
}
