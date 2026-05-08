export const config = {
  api: {
    baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001',
    timeout: 30000,
    retryAttempts: 3,
  },
  auth: {
    tokenRefreshThreshold: 60000, // 1 minute before expiry
    sessionCheckInterval: 300000, // 5 minutes
  },
  app: {
    name: 'Kraivor',
    tagline: 'Developer Intelligence Platform',
    defaultLocale: 'en',
  },
  features: {
    enableDebugMode: process.env.NODE_ENV === 'development',
    enableAnalytics: process.env.NODE_ENV === 'production',
  },
} as const;

export type AppConfig = typeof config;