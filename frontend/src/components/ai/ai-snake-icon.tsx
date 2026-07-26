'use client';

/**
 * Minimal flat-vector snake logo in solid #FACC15.
 * Accepts isAnimating to enable pulse glow while thinking/streaming.
 * Shows a greeting tooltip on hover.
 */

export function SnakeIcon({
  className = '',
  isAnimating = false,
}: {
  className?: string;
  isAnimating?: boolean;
}) {
  return (
    <span className="group/krait relative inline-flex shrink-0">
      <svg
        width={24}
        height={24}
        viewBox="0 0 18 18"
        fill="none"
        className={`shrink-0 ${isAnimating ? 'krait-pulse' : ''} ${className}`}
        aria-hidden="true"
      >
        {/* Sinuous snake body — two smooth curves */}
        <path
          d="M3 9c0-2 1.5-3.5 3-3.5s3 1.5 3 3.5-1.5 3.5-3 3.5c-1 0-1.5-.5-1.5-1.5 0-1 1-1.5 2-1.5s2 .5 2 1.5"
          stroke="#FACC15"
          strokeWidth="1.6"
          strokeLinecap="round"
          fill="none"
        />
        {/* Tail tuck */}
        <path
          d="M11 10c1-.5 2.5-.2 3.5.8"
          stroke="#FACC15"
          strokeWidth="1.6"
          strokeLinecap="round"
          fill="none"
        />
        {/* Head */}
        <circle cx="3.5" cy="9" r="1.2" fill="#FACC15" />
        {/* Antenna / highlight */}
        <line x1="3.5" y1="7.5" x2="4.8" y2="6.2" stroke="#FACC15" strokeWidth="1" strokeLinecap="round" />
      </svg>

      {/* Hover tooltip */}
      <span className="pointer-events-none absolute left-full ml-2 top-1/2 -translate-y-1/2 whitespace-nowrap rounded-lg border border-krait-border bg-krait-obsidian px-3 py-1.5 text-[12px] text-text-secondary opacity-0 shadow-md transition-opacity duration-200 group-hover/krait:opacity-100 z-50">
        <em>Hi, I&apos;m Krait. How can I help you today?</em>
      </span>
    </span>
  );
}
