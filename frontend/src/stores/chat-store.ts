import { create } from "zustand";

import { streamChat, type ChatStreamBody } from "@/lib/chat-stream";
import type { StreamCitation } from "@/lib/types";

interface ToolEvent {
  name: string;
  status: "calling" | "done";
}

interface ChatState {
  activeSessionId: string | null;
  streaming: boolean;
  // Live assistant draft while a response streams in.
  draftContent: string;
  draftCitations: StreamCitation[];
  toolEvents: ToolEvent[];
  warning: string | null;
  error: string | null;
  abort: AbortController | null;

  setActiveSession: (id: string | null) => void;
  send: (
    body: ChatStreamBody,
    callbacks?: { onSession?: (id: string, title: string) => void; onDone?: () => void },
  ) => Promise<void>;
  stop: () => void;
  reset: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  activeSessionId: null,
  streaming: false,
  draftContent: "",
  draftCitations: [],
  toolEvents: [],
  warning: null,
  error: null,
  abort: null,

  setActiveSession: (id) =>
    set({ activeSessionId: id, draftContent: "", draftCitations: [], toolEvents: [], error: null }),

  async send(body, callbacks) {
    const controller = new AbortController();
    set({
      streaming: true, draftContent: "", draftCitations: [], toolEvents: [],
      warning: null, error: null, abort: controller,
    });

    try {
      for await (const ev of streamChat(body, controller.signal)) {
        switch (ev.type) {
          case "session":
            set({ activeSessionId: ev.session_id });
            callbacks?.onSession?.(ev.session_id, ev.title);
            break;
          case "citations":
            set({ draftCitations: ev.citations });
            break;
          case "token":
            set((s) => ({ draftContent: s.draftContent + ev.text }));
            break;
          case "tool_call":
            set((s) => ({ toolEvents: [...s.toolEvents, { name: ev.name, status: "calling" }] }));
            break;
          case "tool_result":
            set((s) => ({
              toolEvents: s.toolEvents.map((t) =>
                t.name === ev.name ? { ...t, status: "done" } : t,
              ),
            }));
            break;
          case "warning":
            set({ warning: ev.message });
            break;
          case "error":
            set({ error: ev.message });
            break;
          case "done":
            callbacks?.onDone?.();
            break;
        }
      }
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        set({ error: (e as Error).message });
      }
    } finally {
      set({ streaming: false, abort: null });
    }
  },

  stop() {
    get().abort?.abort();
    set({ streaming: false });
  },

  reset: () =>
    set({ draftContent: "", draftCitations: [], toolEvents: [], warning: null, error: null }),
}));
