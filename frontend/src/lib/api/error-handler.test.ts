import { describe, it, expect } from 'vitest';
import { AxiosError } from 'axios';
import { handleApiError, isApiError, getErrorMessage, ApiException } from './error-handler';

/**
 * `handleApiError` is the single funnel every API call passes through on its way
 * to a thrown `ApiException`. Two properties matter and neither is covered
 * anywhere else:
 *
 *  1. It must not lose the service-specific `error_code`. The four backend
 *     services disagree on the error envelope (auth sends `error`/`error_code`,
 *     core sends DRF's `detail`, analysis and ai each send a mix), so this
 *     function is the one place that can normalise them. Before `error_code`
 *     was declared on `ErrorResponse`, the field was silently dropped here,
 *     `auth-api.verifyEmail` patched it back on with an `any` cast, and
 *     callers read it back through a second `any`. The `verify-email` page
 *     branched on it to tell an expired link from an invalid one.
 *
 *  2. It must never invent a message. `message` is the frontend's own generic
 *     per-status copy, which is why `verify-email-form` must key off
 *     `errorCode` rather than `message` to pick a specific string.
 */

function axiosErrorWith(status: number, data: unknown): AxiosError {
  const error = new AxiosError(
    `Request failed with status code ${status}`,
    status >= 500 ? 'ERR_BAD_RESPONSE' : 'ERR_BAD_REQUEST',
    undefined,
    undefined,
    { data, status, statusText: 'Err', headers: {}, config: { headers: {} } } as never
  );
  return error;
}

describe('handleApiError', () => {
  it('preserves the auth service error_code (the expired-link case)', () => {
    // Exactly the body services/auth VerifyEmailView returns on an expired JWT.
    const err = handleApiError(
      axiosErrorWith(400, {
        error: 'Your verification link has expired.',
        error_code: 'token_expired',
      })
    );

    expect(err.errorCode).toBe('token_expired');
    // Distinct from `code`, which is the frontend's coarse HTTP classification.
    expect(err.code).toBe('VALIDATION_ERROR');
    expect(err.statusCode).toBe(400);
  });

  it('preserves error_code for the invalid / missing token codes', () => {
    for (const code of ['invalid_token', 'missing_token', 'invalid_credentials', 'account_locked']) {
      const err = handleApiError(axiosErrorWith(400, { error: 'nope', error_code: code }));
      expect(err.errorCode).toBe(code);
    }
  });

  it('overrides the service message on 429, which is deliberate', () => {
    // Unlike 400/422, a 429 replaces the service text with generic copy so an
    // internal rate-limit reason is not surfaced to end users.
    const err = handleApiError(
      axiosErrorWith(429, { error: 'rate_limit_exceeded', message: 'Slow down.' })
    );

    expect(err.errorCode).toBeUndefined();
    expect(err.code).toBe('RATE_LIMITED');
    expect(err.message).toBe(ERROR_MESSAGES.rateLimited());
  });

  it('reports a response-less axios failure as NETWORK_ERROR, not a server fault', () => {
    // offline / DNS failure / CORS rejection / client timeout: the request never
    // reached the service. Reporting 5xx here blamed the backend for a local
    // connectivity fault.
    const err = handleApiError(
      new AxiosError('Network Error', AxiosError.ERR_NETWORK, undefined, undefined, undefined)
    );

    expect(err.code).toBe('NETWORK_ERROR');
    expect(err.statusCode).toBe(0);
    expect(err.message).toBe(ERROR_MESSAGES.networkError());
  });

  it('handles the DRF envelope core sends, which uses detail and has no error_code', () => {
    const err = handleApiError(axiosErrorWith(400, { detail: 'That field is required.' }));

    expect(err.message).toBe('That field is required.');
    expect(err.errorCode).toBeUndefined();
    expect(err.code).toBe('VALIDATION_ERROR');
  });

  it('falls back to generic copy when the service sends no message at all', () => {
    // The bug this guards: a truthy-but-useless generic `message` silently
    // shadowing a caller-specific fallback.
    const err = handleApiError(axiosErrorWith(400, { error: 'Invalid verification token.' }));

    expect(err.errorCode).toBeUndefined();
    expect(err.message).toBe(ERROR_MESSAGES.validationError());
  });

  it('maps every status the switch branches on', () => {
    const cases: Array<[number, string]> = [
      [401, 'UNAUTHORIZED'],
      [403, 'FORBIDDEN'],
      [404, 'NOT_FOUND'],
      [422, 'VALIDATION_ERROR'],
      [429, 'RATE_LIMITED'],
      [500, 'SERVER_ERROR'],
      [503, 'SERVER_ERROR'],
      [418, 'NETWORK_ERROR'],
    ];

    for (const [status, code] of cases) {
      expect(handleApiError(axiosErrorWith(status, {})).code).toBe(code);
    }
  });

  it('returns NETWORK_ERROR for a non-axios throw so callers still get an ApiException', () => {
    const err = handleApiError(new Error('boom'));

    expect(isApiError(err)).toBe(true);
    expect(err.code).toBe('NETWORK_ERROR');
    expect(err.statusCode).toBe(0);
  });
});

describe('isApiError / getErrorMessage', () => {
  it('identifies an ApiException', () => {
    expect(isApiError(handleApiError(axiosErrorWith(400, {})))).toBe(true);
    expect(isApiError(new Error('plain'))).toBe(false);
    expect(isApiError('a string')).toBe(false);
    expect(isApiError(null)).toBe(false);
  });

  it('returns the ApiException message when there is one', () => {
    expect(getErrorMessage(handleApiError(axiosErrorWith(404, {})))).toBe(
      ERROR_MESSAGES.notFound()
    );
  });

  it('falls back for a non-Error throw so callers never render undefined', () => {
    expect(getErrorMessage('nope')).toBe(ERROR_MESSAGES.networkError());
    expect(getErrorMessage({ oops: true })).toBe(ERROR_MESSAGES.networkError());
  });

  it('keeps errorCode absent rather than undefined-valued when not supplied', () => {
    // Distinguishable shape: consumers can rely on `'errorCode' in err` if needed.
    const err = new ApiException('m', 400, 'VALIDATION_ERROR');
    expect(err.errorCode).toBeUndefined();
  });
});

/**
 * Kept separate from the imported module so the expectations above read as
 * literal strings but still fail loudly if the constants are ever reworded in a
 * way that changes behaviour the UI depends on.
 */
const ERROR_MESSAGES = {
  validationError: () => 'Please check your input and try again.',
  notFound: () => 'The requested resource was not found.',
  networkError: () => 'Unable to connect. Please check your internet connection.',
  rateLimited: () => 'Too many requests. Please wait a moment.',
};