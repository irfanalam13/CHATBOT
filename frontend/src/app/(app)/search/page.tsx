"use client";

import * as React from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { FileText, Search as SearchIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge, Spinner } from "@/components/ui/misc";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { SearchHit } from "@/lib/types";

const MODES = ["hybrid", "semantic", "keyword"] as const;

export default function SearchPage() {
  const [query, setQuery] = React.useState("");
  const [mode, setMode] = React.useState<(typeof MODES)[number]>("hybrid");
  const [kbId, setKbId] = React.useState<string | undefined>(undefined);
  const [rerank, setRerank] = React.useState(true);

  const { data: kbs } = useQuery({ queryKey: ["kbs"], queryFn: () => api.knowledgeBases() });

  const search = useMutation({
    mutationFn: () =>
      api.searchDocuments({ query, mode, knowledge_base_id: kbId, rerank, top_k: 12 }),
  });

  return (
    <div className="h-full overflow-y-auto scrollbar-thin">
      <div className="mx-auto max-w-3xl space-y-4 p-6">
        <h1 className="text-2xl font-bold">Search</h1>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (query.trim()) search.mutate();
          }}
          className="space-y-3"
        >
          <div className="relative">
            <SearchIcon className="absolute left-3 top-3 h-4 w-4 text-[var(--muted-foreground)]" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search across your knowledge base…"
              className="h-11 pl-9 text-base"
              autoFocus
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex rounded-lg bg-[var(--muted)] p-1">
              {MODES.map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMode(m)}
                  className={cn(
                    "rounded-md px-3 py-1 text-xs font-medium capitalize",
                    mode === m
                      ? "bg-[var(--background)] shadow-sm"
                      : "text-[var(--muted-foreground)]",
                  )}
                >
                  {m}
                </button>
              ))}
            </div>
            <select
              value={kbId ?? ""}
              onChange={(e) => setKbId(e.target.value || undefined)}
              aria-label="Knowledge base filter"
              className="h-8 rounded-md border border-[var(--input)] bg-transparent px-2 text-xs"
            >
              <option value="">All knowledge bases</option>
              {kbs?.items.map((kb) => (
                <option key={kb.id} value={kb.id}>
                  {kb.name}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-1.5 text-xs">
              <input type="checkbox" checked={rerank} onChange={(e) => setRerank(e.target.checked)} />
              Rerank
            </label>
            <Button type="submit" size="sm" disabled={!query.trim() || search.isPending}>
              {search.isPending ? <Spinner /> : "Search"}
            </Button>
          </div>
        </form>

        {search.data && (
          <p className="text-xs text-[var(--muted-foreground)]">
            {search.data.hits.length} results · {search.data.took_ms}ms · {search.data.mode}
          </p>
        )}

        <div className="space-y-3">
          {search.data?.hits.map((hit, i) => (
            <ResultCard key={i} hit={hit} rank={i + 1} />
          ))}
          {search.isError && (
            <p className="text-sm text-[var(--destructive)]">Search failed. Try again.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function ResultCard({ hit, rank }: { hit: SearchHit; rank: number }) {
  return (
    <Card>
      <CardContent className="pt-5">
        <div className="mb-1.5 flex items-center justify-between text-sm">
          <span className="inline-flex items-center gap-1.5 font-medium">
            <FileText className="h-4 w-4 text-[var(--muted-foreground)]" />
            {hit.document_name ?? "Source"}
            {hit.page_number != null && (
              <span className="text-[var(--muted-foreground)]">· p.{hit.page_number}</span>
            )}
          </span>
          <Badge variant="outline">
            #{rank} · {(hit.score * 100).toFixed(1)}%
          </Badge>
        </div>
        <p className="text-sm text-[var(--muted-foreground)]">{hit.content}</p>
      </CardContent>
    </Card>
  );
}
