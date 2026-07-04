'use client';

/**
 * Minimal flat-vector snake logo in solid #FACC15.
 * Single color, no background, no gradients, no animations.
 * Sits inline beside text — no container, no glow, no border.
 */

export function SnakeIcon({ className = '' }: { className?: string }) {
  return (
    <svg
      width={24}
      height={24}
      viewBox="0 0 18 18"
      fill="none"
      className={`shrink-0 ${className}`}
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
  );
}
