"use client";

import { useQuery } from "@tanstack/react-query";

import { Dialog } from "@/components/ui/dialog";
import { Badge, Spinner } from "@/components/ui/misc";
import { api } from "@/lib/api";
import type { DocumentItem } from "@/lib/types";

export function ChunkViewer({
  document,
  open,
  onClose,
}: {
  document: DocumentItem | null;
  open: boolean;
  onClose: () => void;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["chunks", document?.id],
    queryFn: () => api.documentChunks(document!.id),
    enabled: open && Boolean(document),
  });

  return (
    <Dialog open={open} onClose={onClose} title={document?.filename}>
      {isLoading ? (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-xs text-[var(--muted-foreground)]">
            {data?.total ?? 0} chunks · version {document?.version}
          </p>
          {data?.items.map((c) => (
            <div key={c.id} className="rounded-lg border border-[var(--border)] p-3">
              <div className="mb-1 flex items-center gap-2 text-xs text-[var(--muted-foreground)]">
                <Badge variant="outline">#{c.chunk_index}</Badge>
                {c.page_number != null && <span>page {c.page_number}</span>}
                {c.token_count != null && <span>~{c.token_count} tokens</span>}
              </div>
              <p className="whitespace-pre-wrap text-sm">{c.content}</p>
            </div>
          ))}
        </div>
      )}
    </Dialog>
  );
}
