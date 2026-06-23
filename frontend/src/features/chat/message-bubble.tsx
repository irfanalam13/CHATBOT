"use client";

import * as React from "react";
import {
  Bookmark,
  Check,
  Copy,
  RefreshCw,
  Share2,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import { toast } from "sonner";

import { Markdown } from "@/components/markdown/markdown";
import { Avatar } from "@/components/ui/misc";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Message } from "@/lib/types";
import { Citations } from "./citations";

function IconBtn({
  label,
  active,
  onClick,
  children,
}: {
  label: string;
  active?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      title={label}
      className={cn(
        "rounded p-1.5 text-[var(--muted-foreground)] transition-colors hover:bg-[var(--accent)] hover:text-[var(--foreground)]",
        active && "text-[var(--primary)]",
      )}
    >
      {children}
    </button>
  );
}

export function MessageBubble({
  message,
  onRegenerate,
}: {
  message: Message;
  onRegenerate?: () => void;
}) {
  const isUser = message.role === "user";
  const [copied, setCopied] = React.useState(false);
  const [reaction, setReaction] = React.useState(message.reaction);
  const [bookmarked, setBookmarked] = React.useState(
    Boolean((message as { metadata?: { bookmarked?: boolean } }).metadata?.bookmarked),
  );

  const copy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const react = async (value: "👍" | "👎") => {
    const next = reaction === value ? null : value;
    setReaction(next);
    await api.react(message.id, next).catch(() => undefined);
    if (next) {
      await api
        .submitFeedback({
          message_id: message.id,
          feedback_type: value === "👍" ? "thumbs_up" : "thumbs_down",
        })
        .catch(() => undefined);
    }
  };

  const share = async () => {
    const text = message.content;
    if (navigator.share) {
      await navigator.share({ text }).catch(() => undefined);
    } else {
      await navigator.clipboard.writeText(text);
      toast.success("Message copied to clipboard");
    }
  };

  return (
    <div className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
      <Avatar name={isUser ? "You" : "AI"} className={isUser ? "" : "bg-[var(--accent)] text-[var(--accent-foreground)]"} />
      <div className={cn("group max-w-[min(80%,720px)]", isUser && "items-end")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-sm",
            isUser
              ? "rounded-tr-sm bg-[var(--primary)] text-[var(--primary-foreground)]"
              : "rounded-tl-sm bg-[var(--card)] border border-[var(--border)]",
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          ) : (
            <Markdown content={message.content} />
          )}
          {!isUser && message.citations?.length > 0 && (
            <Citations citations={message.citations} />
          )}
        </div>

        {!isUser && (
          <div className="mt-1 flex items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
            <IconBtn label="Copy" onClick={copy}>
              {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            </IconBtn>
            {onRegenerate && (
              <IconBtn label="Regenerate" onClick={onRegenerate}>
                <RefreshCw className="h-3.5 w-3.5" />
              </IconBtn>
            )}
            <IconBtn label="Good response" active={reaction === "👍"} onClick={() => react("👍")}>
              <ThumbsUp className="h-3.5 w-3.5" />
            </IconBtn>
            <IconBtn label="Bad response" active={reaction === "👎"} onClick={() => react("👎")}>
              <ThumbsDown className="h-3.5 w-3.5" />
            </IconBtn>
            <IconBtn label="Bookmark" active={bookmarked} onClick={() => setBookmarked((b) => !b)}>
              <Bookmark className="h-3.5 w-3.5" />
            </IconBtn>
            <IconBtn label="Share" onClick={share}>
              <Share2 className="h-3.5 w-3.5" />
            </IconBtn>
            {message.model && (
              <span className="ml-1 text-[10px] text-[var(--muted-foreground)]">{message.model}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
