import { ChatSidebar } from "@/features/sidebar/chat-sidebar";
import { ChatWindow } from "@/features/chat/chat-window";

export default function ChatPage() {
  return (
    <div className="flex h-full">
      <aside className="hidden w-72 shrink-0 border-r border-[var(--border)] bg-[var(--card)] md:block">
        <ChatSidebar />
      </aside>
      <div className="min-w-0 flex-1">
        <ChatWindow />
      </div>
    </div>
  );
}
