"use client";

import { Layers, Trophy } from "lucide-react";

import { cn } from "@/lib/utils";
import type { StreamCitation } from "@/lib/types";

/** RAG visualization: retrieved chunks, ranking, confidence, document origin. */
export function RagPanel({ citations }: { citations: StreamCitation[] }) {
  if (!citations.length) {
    return (
      <div className="p-4 text-sm text-[var(--muted-foreground)]">
        No retrieval for this turn. Ask a question grounded in your knowledge base to see
        retrieved chunks here.
      </div>
    );
  }

  const max = Math.max(...citations.map((c) => c.confidence), 0.0001);

  return (
    <div className="space-y-3 p-4">
      <div className="flex items-center gap-2 text-sm font-medium">
        <Layers className="h-4 w-4" /> Retrieved chunks ({citations.length})
      </div>
      {citations.map((c, i) => (
        <div key={i} className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-3">
          <div className="mb-1.5 flex items-center justify-between text-xs">
            <span className="inline-flex items-center gap-1 font-medium">
              {i === 0 && <Trophy className="h-3 w-3 text-amber-500" />}
              #{c.index} · {c.document_name ?? "source"}
              {c.page_number != null && ` · p.${c.page_number}`}
            </span>
            <span className="font-mono text-[var(--muted-foreground)]">
              {(c.confidence * 100).toFixed(1)}%
            </span>
          </div>
          {/* confidence/ranking bar */}
          <div className="mb-2 h-1.5 w-full overflow-hidden rounded-full bg-[var(--muted)]">
            <div
              className={cn("h-full rounded-full bg-[var(--primary)]")}
              style={{ width: `${(c.confidence / max) * 100}%` }}
            />
          </div>
          <p className="line-clamp-4 text-xs text-[var(--muted-foreground)]">{c.snippet}</p>
        </div>
      ))}
    </div>
  );
}
