/**
 * Sentry — server-side (SSR, route handlers, API routes) error reporting.
 *
 * Pairs with sentry.client.config.ts. Inactive unless SENTRY_DSN is set, so
 * local and CI builds need no Sentry account.
 */
import * as Sentry from '@sentry/nextjs';

const dsn = process.env.SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_APP_ENV ?? 'development',
    enabled: true,
    // PII is off by default in Sentry v11 — see sentry.client.config.ts.
    tracesSampleRate: 0.1,
  });
}
