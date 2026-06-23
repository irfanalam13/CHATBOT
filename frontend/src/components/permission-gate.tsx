"use client";

import { useAuthStore } from "@/stores/auth-store";
import type { Permission } from "@/lib/rbac";

/** Renders children only when the current user holds the permission. */
export function PermissionGate({
  permission,
  children,
  fallback = null,
}: {
  permission: Permission;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const can = useAuthStore((s) => s.can);
  return can(permission) ? <>{children}</> : <>{fallback}</>;
}
