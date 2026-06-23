// Client-side mirror of the backend permission matrix (app/core/rbac.py).
// The server is always authoritative; this only drives UI affordances.
import type { Role } from "./types";

export type Permission =
  | "tenant:manage" | "tenant:read"
  | "user:create" | "user:read" | "user:update" | "user:delete"
  | "kb:manage" | "kb:read" | "doc:upload" | "doc:read" | "doc:delete"
  | "chat:use" | "chat:read_all" | "search:use"
  | "analytics:read" | "feedback:review"
  | "tool:manage" | "settings:manage" | "admin:platform";

const ALL: Permission[] = [
  "tenant:manage", "tenant:read", "user:create", "user:read", "user:update",
  "user:delete", "kb:manage", "kb:read", "doc:upload", "doc:read", "doc:delete",
  "chat:use", "chat:read_all", "search:use", "analytics:read", "feedback:review",
  "tool:manage", "settings:manage", "admin:platform",
];

const MATRIX: Record<Role, Permission[]> = {
  super_admin: ALL,
  tenant_admin: [
    "tenant:read", "user:create", "user:read", "user:update", "user:delete",
    "kb:manage", "kb:read", "doc:upload", "doc:read", "doc:delete",
    "chat:use", "chat:read_all", "search:use", "analytics:read",
    "feedback:review", "tool:manage", "settings:manage",
  ],
  manager: [
    "tenant:read", "user:read", "kb:read", "doc:upload", "doc:read", "doc:delete",
    "chat:use", "chat:read_all", "search:use", "analytics:read", "feedback:review",
  ],
  employee: ["kb:read", "doc:upload", "doc:read", "chat:use", "search:use"],
  viewer: ["kb:read", "doc:read", "chat:use", "search:use"],
};

export function hasPermission(
  role: Role | undefined,
  permission: Permission,
  custom: string[] = [],
): boolean {
  if (!role) return false;
  if (custom.includes(permission)) return true;
  return MATRIX[role]?.includes(permission) ?? false;
}
