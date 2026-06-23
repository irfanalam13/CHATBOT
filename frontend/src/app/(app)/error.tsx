"use client";

import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function RouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
      <AlertTriangle className="h-10 w-10 text-[var(--destructive)]" />
      <h2 className="text-lg font-semibold">Something went wrong</h2>
      <p className="max-w-md text-sm text-[var(--muted-foreground)]">{error.message}</p>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}
