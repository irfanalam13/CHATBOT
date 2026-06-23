"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BarChart3,
  BookOpen,
  Bot,
  LogOut,
  Menu,
  MessageSquare,
  Monitor,
  Moon,
  Search,
  Settings,
  Sun,
} from "lucide-react";

import { Avatar } from "@/components/ui/misc";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import { usePreferences } from "@/stores/preferences-store";

const NAV = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/knowledge", label: "Knowledge", icon: BookOpen },
  { href: "/search", label: "Search", icon: Search },
  { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({
  children,
  secondary,
}: {
  children: React.ReactNode;
  secondary?: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, tenant, logout } = useAuthStore();
  const { theme, setTheme } = usePreferences();
  const [mobileNav, setMobileNav] = React.useState(false);

  const cycleTheme = () =>
    setTheme(theme === "light" ? "dark" : theme === "dark" ? "system" : "light");
  const ThemeIcon = theme === "light" ? Sun : theme === "dark" ? Moon : Monitor;

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Nav rail */}
      <nav
        className={cn(
          "flex w-16 shrink-0 flex-col items-center border-r border-[var(--border)] bg-[var(--card)] py-3",
          mobileNav ? "fixed inset-y-0 z-40 flex" : "hidden md:flex",
        )}
        aria-label="Primary"
      >
        <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--primary)] text-[var(--primary-foreground)]">
          <Bot className="h-5 w-5" />
        </div>
        <div className="flex flex-1 flex-col gap-1">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                title={label}
                aria-label={label}
                aria-current={active ? "page" : undefined}
                onClick={() => setMobileNav(false)}
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-lg transition-colors",
                  active
                    ? "bg-[var(--accent)] text-[var(--accent-foreground)]"
                    : "text-[var(--muted-foreground)] hover:bg-[var(--accent)]",
                )}
              >
                <Icon className="h-5 w-5" />
              </Link>
            );
          })}
        </div>
        <button
          onClick={cycleTheme}
          title={`Theme: ${theme}`}
          aria-label="Toggle theme"
          className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg text-[var(--muted-foreground)] hover:bg-[var(--accent)]"
        >
          <ThemeIcon className="h-5 w-5" />
        </button>
      </nav>

      {/* Secondary panel (e.g. chat sidebar) */}
      {secondary && (
        <aside className="hidden w-72 shrink-0 border-r border-[var(--border)] bg-[var(--card)] md:block">
          {secondary}
        </aside>
      )}

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 items-center justify-between border-b border-[var(--border)] px-4">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setMobileNav((m) => !m)}
              aria-label="Menu"
            >
              <Menu className="h-5 w-5" />
            </Button>
            <span className="text-sm font-semibold">
              {tenant?.name ?? process.env.NEXT_PUBLIC_APP_NAME}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden text-xs text-[var(--muted-foreground)] sm:block">
              {user?.email}
            </span>
            <Avatar name={user?.full_name ?? user?.email} />
            <Button
              variant="ghost"
              size="icon"
              onClick={async () => {
                await logout();
                router.replace("/login");
              }}
              aria-label="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </header>
        <main id="main" className="min-h-0 flex-1 overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}
