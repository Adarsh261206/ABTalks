export function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1 px-1" aria-label="VIVA is typing">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-zinc-500 animate-typing"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </span>
  );
}
