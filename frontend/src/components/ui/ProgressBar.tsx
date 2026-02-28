import { cn } from "../../lib/cn";

interface ProgressBarProps {
  /** 0–100 */
  value: number;
  className?: string;
}

export function ProgressBar({ value, className }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, value));
  const colorClass =
    clamped === 100
      ? "bg-accent-positive"
      : clamped >= 50
        ? "bg-accent-warning"
        : "bg-accent-danger";

  return (
    <div className={cn("h-1.5 w-full rounded-full bg-border overflow-hidden", className)}>
      <div
        className={cn("h-full rounded-full transition-[width] duration-300", colorClass)}
        style={{ width: `${clamped}%` }}
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
      />
    </div>
  );
}
