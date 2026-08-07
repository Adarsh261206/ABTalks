export function Logo({ size = 28 }: { size?: number }) {
  return (
    <span
      className="inline-flex items-center justify-center rounded-xl bg-gradient-to-br from-aurora-500 via-aurora-600 to-ink-700 shadow-[0_4px_16px_-4px_rgba(14,165,233,0.5)]"
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <svg viewBox="0 0 24 24" width={size * 0.55} height={size * 0.55} fill="none">
        <path
          d="M5 7.5C5 6.12 6.12 5 7.5 5h9C17.88 5 19 6.12 19 7.5v5c0 1.38-1.12 2.5-2.5 2.5h-4.6l-3.4 3.6c-.5.53-1.4.18-1.4-.55V15.7A2.5 2.5 0 0 1 5 13.2v-5.7Z"
          stroke="white"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  );
}
