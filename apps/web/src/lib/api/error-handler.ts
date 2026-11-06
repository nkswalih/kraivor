import { isAxiosError, type AxiosError } from 'axios';
import { HTTP_STATUS, ERROR_MESSAGES } from '@/constants';
import type { ApiErrorCode } from '@/types/api';

/**
 * The union of error bodies the backend services actually return.
 *
 * The four services do not agree on a shape, so every field is optional:
 *   auth      { error, error_code }
 *   core      { detail }                     (DRF)
 *   analysis  { detail, error_code } | { error, message, details }
 *   ai        { error, message }
 *
 * `error_code` used to be missing here, which meant `handleApiError` threw it
 * away; `auth-api.verifyEmail` patched it back on with an `any` cast, and
 * callers had to read it back through another `any`. Declare the field the
 * services send and the cast is no longer needed anywhere.
 */
interface ErrorResponse {
  /** auth, ai, analysis */
  message?: string;
  /** core (RFC 7807), analysis */
  detail?: string;
  /** core (RFC 7807) — snake_case, e.g. 'validation_error'. Declared but not
   *  mapped onto `ApiException.errorCode`: it uses a different vocabulary from
   *  the `error_code` below (UPPER_SNAKE, e.g. 'NOT_FOUND') and conflating the
   *  two would make the field's meaning depend on which service replied. */
  code?: string;
  /** auth, analysis — e.g. 'token_expired', 'invalid_token' */
  error_code?: string;
  /** analysis */
  details?: Record<string, unknown>;
}

export class ApiException extends Error {
  public readonly statusCode: number;
  public readonly code: ApiErrorCode;
  public readonly details?: Record<string, unknown>;
  /**
   * The service-specific error code (e.g. 'token_expired', 'invalid_token'),
   * when the response carried one. Distinct from `code`, which is this
   * frontend's own coarse classification of the HTTP status.
   */
  public readonly errorCode?: string;

  constructor(
    message: string,
    statusCode: number,
    code: ApiErrorCode,
    details?: Record<string, unknown>,
    errorCode?: string
  ) {
    super(message);
    this.name = 'ApiException';
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
    this.errorCode = errorCode;
  }
}

export function handleApiError(error: unknown): ApiException {
  if (isAxiosError(error)) {
    const axiosError = error as AxiosError<ErrorResponse>;
    const responseData = axiosError.response?.data;

    // No response at all means the request never reached the service: offline,
    // DNS failure, CORS rejection, or a client timeout. That is a connectivity
    // problem, not a 5xx. Defaulting it to INTERNAL_SERVER_ERROR made the UI
    // blame the backend ("Something went wrong. Please try again later.") for
    // what is a local network fault.
    if (axiosError.response === undefined) {
      return new ApiException(ERROR_MESSAGES.NETWORK_ERROR, 0, 'NETWORK_ERROR');
    }

    const statusCode = axiosError.response.status || HTTP_STATUS.INTERNAL_SERVER_ERROR;

    // `message` is what auth/ai send; `detail` is what core (DRF, RFC 7807)
    // and analysis send. Reading only `message` discarded core's real text and
    // replaced every one of its validation errors with generic copy.
    // `error` is deliberately NOT consulted: core/ai use it as a code
    // ("rate_limit_exceeded") while auth uses it as a message, so it cannot be
    // mapped to one without guessing.
    const serviceMessage = responseData?.message || responseData?.detail;
    let message = serviceMessage || ERROR_MESSAGES.SERVER_ERROR;
    let code: ApiErrorCode;

    switch (statusCode) {
      case HTTP_STATUS.UNAUTHORIZED:
        code = 'UNAUTHORIZED';
        message = ERROR_MESSAGES.UNAUTHORIZED;
        break;
      case HTTP_STATUS.FORBIDDEN:
        code = 'FORBIDDEN';
        message = ERROR_MESSAGES.FORBIDDEN;
        break;
      case HTTP_STATUS.NOT_FOUND:
        code = 'NOT_FOUND';
        message = ERROR_MESSAGES.NOT_FOUND;
        break;
      case HTTP_STATUS.UNPROCESSABLE_ENTITY:
        code = 'VALIDATION_ERROR';
        message = serviceMessage || ERROR_MESSAGES.VALIDATION_ERROR;
        break;
      case HTTP_STATUS.TOO_MANY_REQUESTS:
        code = 'RATE_LIMITED';
        message = ERROR_MESSAGES.RATE_LIMITED;
        break;
      case HTTP_STATUS.BAD_REQUEST:
        code = 'VALIDATION_ERROR';
        message = serviceMessage || ERROR_MESSAGES.VALIDATION_ERROR;
        break;
      default:
        code = statusCode >= 500 ? 'SERVER_ERROR' : 'NETWORK_ERROR';
        message = statusCode >= 500 ? ERROR_MESSAGES.SERVER_ERROR : ERROR_MESSAGES.NETWORK_ERROR;
    }

    return new ApiException(
      message,
      statusCode,
      code,
      responseData?.details,
      responseData?.error_code
    );
  }

  return new ApiException(ERROR_MESSAGES.NETWORK_ERROR, 0, 'NETWORK_ERROR');
}

export function isApiError(error: unknown): error is ApiException {
  return error instanceof ApiException;
}

export function getErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return ERROR_MESSAGES.NETWORK_ERROR;
}
