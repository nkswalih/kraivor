import { isAxiosError, type AxiosError } from 'axios';
import { HTTP_STATUS, ERROR_MESSAGES } from '@/constants';
import type { ApiError, ApiErrorCode } from '@/types/api';

interface ErrorResponse {
  message?: string;
  code?: string;
  details?: Record<string, unknown>;
}

export class ApiException extends Error {
  public readonly statusCode: number;
  public readonly code: ApiErrorCode;
  public readonly details?: Record<string, unknown>;

  constructor(message: string, statusCode: number, code: ApiErrorCode, details?: Record<string, unknown>) {
    super(message);
    this.name = 'ApiException';
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
  }
}

export function handleApiError(error: unknown): ApiException {
  if (isAxiosError(error)) {
    const axiosError = error as AxiosError<ErrorResponse>;
    const statusCode = axiosError.response?.status || HTTP_STATUS.INTERNAL_SERVER_ERROR;
    const responseData = axiosError.response?.data;

    let message = responseData?.message || ERROR_MESSAGES.SERVER_ERROR;
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
        message = responseData?.message || ERROR_MESSAGES.VALIDATION_ERROR;
        break;
      case HTTP_STATUS.TOO_MANY_REQUESTS:
        code = 'RATE_LIMITED';
        message = ERROR_MESSAGES.RATE_LIMITED;
        break;
      case HTTP_STATUS.BAD_REQUEST:
        code = 'VALIDATION_ERROR';
        message = responseData?.message || ERROR_MESSAGES.VALIDATION_ERROR;
        break;
      default:
        code = statusCode >= 500 ? 'SERVER_ERROR' : 'NETWORK_ERROR';
        message = statusCode >= 500 ? ERROR_MESSAGES.SERVER_ERROR : ERROR_MESSAGES.NETWORK_ERROR;
    }

    return new ApiException(message, statusCode, code, responseData?.details);
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