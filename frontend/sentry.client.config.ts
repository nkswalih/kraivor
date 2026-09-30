/**
 * Sentry — browser/runtime error reporting for the Next.js frontend.
 *
 * Previously the frontend reported errors nowhere: `core` had Sentry wired and
 * `auth` had it commented out, so a crash in the browser was invisible.
 *
 * Inactive unless NEXT_PUBLIC_SENTRY_DSN is set. The build never fails on a
 * missing DSN, so local and CI work without any Sentry account.
 */
import * as Sentry from '@sentry/nextjs';

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_APP_ENV ?? 'development',
    enabled: true,

    // PII: Sentry v11 no longer has sendDefaultPii — the default flipped to
    // NOT sending user data. Do not re-add it; this app renders authenticated
    // workspace content that must not reach a third-party tracker.

    // Session Replay records DOM. Off until someone explicitly reviews what it
    // captures, since this app renders authenticated workspace content.
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 0,

    // Keep the signal-to-noise ratio usable: noise drowns real regressions.
    tracesSampleRate: 0.1,

    // Drop cross-origin errors we cannot resolve to our code.
    ignoreErrors: [
      // Fired by ad blockers and privacy extensions; not our bug.
      'ResizeObserver loop limit exceeded',
      'ResizeObserver loop completed with undelivered notifications',
      /^ResizeObserver/,
      // Network noise the browser logs on failed third-party calls.
      'NetworkError when attempting to fetch resource.',
      'Load failed',
      'Failed to fetch',
    ],

    beforeSend(event) {
      // Strip query strings — they can carry tokens on some auth redirects.
      if (event.request?.url) {
        try {
          const url = new URL(event.request.url);
          url.search = '';
          event.request.url = url.toString();
        } catch {
          // leave the original URL rather than dropping the event
        }
      }
      return event;
    },
  });
}
