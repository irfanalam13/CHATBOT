// SSE streaming client for POST /api/v1/chat/completions.
// (The backend exposes SSE + native WebSocket rather than Socket.IO; this
//  reads the SSE body incrementally and parses `data: {json}` frames.)
import { tokenStore } from "./storage";
import type { ChatStreamEvent } from "./types";

export interface ChatStreamBody {
  message: string;
  session_id?: string;
  knowledge_base_id?: string;
  use_rag?: boolean;
  use_tools?: boolean;
  stream?: boolean;
}

export async function* streamChat(
  body: ChatStreamBody,
  signal?: AbortSignal,
): AsyncGenerator<ChatStreamEvent> {
  const res = await fetch("/api/v1/chat/completions", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${tokenStore.access ?? ""}`,
    },
    body: JSON.stringify({ stream: true, use_rag: true, use_tools: true, ...body }),
    signal,
  });

  if (!res.ok || !res.body) {
    yield { type: "error", message: `Request failed (${res.status})` };
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 2);
      if (!frame.startsWith("data:")) continue;
      const json = frame.slice(5).trim();
      if (!json) continue;
      try {
        yield JSON.parse(json) as ChatStreamEvent;
      } catch {
        /* ignore malformed frame */
      }
    }
  }
}

// Native WebSocket alternative (parity with the backend /chat/ws endpoint).
export function openChatSocket(
  onEvent: (e: ChatStreamEvent) => void,
): { send: (b: ChatStreamBody) => void; close: () => void } {
  const origin = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
  const ws = new WebSocket(`${origin}/api/v1/chat/ws?token=${tokenStore.access ?? ""}`);
  ws.onmessage = (m) => {
    try {
      onEvent(JSON.parse(m.data) as ChatStreamEvent);
    } catch {
      /* ignore */
    }
  };
  return {
    send: (b) => ws.readyState === WebSocket.OPEN && ws.send(JSON.stringify(b)),
    close: () => ws.close(),
  };
}
