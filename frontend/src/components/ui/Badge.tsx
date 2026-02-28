import React from "react";
import { cn } from "../../lib/cn";

export type BadgeVariant = "positive" | "warning" | "danger" | "neutral";

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  positive: "bg-accent-positive/15 text-accent-positive",
  warning: "bg-accent-warning/15 text-accent-warning",
  danger: "bg-accent-danger/15 text-accent-danger",
  neutral: "border border-border text-text-secondary",
};

export function Badge({
  children,
  variant = "neutral",
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        variantClasses[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
