"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Layers, MessageSquarePlus, Wrench } from "lucide-react";

import { Markdown } from "@/components/markdown/markdown";
import { Button } from "@/components/ui/button";
import { Avatar, Badge } from "@/components/ui/misc";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/stores/chat-store";
import { Citations } from "./citations";
import { Composer } from "./composer";
import { MessageBubble } from "./message-bubble";
import { RagPanel } from "./rag-panel";
import { TypingIndicator } from "./typing-indicator";
import { useSendMessage, useSessionMessages } from "./use-chat";

const STARTERS = [
  "What can you help me with?",
  "Summarize our latest documents",
  "What is our refund policy?",
  "Show recent activity",
];

export function ChatWindow() {
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const setActiveSession = useChatStore((s) => s.setActiveSession);
  const { draftContent, draftCitations, toolEvents, streaming, warning, error } = useChatStore();
  const stop = useChatStore((s) => s.stop);

  const [kbId, setKbId] = React.useState<string | undefined>(undefined);
  const [showRag, setShowRag] = React.useState(false);
  const { data: kbs } = useQuery({ queryKey: ["kbs"], queryFn: () => api.knowledgeBases() });
  const { data: messages } = useSessionMessages(activeSessionId);
  const send = useSendMessage(kbId);

  const scrollRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, draftContent, streaming]);

  const lastUser = React.useMemo(
    () => [...(messages ?? [])].reverse().find((m) => m.role === "user"),
    [messages],
  );

  const regenerate = () => {
    if (lastUser) send(lastUser.content);
  };

  const empty = !activeSessionId && !streaming && !(messages?.length);

  return (
    <div className="flex h-full">
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Header */}
        <header className="flex items-center justify-between gap-2 border-b border-[var(--border)] px-4 py-2.5">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setActiveSession(null)}
              className="gap-1"
            >
              <MessageSquarePlus className="h-4 w-4" /> New
            </Button>
            <select
              value={kbId ?? ""}
              onChange={(e) => setKbId(e.target.value || undefined)}
              aria-label="Knowledge base"
              className="h-8 rounded-md border border-[var(--input)] bg-transparent px-2 text-sm"
            >
              <option value="">All knowledge</option>
              {kbs?.items.map((kb) => (
                <option key={kb.id} value={kb.id}>
                  {kb.name}
                </option>
              ))}
            </select>
          </div>
          <Button
            variant={showRag ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setShowRag((s) => !s)}
            className="gap-1"
          >
            <Layers className="h-4 w-4" /> Sources
          </Button>
        </header>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin">
          <div className="mx-auto max-w-3xl space-y-6 px-4 py-6">
            {empty ? (
              <EmptyState onPick={(q) => send(q)} />
            ) : (
              <>
                {messages?.map((m) => (
                  <MessageBubble
                    key={m.id}
                    message={m}
                    onRegenerate={m.role === "assistant" ? regenerate : undefined}
                  />
                ))}

                {streaming && (
                  <div className="flex gap-3">
                    <Avatar name="AI" className="bg-[var(--accent)] text-[var(--accent-foreground)]" />
                    <div className="max-w-[min(80%,720px)] rounded-2xl rounded-tl-sm border border-[var(--border)] bg-[var(--card)] px-4 py-2.5 text-sm">
                      {toolEvents.length > 0 && (
                        <div className="mb-2 flex flex-wrap gap-1.5">
                          {toolEvents.map((t, i) => (
                            <Badge key={i} variant={t.status === "done" ? "success" : "secondary"}>
                              <Wrench className="mr-1 h-3 w-3" />
                              {t.name} {t.status === "calling" ? "…" : "✓"}
                            </Badge>
                          ))}
                        </div>
                      )}
                      {draftContent ? <Markdown content={draftContent} /> : <TypingIndicator />}
                      {draftCitations.length > 0 && <Citations citations={draftCitations} />}
                    </div>
                  </div>
                )}

                {warning && (
                  <div className="flex items-center gap-2 rounded-md bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-400">
                    <AlertTriangle className="h-4 w-4" /> {warning}
                  </div>
                )}
                {error && (
                  <div className="flex items-center gap-2 rounded-md bg-[var(--destructive)]/10 px-3 py-2 text-xs text-[var(--destructive)]">
                    <AlertTriangle className="h-4 w-4" /> {error}
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Composer */}
        <div className="border-t border-[var(--border)] px-4 py-3">
          <div className="mx-auto max-w-3xl">
            <Composer
              onSend={(t) => send(t)}
              onStop={stop}
              streaming={streaming}
              showSuggestions={Boolean(activeSessionId) || empty}
            />
          </div>
        </div>
      </div>

      {/* RAG side panel */}
      {showRag && (
        <aside className="hidden w-80 shrink-0 overflow-y-auto border-l border-[var(--border)] scrollbar-thin lg:block">
          <RagPanel citations={draftCitations} />
        </aside>
      )}
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--primary)] text-[var(--primary-foreground)]">
        <MessageSquarePlus className="h-7 w-7" />
      </div>
      <h2 className="text-xl font-semibold">How can I help today?</h2>
      <p className="mt-1 max-w-md text-sm text-[var(--muted-foreground)]">
        Ask anything about your documents. Answers are grounded with citations you can verify.
      </p>
      <div className="mt-6 grid w-full max-w-lg grid-cols-1 gap-2 sm:grid-cols-2">
        {STARTERS.map((q) => (
          <button
            key={q}
            onClick={() => onPick(q)}
            className="rounded-lg border border-[var(--border)] p-3 text-left text-sm hover:bg-[var(--accent)]"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
