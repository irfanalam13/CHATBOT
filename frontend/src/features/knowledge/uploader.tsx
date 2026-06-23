"use client";

import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, FileUp, Loader2, UploadCloud, XCircle } from "lucide-react";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { cn, formatBytes } from "@/lib/utils";

interface UploadItem {
  file: File;
  progress: number;
  status: "pending" | "uploading" | "done" | "error";
  error?: string;
}

const ACCEPT = ".pdf,.docx,.txt,.csv,.xlsx,.xls,.html,.htm,.md,.json,.xml,.eml";

export function Uploader({ knowledgeBaseId }: { knowledgeBaseId: string | null }) {
  const qc = useQueryClient();
  const [items, setItems] = React.useState<UploadItem[]>([]);
  const [dragging, setDragging] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const upload = React.useCallback(
    async (files: FileList | File[]) => {
      if (!knowledgeBaseId) {
        toast.error("Select or create a knowledge base first");
        return;
      }
      const arr = Array.from(files);
      setItems((prev) => [
        ...prev,
        ...arr.map((file) => ({ file, progress: 0, status: "pending" as const })),
      ]);

      for (const file of arr) {
        setItems((prev) =>
          prev.map((it) => (it.file === file ? { ...it, status: "uploading" } : it)),
        );
        try {
          await api.uploadDocument(knowledgeBaseId, file, (pct) =>
            setItems((prev) =>
              prev.map((it) => (it.file === file ? { ...it, progress: pct } : it)),
            ),
          );
          setItems((prev) =>
            prev.map((it) =>
              it.file === file ? { ...it, status: "done", progress: 100 } : it,
            ),
          );
        } catch (e) {
          setItems((prev) =>
            prev.map((it) =>
              it.file === file ? { ...it, status: "error", error: (e as Error).message } : it,
            ),
          );
        }
      }
      qc.invalidateQueries({ queryKey: ["documents"] });
    },
    [knowledgeBaseId, qc],
  );

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          upload(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label="Upload documents"
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition-colors",
          dragging
            ? "border-[var(--primary)] bg-[var(--accent)]"
            : "border-[var(--border)] hover:bg-[var(--accent)]",
        )}
      >
        <UploadCloud className="mb-2 h-8 w-8 text-[var(--muted-foreground)]" />
        <p className="text-sm font-medium">Drag &amp; drop files, or click to browse</p>
        <p className="mt-1 text-xs text-[var(--muted-foreground)]">
          PDF, DOCX, TXT, CSV, XLSX, HTML, MD, JSON, XML, EML — bulk upload supported
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => e.target.files && upload(e.target.files)}
        />
      </div>

      {items.length > 0 && (
        <ul className="mt-3 space-y-2">
          {items.map((it, i) => (
            <li
              key={i}
              className="flex items-center gap-3 rounded-lg border border-[var(--border)] p-2.5 text-sm"
            >
              <FileUp className="h-4 w-4 shrink-0 text-[var(--muted-foreground)]" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <span className="truncate">{it.file.name}</span>
                  <span className="ml-2 shrink-0 text-xs text-[var(--muted-foreground)]">
                    {formatBytes(it.file.size)}
                  </span>
                </div>
                <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-[var(--muted)]">
                  <div
                    className="h-full bg-[var(--primary)] transition-all"
                    style={{ width: `${it.progress}%` }}
                  />
                </div>
                {it.error && <p className="mt-0.5 text-xs text-[var(--destructive)]">{it.error}</p>}
              </div>
              {it.status === "done" ? (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              ) : it.status === "error" ? (
                <XCircle className="h-4 w-4 text-[var(--destructive)]" />
              ) : (
                <Loader2 className="h-4 w-4 animate-spin text-[var(--muted-foreground)]" />
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
