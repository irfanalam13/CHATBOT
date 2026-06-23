import { create } from "zustand";

import { api } from "@/lib/api";
import { tokenStore } from "@/lib/storage";
import type { Permission } from "@/lib/rbac";
import { hasPermission } from "@/lib/rbac";
import type { Tenant, User } from "@/lib/types";

interface AuthState {
  user: User | null;
  tenant: Tenant | null;
  status: "idle" | "loading" | "authenticated" | "unauthenticated";
  login: (email: string, password: string, tenantSlug: string) => Promise<void>;
  register: (data: {
    tenant_name: string;
    tenant_slug: string;
    admin_email: string;
    admin_password: string;
    admin_full_name?: string;
  }) => Promise<void>;
  bootstrap: () => Promise<void>;
  logout: () => Promise<void>;
  can: (permission: Permission) => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  tenant: null,
  status: "idle",

  async login(email, password, tenantSlug) {
    set({ status: "loading" });
    const tokens = await api.login(email, password, tenantSlug);
    tokenStore.set(tokens);
    const [user, tenant] = await Promise.all([api.me(), api.tenant().catch(() => null)]);
    set({ user, tenant, status: "authenticated" });
  },

  async register(data) {
    set({ status: "loading" });
    const tokens = await api.register(data);
    tokenStore.set(tokens);
    const [user, tenant] = await Promise.all([api.me(), api.tenant().catch(() => null)]);
    set({ user, tenant, status: "authenticated" });
  },

  async bootstrap() {
    if (!tokenStore.has()) {
      set({ status: "unauthenticated" });
      return;
    }
    set({ status: "loading" });
    try {
      const [user, tenant] = await Promise.all([api.me(), api.tenant().catch(() => null)]);
      set({ user, tenant, status: "authenticated" });
    } catch {
      tokenStore.clear();
      set({ status: "unauthenticated" });
    }
  },

  async logout() {
    const refresh = tokenStore.refresh;
    if (refresh) await api.logout(refresh).catch(() => undefined);
    tokenStore.clear();
    set({ user: null, tenant: null, status: "unauthenticated" });
  },

  can(permission) {
    const u = get().user;
    return hasPermission(u?.role, permission, u?.custom_permissions ?? []);
  },
}));
