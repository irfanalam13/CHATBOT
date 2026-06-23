"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
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

// Mirrors the backend RegisterTenantRequest constraints (app/schemas/auth.py).
const schema = z.object({
  tenant_name: z.string().min(2, "At least 2 characters").max(255),
  tenant_slug: z
    .string()
    .min(2, "At least 2 characters")
    .max(120)
    .regex(/^[a-z0-9-]+$/, "Lowercase letters, numbers and hyphens only"),
  admin_full_name: z.string().max(255).optional(),
  admin_email: emailSchema,
  admin_password: z.string().min(8, "At least 8 characters").max(128),
});
type FormValues = z.infer<typeof schema>;

const slugify = (value: string) =>
  value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 120);

export default function RegisterPage() {
  const router = useRouter();
  const { register: registerTenant, status, bootstrap } = useAuthStore();

  React.useEffect(() => {
    if (status === "idle") bootstrap();
  }, [status, bootstrap]);
  React.useEffect(() => {
    if (status === "authenticated") router.replace("/chat");
  }, [status, router]);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  // Auto-fill the slug from the workspace name until the user edits it manually.
  const slugEdited = React.useRef(false);
  const onNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!slugEdited.current) {
      setValue("tenant_slug", slugify(e.target.value), { shouldValidate: true });
    }
  };

  const slugField = register("tenant_slug");

  const onSubmit = async (values: FormValues) => {
    try {
      await registerTenant({
        tenant_name: values.tenant_name,
        tenant_slug: values.tenant_slug,
        admin_email: values.admin_email,
        admin_password: values.admin_password,
        admin_full_name: values.admin_full_name || undefined,
      });
      toast.success("Workspace created");
      router.replace("/chat");
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Sign up failed");
    }
  };

  const nameField = register("tenant_name");

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--muted)] p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--primary)] text-[var(--primary-foreground)]">
            <Bot className="h-6 w-6" />
          </div>
          <CardTitle>Create your workspace</CardTitle>
          <CardDescription>Set up a new tenant and admin account</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3" noValidate>
            <Field label="Workspace name" error={errors.tenant_name?.message}>
              <Input
                placeholder="Acme Inc."
                autoComplete="organization"
                {...nameField}
                onChange={(e) => {
                  nameField.onChange(e);
                  onNameChange(e);
                }}
              />
            </Field>
            <Field
              label="Workspace URL"
              error={errors.tenant_slug?.message}
              hint="Used to sign in. Lowercase letters, numbers and hyphens."
            >
              <Input
                placeholder="acme"
                autoComplete="off"
                {...slugField}
                onChange={(e) => {
                  slugEdited.current = true;
                  slugField.onChange(e);
                }}
              />
            </Field>
            <Field label="Your name" error={errors.admin_full_name?.message}>
              <Input placeholder="Jane Doe" autoComplete="name" {...register("admin_full_name")} />
            </Field>
            <Field label="Email" error={errors.admin_email?.message}>
              <Input
                type="email"
                placeholder="you@company.com"
                autoComplete="email"
                {...register("admin_email")}
              />
            </Field>
            <Field label="Password" error={errors.admin_password?.message}>
              <PasswordInput autoComplete="new-password" {...register("admin_password")} />
            </Field>
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? <Spinner /> : "Create workspace"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-[var(--muted-foreground)]">
            Already have a workspace?{" "}
            <Link href="/login" className="font-medium text-[var(--primary)] hover:underline">
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function Field({
  label,
  error,
  hint,
  children,
}: {
  label: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-1">
      <span className="text-sm font-medium">{label}</span>
      {children}
      {hint && !error && (
        <span className="block text-xs text-[var(--muted-foreground)]">{hint}</span>
      )}
      {error && <span className="block text-xs text-[var(--destructive)]">{error}</span>}
    </label>
  );
}
