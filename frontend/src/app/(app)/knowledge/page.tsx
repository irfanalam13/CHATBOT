"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { PermissionGate } from "@/components/permission-gate";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/api";
import { DocumentList } from "@/features/knowledge/document-list";
import { Uploader } from "@/features/knowledge/uploader";

export default function KnowledgePage() {
  const qc = useQueryClient();
  const { data: kbs } = useQuery({ queryKey: ["kbs"], queryFn: () => api.knowledgeBases() });
  const [kbId, setKbId] = React.useState<string | null>(null);
  const [newName, setNewName] = React.useState("");

  React.useEffect(() => {
    if (!kbId && kbs?.items.length) setKbId(kbs.items[0].id);
  }, [kbs, kbId]);

  const create = useMutation({
    mutationFn: () =>
      api.createKnowledgeBase({
        name: newName,
        slug: newName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""),
      }),
    onSuccess: (kb) => {
      qc.invalidateQueries({ queryKey: ["kbs"] });
      setKbId(kb.id);
      setNewName("");
      toast.success("Knowledge base created");
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Failed"),
  });

  return (
    <div className="h-full overflow-y-auto scrollbar-thin">
      <div className="mx-auto max-w-4xl space-y-6 p-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Knowledge Base</h1>
          <div className="flex items-center gap-2">
            <select
              value={kbId ?? ""}
              onChange={(e) => setKbId(e.target.value || null)}
              aria-label="Knowledge base"
              className="h-9 rounded-md border border-[var(--input)] bg-transparent px-3 text-sm"
            >
              <option value="">Select…</option>
              {kbs?.items.map((kb) => (
                <option key={kb.id} value={kb.id}>
                  {kb.name} ({kb.document_count})
                </option>
              ))}
            </select>
          </div>
        </div>

        <PermissionGate permission="kb:manage">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Create knowledge base</CardTitle>
            </CardHeader>
            <CardContent>
              <form
                className="flex gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (newName.trim()) create.mutate();
                }}
              >
                <Input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Product Docs"
                />
                <Button type="submit" disabled={!newName.trim() || create.isPending}>
                  <Plus className="h-4 w-4" /> Create
                </Button>
              </form>
            </CardContent>
          </Card>
        </PermissionGate>

        <PermissionGate
          permission="doc:upload"
          fallback={
            <p className="text-sm text-[var(--muted-foreground)]">
              You don&apos;t have permission to upload documents.
            </p>
          }
        >
          <Uploader knowledgeBaseId={kbId} />
        </PermissionGate>

        <div>
          <h2 className="mb-2 text-sm font-semibold">Documents</h2>
          <DocumentList knowledgeBaseId={kbId} />
        </div>
      </div>
    </div>
  );
}
