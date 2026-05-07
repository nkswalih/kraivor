export const ROUTES = {
  // Public routes
  LANDING: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',
  VERIFY_EMAIL: '/verify-email',
  PRICING: '/pricing',
  FEATURES: '/features',
  DOCS: '/docs',

  // Protected routes
  APP: '/[workspace]',
  DASHBOARD: '/[workspace]/(dashboard)',
  ANALYSIS: '/[workspace]/(routes)/analysis',
  AI: '/[workspace]/(routes)/ai',
  NOTES: '/[workspace]/(routes)/notes',
  PROJECTS: '/[workspace]/(routes)/projects',
  SETTINGS: '/[workspace]/settings',

  // API routes
  API: {
    AUTH: '/api/auth',
    AUTH_REFRESH: '/api/auth/refresh',
    AUTH_LOGOUT: '/api/auth/logout',
    WORKSPACES: '/api/workspaces',
    REPOSITORIES: '/api/repositories',
    ANALYSIS: '/api/analysis',
    NOTES: '/api/notes',
    PROJECTS: '/api/projects',
    TASKS: '/api/tasks',
  },
} as const;

export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login',
    REGISTER: '/auth/register',
    LOGOUT: '/auth/logout',
    REFRESH: '/auth/refresh',
    FORGOT_PASSWORD: '/auth/forgot-password',
    RESET_PASSWORD: '/auth/reset-password',
    VERIFY_EMAIL: '/auth/verify-email',
    ME: '/auth/me',
  },
  WORKSPACES: {
    LIST: '/workspaces',
    GET: (id: string) => `/workspaces/${id}`,
    CREATE: '/workspaces',
    UPDATE: (id: string) => `/workspaces/${id}`,
    DELETE: (id: string) => `/workspaces/${id}`,
    MEMBERS: (id: string) => `/workspaces/${id}/members`,
  },
  REPOSITORIES: {
    LIST: '/repositories',
    GET: (id: string) => `/repositories/${id}`,
    CONNECT: '/repositories/connect',
    DISCONNECT: (id: string) => `/repositories/${id}/disconnect`,
    ANALYZE: (id: string) => `/repositories/${id}/analyze`,
  },
  AI: {
    CHAT: '/ai/chat',
    SESSIONS: '/ai/sessions',
    STREAM: '/ai/stream',
  },
  NOTES: {
    LIST: '/notes',
    GET: (id: string) => `/notes/${id}`,
    CREATE: '/notes',
    UPDATE: (id: string) => `/notes/${id}`,
    DELETE: (id: string) => `/notes/${id}`,
  },
  PROJECTS: {
    LIST: '/projects',
    GET: (id: string) => `/projects/${id}`,
    CREATE: '/projects',
    UPDATE: (id: string) => `/projects/${id}`,
    DELETE: (id: string) => `/projects/${id}`,
  },
  TASKS: {
    LIST: '/tasks',
    GET: (id: string) => `/tasks/${id}`,
    CREATE: '/tasks',
    UPDATE: (id: string) => `/tasks/${id}`,
    DELETE: (id: string) => `/tasks/${id}`,
  },
} as const;

export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  TOO_MANY_REQUESTS: 429,
  INTERNAL_SERVER_ERROR: 500,
  SERVICE_UNAVAILABLE: 503,
} as const;

export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Unable to connect. Please check your internet connection.',
  SERVER_ERROR: 'Something went wrong. Please try again later.',
  UNAUTHORIZED: 'Your session has expired. Please log in again.',
  FORBIDDEN: 'You do not have permission to perform this action.',
  NOT_FOUND: 'The requested resource was not found.',
  VALIDATION_ERROR: 'Please check your input and try again.',
  RATE_LIMITED: 'Too many requests. Please wait a moment.',
} as const;