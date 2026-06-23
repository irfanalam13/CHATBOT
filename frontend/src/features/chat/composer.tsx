"use client";

import * as React from "react";
import { ArrowUp, Paperclip, Sparkles, Square } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const QUICK_ACTIONS = [
  "Summarize this",
  "Explain in simple terms",
  "What are the key risks?",
  "Draft an email about this",
];

const AI_COMMANDS = ["/summarize", "/translate", "/table", "/explain"];

export function Composer({
  onSend,
  onStop,
  streaming,
  showSuggestions,
}: {
  onSend: (text: string) => void;
  onStop: () => void;
  streaming: boolean;
  showSuggestions?: boolean;
}) {
  const [value, setValue] = React.useState("");
  const [showCommands, setShowCommands] = React.useState(false);
  const ref = React.useRef<HTMLTextAreaElement>(null);

  const autosize = () => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  const submit = () => {
    const text = value.trim();
    if (!text || streaming) return;
    onSend(text);
    setValue("");
    requestAnimationFrame(() => {
      if (ref.current) ref.current.style.height = "auto";
    });
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="space-y-2">
      {showSuggestions && !value && (
        <div className="flex flex-wrap gap-2">
          {QUICK_ACTIONS.map((q) => (
            <button
              key={q}
              onClick={() => onSend(q)}
              className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] px-3 py-1 text-xs hover:bg-[var(--accent)]"
            >
              <Sparkles className="h-3 w-3" /> {q}
            </button>
          ))}
        </div>
      )}

      <div className="relative rounded-2xl border border-[var(--border)] bg-[var(--card)] p-2 shadow-sm focus-within:ring-2 focus-within:ring-[var(--ring)]">
        {showCommands && (
          <div className="absolute bottom-full mb-2 w-56 rounded-lg border border-[var(--border)] bg-[var(--popover)] p-1 shadow-lg">
            {AI_COMMANDS.map((c) => (
              <button
                key={c}
                onClick={() => {
                  setValue(c + " ");
                  setShowCommands(false);
                  ref.current?.focus();
                }}
                className="block w-full rounded px-2 py-1 text-left text-sm hover:bg-[var(--accent)]"
              >
                {c}
              </button>
            ))}
          </div>
        )}
        <div className="flex items-end gap-2">
          <Button
            variant="ghost"
            size="icon"
            type="button"
            aria-label="AI commands"
            onClick={() => setShowCommands((s) => !s)}
          >
            <Paperclip className="h-4 w-4" />
          </Button>
          <textarea
            ref={ref}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              autosize();
              setShowCommands(e.target.value === "/");
            }}
            onKeyDown={onKeyDown}
            rows={1}
            placeholder="Message the assistant…  (Enter to send, Shift+Enter for newline)"
            aria-label="Message input"
            className="max-h-[200px] flex-1 resize-none bg-transparent px-1 py-2 text-sm outline-none placeholder:text-[var(--muted-foreground)]"
          />
          {streaming ? (
            <Button size="icon" variant="destructive" onClick={onStop} aria-label="Stop">
              <Square className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              size="icon"
              onClick={submit}
              disabled={!value.trim()}
              aria-label="Send message"
              className={cn(!value.trim() && "opacity-50")}
            >
              <ArrowUp className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
      <p className="text-center text-[10px] text-[var(--muted-foreground)]">
        Responses are AI-generated and grounded in your knowledge base. Verify important
        information.
      </p>
    </div>
  );
}
