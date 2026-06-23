"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ChatStreamBody } from "@/lib/chat-stream";
import { useChatStore } from "@/stores/chat-store";

export function useSessions(params = "") {
  return useQuery({
    queryKey: ["sessions", params],
    queryFn: () => api.sessions(params),
  });
}

export function useSessionMessages(sessionId: string | null) {
  return useQuery({
    queryKey: ["messages", sessionId],
    queryFn: () => api.sessionMessages(sessionId!),
    enabled: Boolean(sessionId),
  });
}

export function useSendMessage(knowledgeBaseId?: string) {
  const qc = useQueryClient();
  const send = useChatStore((s) => s.send);
  const activeSessionId = useChatStore((s) => s.activeSessionId);

  return async (message: string, opts?: Partial<ChatStreamBody>) => {
    await send(
      {
        message,
        session_id: activeSessionId ?? undefined,
        knowledge_base_id: knowledgeBaseId,
        ...opts,
      },
      {
        onSession: () => qc.invalidateQueries({ queryKey: ["sessions"] }),
        onDone: () => {
          const sid = useChatStore.getState().activeSessionId;
          qc.invalidateQueries({ queryKey: ["messages", sid] });
          qc.invalidateQueries({ queryKey: ["sessions"] });
        },
      },
    );
  };
}

export function useSessionMutations() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ["sessions"] });

  const rename = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      api.updateSession(id, { title }),
    onSuccess: invalidate,
  });
  const pin = useMutation({
    mutationFn: ({ id, pinned }: { id: string; pinned: boolean }) =>
      api.updateSession(id, { pinned }),
    onSuccess: invalidate,
  });
  const archive = useMutation({
    mutationFn: (id: string) => api.updateSession(id, { status: "archived" }),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.deleteSession(id),
    onSuccess: invalidate,
  });
  return { rename, pin, archive, remove };
}
