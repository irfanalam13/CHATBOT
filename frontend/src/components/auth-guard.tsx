"use client";

import * as React from "react";
import { usePathname, useRouter } from "next/navigation";

import { Spinner } from "@/components/ui/misc";
import { useAuthStore } from "@/stores/auth-store";

/** Client-side protected-route guard. Bootstraps the session, redirects to
 *  /login when unauthenticated. Server cannot read localStorage tokens, so the
 *  guard runs here. */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const status = useAuthStore((s) => s.status);
  const bootstrap = useAuthStore((s) => s.bootstrap);

  React.useEffect(() => {
    if (status === "idle") bootstrap();
  }, [status, bootstrap]);

  React.useEffect(() => {
    if (status === "unauthenticated") {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [status, router, pathname]);

  if (status === "authenticated") return <>{children}</>;

  return (
    <div className="flex h-screen items-center justify-center">
      <Spinner className="h-6 w-6 text-[var(--muted-foreground)]" />
    </div>
  );
}
