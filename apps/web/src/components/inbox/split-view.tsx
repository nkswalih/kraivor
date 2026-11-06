'use client';

import type { ReactNode } from 'react';
import { ChevronLeft } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SplitViewProps {
  list: ReactNode;
  detail: ReactNode;
  /** True once a row is chosen, which is what flips the mobile layout. */
  hasSelection: boolean;
  onBack: () => void;
}

/**
 * The list-beside-detail shape three of the five inbox sections use.
 *
 * It exists because those sections were written for a fixed-width page: a
 * 360px pane, a 280px pane, and a detail column that assumed there was always
 * room for both. Inside a dialog that has to fit a 360px phone, that layout
 * has nowhere to go -- two columns of 360 and 280 do not fit, and squeezing
 * them turns every row into a truncate.
 *
 * So the breakpoint does the work in CSS, with no JS media query and no
 * layout measurement:
 *
 *  - `sm` and up: both panes side by side, list pinned to its width;
 *  - below `sm`: exactly one pane at a time. No selection shows the list;
 *    selecting swaps in the detail with a Back bar, which is the Discord /
 *    Slack / Linear convention on a phone.
 *
 * Because it is all class swapping, the flip is instant and cannot desync
 * from a resize the way a `matchMedia` listener would.
 */
export function SplitView({ list, detail, hasSelection, onBack }: SplitViewProps) {
  return (
    <div className="flex flex-1 min-h-0 min-w-0 flex-col sm:flex-row">
      <div
        className={cn(
          'min-h-0 flex-1 w-full overflow-y-auto overscroll-contain',
          'border-b border-[#27272A] sm:flex-none sm:w-[320px] sm:shrink-0 sm:border-b-0 sm:border-r',
          hasSelection && 'hidden sm:block'
        )}
      >
        {list}
      </div>

      <div
        className={cn(
          'min-h-0 flex-1 min-w-0 flex-col overflow-hidden',
          hasSelection ? 'flex' : 'hidden',
          'sm:flex'
        )}
      >
        {hasSelection && (
          <div className="sm:hidden shrink-0 border-b border-[#27272A] px-2 py-1.5">
            <button
              type="button"
              onClick={onBack}
              className="flex items-center gap-1 px-2 py-1 rounded-[6px] text-[13px] text-[#A1A1AA] hover:text-[#FAFAFA] hover:bg-[#18181B] transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              Back
            </button>
          </div>
        )}
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">{detail}</div>
      </div>
    </div>
  );
}
