export function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-1 py-2" aria-label="Assistant is typing">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="typing-dot h-2 w-2 rounded-full bg-[var(--muted-foreground)]"
          style={{ animationDelay: `${i * 0.2}s` }}
        />
      ))}
    </div>
  );
}
