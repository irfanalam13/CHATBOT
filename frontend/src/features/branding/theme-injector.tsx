"use client";

import * as React from "react";

import { useAuthStore } from "@/stores/auth-store";

/**
 * White-label branding: applies a tenant's custom primary color (and any other
 * brand tokens) at runtime by overriding CSS variables on :root. The tenant's
 * branding is read from tenant.metadata (set via Settings → Branding).
 */
export function ThemeInjector() {
  const tenant = useAuthStore((s) => s.tenant);

  React.useEffect(() => {
    const branding =
      (tenant as unknown as { metadata?: Record<string, string> })?.metadata ?? {};
    const root = document.documentElement;
    if (branding.primary_color) root.style.setProperty("--primary", branding.primary_color);
    if (branding.accent_color) root.style.setProperty("--accent", branding.accent_color);
    if (branding.radius) root.style.setProperty("--radius", branding.radius);
  }, [tenant]);

  return null;
}
