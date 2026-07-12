'use client';

import { SnakeIcon } from '@/components/features/ai-snake-icon';

/**
 * Minimal thinking indicator.
 *
 * Layout:
 *   [ SnakeIcon ] Thinking…
 *
 * - Icon is flat, solid yellow, no background, no animation.
 * - "Thinking" stays fixed; only the three dots animate (sequential fade).
 * - Subtle gold shimmer sweeps left→right across "Thinking" (2s loop).
 * - Transparent background, no card, no borders, no separators.
 * - Exit transition 120ms for smooth handoff to streamed content.
 */

const DOTS = [0, 1, 2];

export function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2 py-1 select-none animate-fade-up">
      <SnakeIcon />

      <span className="text-[14px] font-medium text-yellow-300 ai-think-shimmer leading-none">
        Thinking
      </span>

      <span className="inline-flex items-center leading-none">
        {DOTS.map(i => (
          <span
            key={i}
            className="ai-dot text-[14px] font-medium leading-none"
            style={{
              color: 'rgba(250, 204, 21, 0.7)',
              animationDelay: `${i * 0.4}s`,
            }}
          >
            .
          </span>
        ))}
      </span>
    </div>
  );
}
