import * as React from "react";

import { cn } from "@/lib/utils";

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & {
  variant?: "default" | "secondary" | "outline" | "success" | "warning" | "destructive";
}) {
  const variants = {
    default: "bg-[var(--primary)] text-[var(--primary-foreground)]",
    secondary: "bg-[var(--secondary)] text-[var(--secondary-foreground)]",
    outline: "border border-[var(--border)]",
    success: "bg-green-500/15 text-green-600 dark:text-green-400",
    warning: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
    destructive: "bg-[var(--destructive)]/15 text-[var(--destructive)]",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("animate-pulse rounded-md bg-[var(--muted)]", className)} {...props} />;
}

export function Separator({ className }: { className?: string }) {
  return <div className={cn("h-px w-full bg-[var(--border)]", className)} />;
}

export function Spinner({ className }: { className?: string }) {
  return (
    <svg
      className={cn("animate-spin", className)}
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      aria-label="Loading"
    >
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.25" />
      <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function Avatar({ name, className }: { name?: string | null; className?: string }) {
  const initials = (name ?? "?")
    .split(" ")
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  return (
    <div
      className={cn(
        "flex h-8 w-8 items-center justify-center rounded-full bg-[var(--primary)] text-xs font-semibold text-[var(--primary-foreground)]",
        className,
      )}
    >
      {initials}
    </div>
  );
}
