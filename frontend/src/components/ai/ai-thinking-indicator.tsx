'use client';

import { SnakeIcon } from '@/components/ai/ai-snake-icon';

/**
 * Minimal thinking indicator.
 *
 * Layout:
 *   [ SnakeIcon ] <status>
 *
 * - Icon is flat, solid yellow, no background, no animation.
 * - Status text updates dynamically based on pipeline stage.
 * - Dots animate (sequential fade) after the status text.
 * - Transparent background, no card, no borders, no separators.
 * - Exit transition 120ms for smooth handoff to streamed content.
 */

const DOTS = [0, 1, 2];

export function ThinkingIndicator({ status }: { status?: string }) {
  const text = status || 'Thinking';

  return (
    <div className="flex items-center gap-2 py-1 select-none animate-fade-up">
      <SnakeIcon />

      <span className="text-[14px] font-medium text-yellow-300 ai-think-shimmer leading-none">
        {text}
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
