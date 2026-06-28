export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',
  VERIFY_EMAIL: '/verify-email',
  RESET_PASSWORD: '/reset-password',
  PRICING: '/pricing',
  FEATURES: '/features',
  DOCS: '/docs',
} as const;

export const DEFAULT_WORKSPACE_SLUG = 'dashboard';

export const workspaceRoutes = (slug: string) => ({
  dashboard: `/${slug}`,
  analysis: `/${slug}/analysis`,
  ai: `/${slug}/ai`,
  notes: `/${slug}/notes`,
  projects: `/${slug}/projects`,
  settings: `/${slug}/settings`,
  security: `/${slug}/settings/security`,
  apiKeys: `/${slug}/settings/api-keys`,
  mfa: `/${slug}/settings/mfa`,
});

export const DEFAULT_DASHBOARD_ROUTE = workspaceRoutes(DEFAULT_WORKSPACE_SLUG).dashboard;

export const API_ENDPOINTS = {
  AUTH: {
    IDENTIFY: '/auth/signin/identify/',
    PASSWORD: '/auth/signin/password/',
    OTP_SEND: '/auth/signin/otp/send/',
    OTP_VERIFY: '/auth/signin/otp/verify/',
    REGISTER: '/auth/signup/',
    LOGOUT: '/auth/logout/',
    REFRESH: '/auth/refresh/',
    FORGOT_PASSWORD: '/auth/forgot-password/',
    RESET_PASSWORD: '/auth/reset-password/',
    VERIFY_EMAIL: '/auth/verify-email/',
    RESEND_VERIFICATION: '/auth/resend-verification/',
    ME: '/auth/me/',
    SESSIONS: '/auth/sessions/',
    SESSIONS_ALL: '/auth/sessions/all/',
    SESSION_REVOKE: (sessionId: string) => `/auth/sessions/${sessionId}/`,
    LOGOUT_ALL: '/auth/logout/all/',
    API_KEYS: '/auth/api-keys/',
    API_KEY_REVOKE: (keyId: string) => `/auth/api-keys/${keyId}/`,
    MFA_VERIFY: '/auth/mfa/verify/',
  },
  WORKSPACES: {
    LIST: '/workspaces/',
    GET: (id: string) => `/workspaces/${id}/`,
    CREATE: '/workspaces/',
    UPDATE: (id: string) => `/workspaces/${id}/`,
    DELETE: (id: string) => `/workspaces/${id}/`,
    MEMBERS: (id: string) => `/workspaces/${id}/members/`,
  },
  REPOSITORIES: {
    LIST: '/repositories/',
    GET: (id: string) => `/repositories/${id}/`,
    CONNECT: '/repositories/connect/',
    DISCONNECT: (id: string) => `/repositories/${id}/disconnect/`,
    ANALYZE: (id: string) => `/repositories/${id}/analyze/`,
  },
  AI: {
    CHAT: '/ai/chat/',
    SESSIONS: '/ai/sessions/',
    STREAM: '/ai/stream/',
  },
  ANALYSIS: {
    JOBS_LIST: '/api/v1/jobs',
    JOB_GET: (id: string) => `/api/v1/jobs/${id}`,
    JOB_START: '/api/v1/jobs',
    FINDINGS: '/api/v1/findings',
    FINDINGS_SUMMARY: '/api/v1/findings/summary',
    REPORT_BY_JOB: (id: string) => `/api/v1/reports/by-job/${id}`,
    DEAD_CODE: '/api/v1/dead-code',
    ERROR_FINDINGS: '/api/v1/error-findings',
    PERF_METRICS: '/api/v1/performance-metrics',
    SIMULATION_RESULTS: '/api/v1/simulation-results',
    ENTERPRISE_GUIDE: '/api/v1/enterprise-guide',
    FILE_UPLOAD: '/api/v1/files/upload',
  },
  NOTES: {
    LIST: '/notes/',
    GET: (id: string) => `/notes/${id}/`,
    CREATE: '/notes/',
    UPDATE: (id: string) => `/notes/${id}/`,
    DELETE: (id: string) => `/notes/${id}/`,
  },
  PROJECTS: {
    LIST: '/projects/',
    GET: (id: string) => `/projects/${id}/`,
    CREATE: '/projects/',
    UPDATE: (id: string) => `/projects/${id}/`,
    DELETE: (id: string) => `/projects/${id}/`,
  },
  TASKS: {
    LIST: '/tasks/',
    GET: (id: string) => `/tasks/${id}/`,
    CREATE: '/tasks/',
    UPDATE: (id: string) => `/tasks/${id}/`,
    DELETE: (id: string) => `/tasks/${id}/`,
  },
} as const;

export const PUBLIC_AUTH_ENDPOINTS = [
  API_ENDPOINTS.AUTH.IDENTIFY,
  API_ENDPOINTS.AUTH.PASSWORD,
  API_ENDPOINTS.AUTH.OTP_SEND,
  API_ENDPOINTS.AUTH.OTP_VERIFY,
  API_ENDPOINTS.AUTH.REGISTER,
  API_ENDPOINTS.AUTH.REFRESH,
  API_ENDPOINTS.AUTH.FORGOT_PASSWORD,
  API_ENDPOINTS.AUTH.RESET_PASSWORD,
  API_ENDPOINTS.AUTH.VERIFY_EMAIL,
  API_ENDPOINTS.AUTH.RESEND_VERIFICATION,
] as const;

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
