'use client';

import { AlertTriangle, RotateCcw } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AiSummaryError } from '@/types/domain/analysis';

/**
 * Why there is no AI summary, in the words a reader can act on.
 *
 * The single message this replaces -- "AI enrichment is not available. Click
 * Regenerate to retry." -- was true of a run that had not been enriched yet, a
 * run whose provider key was missing, a run that hit a rate limit, and a run
 * whose summary came back too short to be a summary. It also asked for a retry
 * in all four, including the ones where retrying cannot work.
 *
 * ## `suggested_action` decides, not a table of codes here
 *
 * The service already worked out what it wants a reader to do -- it classifies
 * into an `ErrorCategory` and pairs it with a `SuggestedAction`, and
 * `describe_summary_failure` puts that pair in this envelope. Inferring the
 * action a second time in the frontend means two places that disagree about what
 * `auth_failed` means, and the frontend's copy is the one a user reads.
 *
 * `add_key`, `check_key` and `switch_model` are addressed to whoever operates the
 * deployment. A reader of a report cannot add a key, so those get no button --
 * and get said so, because a card that reports a failure and offers no way to
 * act reads as a bug rather than as a decision.
 *
 * The code table is only the fallback for envelopes with no `suggested_action`,
 * which happens for a version skew between the two services. Its default is to
 * offer the retry: an unclassified failure is more likely to be a new provider
 * problem than a permanent configuration mistake.
 *
 * ## The message is the service's, not ours
 *
 * `message` is rendered in every case, including the ones with a tailored
 * headline. It is the only place the provider's own classification of the failure
 * reaches a human, and replacing it with our wording would throw away detail this
 * component cannot anticipate: a new `ErrorCategory` upstream arrives as a
 * readable sentence rather than as "unknown error".
 */
export interface AiSummaryErrorPanelProps {
  error: AiSummaryError;
  /** Rendered only when retrying could plausibly work. */
  onRetry?: () => void;
  isRetrying?: boolean;
  className?: string;
}

/** `SuggestedAction` values that mean "doing it again could work". */
const OFFERS_RETRY = new Set(['retry', 'wait']);

/**
 * Codes with no `suggested_action` attached that retrying cannot fix.
 *
 * Only consulted when the action is absent, and deliberately short: everything
 * else is assumed worth trying once, because a card that refuses to act is worse
 * than a card that asks.
 */
const TERMINAL_WITHOUT_HINT = new Set([
  'provider_not_configured',
  'auth_failed',
  'billing_exhausted',
]);

function retryIsWorthOffering(error: AiSummaryError): boolean {
  if (error.suggested_action) return OFFERS_RETRY.has(error.suggested_action);
  return !TERMINAL_WITHOUT_HINT.has(error.code);
}

export function AiSummaryErrorPanel({
  error,
  onRetry,
  isRetrying = false,
  className,
}: AiSummaryErrorPanelProps) {
  const retryable = retryIsWorthOffering(error);
  const canRetry = retryable && Boolean(onRetry);
  const serviceMessage = error.message?.trim();

  return (
    <div
      // `role="status"` rather than `alert`. This mounts once, on a page someone
      // has already navigated to, and announces the reason without stealing
      // focus -- which `alert` does, and which would be wrong for a card in a
      // sidebar the reader may be scrolled past.
      role="status"
      className={cn(
        'flex items-start gap-2 rounded-lg border border-[var(--color-error)]/25 bg-[var(--color-error)]/5 p-3',
        className,
      )}
    >
      {/* The word beside it carries the meaning; the icon is decoration on top. */}
      <AlertTriangle
        aria-hidden="true"
        className="w-4 h-4 shrink-0 mt-px text-[var(--color-error)]"
      />
      <div className="min-w-0 flex-1">
        <p className="text-[12px] font-medium text-foreground">
          {headlineFor(error.code)}
        </p>
        {serviceMessage && (
          <p className="text-[11px] text-text-secondary mt-1 break-words">
            {serviceMessage}
          </p>
        )}
        {/* Rendered whenever the provider gave a hint, and never as a bare
            number: `retry_after` is in seconds, and "retry_after: 30" shown to a
            reader is a unit error unless the unit is in the sentence. Absent when
            it is zero, which means "no hint" rather than "wait no time".
            Deliberately not gated on `canRetry`: the hint is information and the
            button is the action, and tying them means the advice disappears on a
            surface that happens not to pass `onRetry` -- which is a prop the
            reader cannot see, so the sentence vanishes for no visible reason. */}
        {typeof error.retry_after === 'number' && error.retry_after > 0 && (
          <p className="text-[11px] text-text-tertiary mt-1">
            {waitPhrase(error.retry_after)}
          </p>
        )}
        {canRetry && (
          <button
            onClick={onRetry}
            disabled={isRetrying}
            className="mt-2 flex items-center gap-1.5 px-2 py-1 rounded-md border border-border bg-card text-[11px] text-text-secondary hover:text-foreground hover:border-venom-yellow/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {/* A decorative glyph beside a real label, which changes to "Retrying..."
                while the spinner shows. Nothing for the icon to add, and an
                unlabelled graphic announced as "graphic" is noise. */}
            <RotateCcw
              aria-hidden="true"
              className={cn(
                'w-3 h-3',
                isRetrying && 'animate-spin motion-reduce:animate-none',
              )}
            />
            {isRetrying ? 'Retrying...' : 'Retry AI summary'}
          </button>
        )}
        {!retryable && onRetry && (
          // Said rather than left as an absent button: a reader told the run's
          // summary could not be produced, given no way to act, needs to know the
          // action was withheld on purpose.
          <p className="text-[11px] text-text-tertiary mt-2">
            Retrying will not help until this is fixed.
          </p>
        )}
      </div>
    </div>
  );
}

/**
 * Seconds as something a reader can wait for.
 *
 * Rounded up and coarsened to minutes above a minute, because "about 47 seconds"
 * is not a useful thing to read and stops being true the moment it is rendered.
 * Below a minute the seconds are kept, since that is the range where the number
 * is both short and worth knowing.
 */
function waitPhrase(seconds: number): string {
  if (seconds < 60) return `About ${Math.ceil(seconds)} seconds from now.`;
  const minutes = Math.ceil(seconds / 60);
  return `About ${minutes} minute${minutes > 1 ? 's' : ''} from now.`;
}

/**
 * The headline, per known code.
 *
 * Written rather than derived. `code` is a stable identifier and a sentence is
 * not, and any transformation between them produces text nobody chose. An
 * unrecognised code falls through to a neutral line rather than to the code
 * itself, because a raw `all_models_failed` read by a paying user looks like the
 * name of a setting they have wrong.
 *
 * Every value here is a member of the AI service's `ErrorCategory`, plus the two
 * this service produces itself for transport failures. A code with no entry is
 * a new category upstream, and `unknown` is the honest headline for it.
 */
function headlineFor(code: string): string {
  switch (code) {
    case 'rate_limited':
      return 'The AI service is busy';
    case 'timeout':
      return 'The AI summary took too long';
    case 'provider_unavailable':
      return 'The AI service is temporarily unavailable';
    case 'provider_unreachable':
      return 'The AI service could not be reached';
    case 'provider_not_configured':
      return 'AI summaries are not enabled';
    case 'auth_failed':
      return 'The AI service rejected our credentials';
    case 'billing_exhausted':
      return 'The AI service account has run out of credit';
    case 'context_overflow':
      return 'The summary was too large to process';
    case 'all_models_failed':
      return 'No AI model could produce a summary';
    case 'unknown':
    default:
      return 'No AI summary was produced';
  }
}
