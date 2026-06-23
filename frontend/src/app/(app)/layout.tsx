import { AppShell } from "@/components/app-shell";
import { AuthGuard } from "@/components/auth-guard";
import { ThemeInjector } from "@/features/branding/theme-injector";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <ThemeInjector />
      <AppShell>{children}</AppShell>
    </AuthGuard>
  );
}
