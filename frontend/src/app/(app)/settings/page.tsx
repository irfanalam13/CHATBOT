"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge, Separator } from "@/components/ui/misc";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PermissionGate } from "@/components/permission-gate";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { usePreferences } from "@/stores/preferences-store";

const MODELS = [
  "claude-opus-4-8",
  "claude-sonnet-4-6",
  "claude-haiku-4-5",
  "gpt-4o",
  "gemini-1.5-pro",
];

export default function SettingsPage() {
  return (
    <div className="h-full overflow-y-auto scrollbar-thin">
      <div className="mx-auto max-w-3xl space-y-6 p-6">
        <h1 className="text-2xl font-bold">Settings</h1>
        <Tabs defaultValue="profile">
          <TabsList>
            <TabsTrigger value="profile">Profile</TabsTrigger>
            <TabsTrigger value="appearance">Appearance</TabsTrigger>
            <TabsTrigger value="ai">AI &amp; RAG</TabsTrigger>
            <TabsTrigger value="branding">Branding</TabsTrigger>
          </TabsList>
          <TabsContent value="profile">
            <ProfileSection />
          </TabsContent>
          <TabsContent value="appearance">
            <AppearanceSection />
          </TabsContent>
          <TabsContent value="ai">
            <PermissionGate
              permission="settings:manage"
              fallback={<LockedNotice />}
            >
              <AiSection />
            </PermissionGate>
          </TabsContent>
          <TabsContent value="branding">
            <PermissionGate permission="settings:manage" fallback={<LockedNotice />}>
              <BrandingSection />
            </PermissionGate>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function LockedNotice() {
  return (
    <Card>
      <CardContent className="pt-5 text-sm text-[var(--muted-foreground)]">
        You need the <code>settings:manage</code> permission to change these settings.
      </CardContent>
    </Card>
  );
}

function ProfileSection() {
  const { user, tenant } = useAuthStore();
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Your profile</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <Row label="Name" value={user?.full_name ?? "—"} />
        <Row label="Email" value={user?.email ?? "—"} />
        <Row label="Role" value={<Badge variant="secondary" className="capitalize">{user?.role}</Badge>} />
        <Separator />
        <Row label="Workspace" value={tenant?.name ?? "—"} />
        <Row label="Tenant ID" value={<code className="text-xs">{tenant?.slug}</code>} />
      </CardContent>
    </Card>
  );
}

function AppearanceSection() {
  const prefs = usePreferences();
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Appearance &amp; accessibility</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1">
          <span className="text-sm font-medium">Theme</span>
          <div className="flex gap-1 rounded-lg bg-[var(--muted)] p-1">
            {(["light", "dark", "system"] as const).map((t) => (
              <button
                key={t}
                onClick={() => prefs.setTheme(t)}
                className={`flex-1 rounded-md px-3 py-1.5 text-sm capitalize ${
                  prefs.theme === t ? "bg-[var(--background)] shadow-sm" : "text-[var(--muted-foreground)]"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
        <Toggle label="High contrast mode" checked={prefs.highContrast} onChange={prefs.toggleHighContrast} />
        <Toggle label="Reduce motion" checked={prefs.reducedMotion} onChange={prefs.toggleReducedMotion} />
      </CardContent>
    </Card>
  );
}

function AiSection() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["settings"], queryFn: () => api.settings() });
  const [form, setForm] = React.useState<Record<string, unknown>>({});

  const save = useMutation({
    mutationFn: () => api.updateSettings(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settings"] });
      setForm({});
      toast.success("Settings saved");
    },
  });

  const value = (k: string, fallback: unknown) =>
    (form[k] ?? (data as Record<string, unknown> | undefined)?.[k] ?? fallback) as never;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Model &amp; retrieval</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <LabeledSelect
          label="LLM model"
          value={value("llm_model", "claude-opus-4-8")}
          options={MODELS}
          onChange={(v) => setForm((f) => ({ ...f, llm_model: v }))}
        />
        <div className="space-y-1">
          <span className="text-sm font-medium">System prompt</span>
          <Textarea
            rows={3}
            defaultValue={data?.system_prompt ?? ""}
            placeholder="You are a helpful enterprise assistant…"
            onChange={(e) => setForm((f) => ({ ...f, system_prompt: e.target.value }))}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <LabeledInput
            label="Chunk size"
            type="number"
            defaultValue={data?.chunk_size ?? 800}
            onChange={(v) => setForm((f) => ({ ...f, chunk_size: Number(v) }))}
          />
          <LabeledInput
            label="Retrieval top-K"
            type="number"
            defaultValue={data?.retrieval_top_k ?? 8}
            onChange={(v) => setForm((f) => ({ ...f, retrieval_top_k: Number(v) }))}
          />
        </div>
        <Toggle
          label="Enable reranking"
          checked={value("enable_reranking", true)}
          onChange={() => setForm((f) => ({ ...f, enable_reranking: !value("enable_reranking", true) }))}
        />
        <Toggle
          label="Enable tools / function calling"
          checked={value("enable_tools", true)}
          onChange={() => setForm((f) => ({ ...f, enable_tools: !value("enable_tools", true) }))}
        />

        <Separator />
        <p className="text-sm font-medium">Provider API keys (write-only)</p>
        <div className="grid gap-2">
          <KeyInput label="Anthropic" set={data?.has_anthropic_key} onChange={(v) => setForm((f) => ({ ...f, anthropic_api_key: v }))} />
          <KeyInput label="OpenAI" set={data?.has_openai_key} onChange={(v) => setForm((f) => ({ ...f, openai_api_key: v }))} />
          <KeyInput label="Google" set={data?.has_google_key} onChange={(v) => setForm((f) => ({ ...f, google_api_key: v }))} />
        </div>

        <Button onClick={() => save.mutate()} disabled={save.isPending || !Object.keys(form).length}>
          Save changes
        </Button>
      </CardContent>
    </Card>
  );
}

function BrandingSection() {
  const qc = useQueryClient();
  const { tenant } = useAuthStore();
  const meta = (tenant as unknown as { metadata?: Record<string, string> })?.metadata ?? {};
  const [primary, setPrimary] = React.useState(meta.primary_color ?? "#4f46e5");
  const [name, setName] = React.useState(tenant?.name ?? "");

  const save = useMutation({
    mutationFn: () =>
      api.updateTenant({
        name,
        // metadata carries white-label branding tokens
        ...({ metadata: { ...meta, primary_color: primary } } as object),
      }),
    onSuccess: () => {
      qc.invalidateQueries();
      document.documentElement.style.setProperty("--primary", primary);
      toast.success("Branding updated");
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">White-label branding</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <LabeledInput label="Display name" defaultValue={name} onChange={setName} />
        <div className="space-y-1">
          <span className="text-sm font-medium">Primary brand color</span>
          <div className="flex items-center gap-2">
            <input
              type="color"
              value={primary}
              onChange={(e) => setPrimary(e.target.value)}
              className="h-9 w-12 rounded border border-[var(--border)]"
              aria-label="Primary color"
            />
            <Input value={primary} onChange={(e) => setPrimary(e.target.value)} className="w-32 font-mono" />
            <span
              className="ml-2 rounded-md px-3 py-1.5 text-sm text-white"
              style={{ background: primary }}
            >
              Preview
            </span>
          </div>
        </div>
        <Button onClick={() => save.mutate()} disabled={save.isPending}>
          Save branding
        </Button>
      </CardContent>
    </Card>
  );
}

// ── small helpers ─────────────────────────────────────────────
function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[var(--muted-foreground)]">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: () => void }) {
  return (
    <label className="flex items-center justify-between text-sm">
      <span className="font-medium">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={onChange}
        className={`relative h-6 w-11 rounded-full transition-colors ${
          checked ? "bg-[var(--primary)]" : "bg-[var(--muted)]"
        }`}
      >
        <span
          className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
            checked ? "translate-x-5" : "translate-x-0.5"
          }`}
        />
      </button>
    </label>
  );
}

function LabeledInput({
  label,
  type = "text",
  defaultValue,
  onChange,
}: {
  label: string;
  type?: string;
  defaultValue?: string | number;
  onChange: (v: string) => void;
}) {
  return (
    <label className="block space-y-1">
      <span className="text-sm font-medium">{label}</span>
      <Input type={type} defaultValue={defaultValue} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

function LabeledSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <label className="block space-y-1">
      <span className="text-sm font-medium">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 w-full rounded-md border border-[var(--input)] bg-transparent px-3 text-sm"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}

function KeyInput({
  label,
  set,
  onChange,
}: {
  label: string;
  set?: boolean;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="w-24 font-medium">{label}</span>
      <Input
        type="password"
        placeholder={set ? "•••••••• (set)" : "Not configured"}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}
