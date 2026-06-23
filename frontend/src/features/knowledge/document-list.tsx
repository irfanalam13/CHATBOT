"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, FileText, RefreshCw, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge, Skeleton, Spinner } from "@/components/ui/misc";
import { api } from "@/lib/api";
import { formatBytes } from "@/lib/utils";
import type { DocumentItem, DocumentStatus } from "@/lib/types";
import { ChunkViewer } from "./chunk-viewer";

const STATUS_VARIANT: Record<DocumentStatus, "success" | "warning" | "secondary" | "destructive"> = {
  ready: "success",
  failed: "destructive",
  uploaded: "secondary",
  validating: "warning",
  scanning: "warning",
  extracting: "warning",
  chunking: "warning",
  embedding: "warning",
  indexing: "warning",
};

const IN_PROGRESS: DocumentStatus[] = [
  "uploaded", "validating", "scanning", "extracting", "chunking", "embedding", "indexing",
];

export function DocumentList({ knowledgeBaseId }: { knowledgeBaseId: string | null }) {
  const qc = useQueryClient();
  const [viewing, setViewing] = React.useState<DocumentItem | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["documents", knowledgeBaseId],
    queryFn: () => api.documents(knowledgeBaseId ?? undefined),
    // Poll while any document is still processing (embedding/index status).
    refetchInterval: (q) =>
      q.state.data?.items.some((d) => IN_PROGRESS.includes(d.status)) ? 2500 : false,
  });

  const reprocess = useMutation({
    mutationFn: (id: string) => api.reprocessDocument(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.deleteDocument(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
  });

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-14 w-full" />
        ))}
      </div>
    );
  }

  if (!data?.items.length) {
    return (
      <p className="py-8 text-center text-sm text-[var(--muted-foreground)]">
        No documents yet. Upload some above.
      </p>
    );
  }

  return (
    <>
      <ul className="divide-y divide-[var(--border)] rounded-xl border border-[var(--border)]">
        {data.items.map((doc) => {
          const processing = IN_PROGRESS.includes(doc.status);
          return (
            <li key={doc.id} className="flex items-center gap-3 p-3">
              <FileText className="h-5 w-5 shrink-0 text-[var(--muted-foreground)]" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{doc.filename}</p>
                <p className="text-xs text-[var(--muted-foreground)]">
                  {formatBytes(doc.size_bytes)} · {doc.chunk_count} chunks · v{doc.version}
                  {doc.error_message && ` · ${doc.error_message}`}
                </p>
              </div>
              <Badge variant={STATUS_VARIANT[doc.status]} className="capitalize">
                {processing && <Spinner className="mr-1 h-3 w-3" />}
                {doc.status}
              </Badge>
              <div className="flex items-center gap-0.5">
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="View chunks"
                  disabled={doc.status !== "ready"}
                  onClick={() => setViewing(doc)}
                >
                  <Eye className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Reprocess"
                  onClick={() => reprocess.mutate(doc.id)}
                >
                  <RefreshCw className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Delete"
                  onClick={() => remove.mutate(doc.id)}
                >
                  <Trash2 className="h-4 w-4 text-[var(--destructive)]" />
                </Button>
              </div>
            </li>
          );
        })}
      </ul>
      <ChunkViewer document={viewing} open={Boolean(viewing)} onClose={() => setViewing(null)} />
    </>
  );
}
