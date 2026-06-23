"use client";

import * as React from "react";
import {
  Archive,
  MessageSquare,
  MoreHorizontal,
  Pin,
  PinOff,
  Plus,
  Search,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/misc";
import { cn } from "@/lib/utils";
import type { ChatSession } from "@/lib/types";
import { useChatStore } from "@/stores/chat-store";
import { useSessionMutations, useSessions } from "@/features/chat/use-chat";

type Filter = "active" | "pinned" | "archived";

export function ChatSidebar() {
  const [q, setQ] = React.useState("");
  const [filter, setFilter] = React.useState<Filter>("active");
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const setActiveSession = useChatStore((s) => s.setActiveSession);

  const params = new URLSearchParams({ page_size: "100" });
  if (filter === "pinned") params.set("pinned", "true");
  if (filter === "archived") params.set("status", "archived");
  if (q) params.set("q", q);
  const { data, isLoading } = useSessions(`?${params.toString()}`);
  const { pin, archive, remove, rename } = useSessionMutations();

  const sessions = data?.items ?? [];
  const pinned = sessions.filter((s) => s.pinned);
  const rest = sessions.filter((s) => !s.pinned);

  return (
    <div className="flex h-full flex-col">
      <div className="p-3">
        <Button
          className="w-full justify-start gap-2"
          onClick={() => setActiveSession(null)}
        >
          <Plus className="h-4 w-4" /> New chat
        </Button>
      </div>

      <div className="px-3 pb-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-[var(--muted-foreground)]" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search chats"
            className="pl-8"
            aria-label="Search chats"
          />
        </div>
        <div className="mt-2 flex gap-1">
          {(["active", "pinned", "archived"] as Filter[]).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                "flex-1 rounded-md px-2 py-1 text-xs capitalize",
                filter === f
                  ? "bg-[var(--secondary)] text-[var(--secondary-foreground)]"
                  : "text-[var(--muted-foreground)] hover:bg-[var(--accent)]",
              )}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-3 scrollbar-thin">
        {isLoading ? (
          <div className="flex justify-center py-6 text-[var(--muted-foreground)]">
            <Spinner />
          </div>
        ) : sessions.length === 0 ? (
          <p className="px-2 py-6 text-center text-xs text-[var(--muted-foreground)]">
            No conversations yet.
          </p>
        ) : (
          <>
            {pinned.length > 0 && filter === "active" && (
              <Group label="Pinned">
                {pinned.map((s) => (
                  <SessionRow
                    key={s.id}
                    session={s}
                    active={s.id === activeSessionId}
                    onOpen={() => setActiveSession(s.id)}
                    onPin={() => pin.mutate({ id: s.id, pinned: !s.pinned })}
                    onArchive={() => archive.mutate(s.id)}
                    onDelete={() => remove.mutate(s.id)}
                    onRename={(t) => rename.mutate({ id: s.id, title: t })}
                  />
                ))}
              </Group>
            )}
            <Group label={filter === "active" ? "Recent" : ""}>
              {(filter === "active" ? rest : sessions).map((s) => (
                <SessionRow
                  key={s.id}
                  session={s}
                  active={s.id === activeSessionId}
                  onOpen={() => setActiveSession(s.id)}
                  onPin={() => pin.mutate({ id: s.id, pinned: !s.pinned })}
                  onArchive={() => archive.mutate(s.id)}
                  onDelete={() => remove.mutate(s.id)}
                  onRename={(t) => rename.mutate({ id: s.id, title: t })}
                />
              ))}
            </Group>
          </>
        )}
      </div>
    </div>
  );
}

function Group({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-2">
      {label && (
        <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">
          {label}
        </p>
      )}
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

function SessionRow({
  session,
  active,
  onOpen,
  onPin,
  onArchive,
  onDelete,
  onRename,
}: {
  session: ChatSession;
  active: boolean;
  onOpen: () => void;
  onPin: () => void;
  onArchive: () => void;
  onDelete: () => void;
  onRename: (title: string) => void;
}) {
  const [menu, setMenu] = React.useState(false);

  return (
    <div
      className={cn(
        "group relative flex items-center gap-2 rounded-md px-2 py-2 text-sm",
        active ? "bg-[var(--accent)] text-[var(--accent-foreground)]" : "hover:bg-[var(--accent)]",
      )}
    >
      <button onClick={onOpen} className="flex min-w-0 flex-1 items-center gap-2 text-left">
        <MessageSquare className="h-4 w-4 shrink-0 text-[var(--muted-foreground)]" />
        <span className="truncate">{session.title}</span>
        {session.pinned && <Pin className="h-3 w-3 shrink-0 text-[var(--primary)]" />}
      </button>
      <button
        onClick={() => setMenu((m) => !m)}
        aria-label="Chat options"
        className="opacity-0 transition-opacity group-hover:opacity-100"
      >
        <MoreHorizontal className="h-4 w-4" />
      </button>

      {menu && (
        <div
          className="absolute right-2 top-9 z-20 w-40 rounded-lg border border-[var(--border)] bg-[var(--popover)] p-1 text-sm shadow-lg"
          onMouseLeave={() => setMenu(false)}
        >
          <MenuItem
            onClick={() => {
              const t = prompt("Rename chat", session.title);
              if (t) onRename(t);
              setMenu(false);
            }}
          >
            <MessageSquare className="h-3.5 w-3.5" /> Rename
          </MenuItem>
          <MenuItem onClick={() => { onPin(); setMenu(false); }}>
            {session.pinned ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
            {session.pinned ? "Unpin" : "Pin"}
          </MenuItem>
          <MenuItem onClick={() => { onArchive(); setMenu(false); }}>
            <Archive className="h-3.5 w-3.5" /> Archive
          </MenuItem>
          <MenuItem destructive onClick={() => { onDelete(); setMenu(false); }}>
            <Trash2 className="h-3.5 w-3.5" /> Delete
          </MenuItem>
        </div>
      )}
    </div>
  );
}

function MenuItem({
  children,
  onClick,
  destructive,
}: {
  children: React.ReactNode;
  onClick: () => void;
  destructive?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2 rounded px-2 py-1.5 text-left hover:bg-[var(--accent)]",
        destructive && "text-[var(--destructive)]",
      )}
    >
      {children}
    </button>
  );
}
