import type { NextConfig } from 'next';
import createBundleAnalyzer from '@next/bundle-analyzer';
// v11 moved the Next config wrapper to a dedicated subpath export.
import { withSentryConfig } from '@sentry/nextjs/config';

const withBundleAnalyzer = createBundleAnalyzer({
  enabled: process.env.ANALYZE === 'true',
});

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    optimizePackageImports: ['lucide-react', '@radix-ui/react-icons', '@phosphor-icons/react'],
  },
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'kraivor-uploads.s3.amazonaws.com' },
      { protocol: 'https', hostname: 'avatars.githubusercontent.com' },
      { protocol: 'https', hostname: 'lh3.googleusercontent.com' },
      // Dev only: profile media is served by nginx -> identity from local
      // disk (see services/auth/auth/settings/development.py), so banner and
      // avatar URLs come back as http://localhost/media/...
      { protocol: 'http', hostname: 'localhost' },
    ],
  },
  logging: {
    fetches: {
      fullUrl: process.env.NODE_ENV === 'development',
    },
  },
  typescript: {
    ignoreBuildErrors: false,
  },
  eslint: {
    ignoreDuringBuilds: false,
  },
  async rewrites() {
    return [
      {
        source: '/s3-proxy/:path*',
        destination: 'https://kraivor-uploads.s3.amazonaws.com/:path*',
      },
    ];
  },
};

export default withBundleAnalyzer(
  // Sentry must wrap the outermost so source maps and instrumentation apply.
  // No-op when SENTRY_DSN is unset, so local/CI builds are unaffected.
  withSentryConfig(nextConfig, {
    silent: !process.env.SENTRY_DSN,
    org: process.env.SENTRY_ORG,
    project: process.env.SENTRY_PROJECT,
    widenClientFileUpload: true,
  })
);
