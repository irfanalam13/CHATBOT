"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Bot } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Spinner } from "@/components/ui/misc";
import { ApiError } from "@/lib/api";
import { emailSchema } from "@/lib/validation";
import { useAuthStore } from "@/stores/auth-store";

const schema = z.object({
  tenant_slug: z.string().min(1, "Required"),
  email: emailSchema,
  password: z.string().min(1, "Required"),
});
type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  return (
    <React.Suspense fallback={null}>
      <LoginForm />
    </React.Suspense>
  );
}

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") ?? "/chat";
  const { login, status, bootstrap } = useAuthStore();

  React.useEffect(() => {
    if (status === "idle") bootstrap();
  }, [status, bootstrap]);
  React.useEffect(() => {
    if (status === "authenticated") router.replace(next);
  }, [status, router, next]);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { tenant_slug: process.env.NEXT_PUBLIC_DEFAULT_TENANT ?? "" },
  });

  const onSubmit = async (values: FormValues) => {
    try {
      await login(values.email, values.password, values.tenant_slug);
      router.replace(next);
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Login failed");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--muted)] p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--primary)] text-[var(--primary-foreground)]">
            <Bot className="h-6 w-6" />
          </div>
          <CardTitle>{process.env.NEXT_PUBLIC_APP_NAME ?? "Sign in"}</CardTitle>
          <CardDescription>Access your AI assistant</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3" noValidate>
            <Field label="Workspace" error={errors.tenant_slug?.message}>
              <Input placeholder="acme" autoComplete="organization" {...register("tenant_slug")} />
            </Field>
            <Field label="Email" error={errors.email?.message}>
              <Input type="email" placeholder="you@company.com" autoComplete="email" {...register("email")} />
            </Field>
            <Field label="Password" error={errors.password?.message}>
              <PasswordInput autoComplete="current-password" {...register("password")} />
            </Field>
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? <Spinner /> : "Sign in"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-[var(--muted-foreground)]">
            New here?{" "}
            <Link href="/register" className="font-medium text-[var(--primary)] hover:underline">
              Create a workspace
            </Link>
          </p>
          <p className="mt-2 text-center text-xs text-[var(--muted-foreground)]">
            Demo: workspace <code className="font-mono">demo</code> · admin@demo.test / demo12345
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-1">
      <span className="text-sm font-medium">{label}</span>
      {children}
      {error && <span className="block text-xs text-[var(--destructive)]">{error}</span>}
    </label>
  );
}
