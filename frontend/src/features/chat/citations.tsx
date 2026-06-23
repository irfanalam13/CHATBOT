"use client";

import * as React from "react";
import { ExternalLink, FileText } from "lucide-react";

import { Badge } from "@/components/ui/misc";
import { cn } from "@/lib/utils";
import type { Citation, StreamCitation } from "@/lib/types";

type AnyCitation = (Citation | StreamCitation) & { index?: number };

function confidenceColor(c: number | null | undefined): string {
  if (c == null) return "text-[var(--muted-foreground)]";
  if (c >= 0.7) return "text-green-600 dark:text-green-400";
  if (c >= 0.4) return "text-amber-600 dark:text-amber-400";
  return "text-[var(--destructive)]";
}

export function Citations({ citations }: { citations: AnyCitation[] }) {
  const [open, setOpen] = React.useState<number | null>(null);
  if (!citations.length) return null;

  return (
    <div className="mt-3 border-t border-[var(--border)] pt-2">
      <p className="mb-1.5 text-xs font-medium text-[var(--muted-foreground)]">Sources</p>
      <div className="flex flex-wrap gap-1.5">
        {citations.map((c, i) => {
          const conf = c.confidence ?? null;
          return (
            <button
              key={i}
              onClick={() => setOpen(open === i ? null : i)}
              className="inline-flex items-center gap-1 rounded-md border border-[var(--border)] bg-[var(--card)] px-2 py-1 text-xs hover:bg-[var(--accent)]"
            >
              <FileText className="h-3 w-3" />
              <span className="font-medium">[{c.index ?? i + 1}]</span>
              <span className="max-w-[140px] truncate">{c.document_name ?? "source"}</span>
              {conf != null && (
                <span className={cn("font-mono", confidenceColor(conf))}>
                  {(conf * 100).toFixed(0)}%
                </span>
              )}
            </button>
          );
        })}
      </div>

      {open != null && citations[open] && (
        <div className="mt-2 rounded-md border border-[var(--border)] bg-[var(--muted)] p-3 text-xs">
          <div className="mb-1 flex items-center justify-between">
            <span className="font-semibold">{citations[open].document_name}</span>
            <div className="flex items-center gap-2">
              {citations[open].page_number != null && (
                <Badge variant="outline">p.{citations[open].page_number}</Badge>
              )}
              {citations[open].source_link && (
                <a
                  href={citations[open].source_link!}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-[var(--primary)]"
                >
                  Open <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </div>
          <p className="text-[var(--muted-foreground)]">{citations[open].snippet}</p>
        </div>
      )}
    </div>
  );
}
