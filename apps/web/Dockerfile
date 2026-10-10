# The pnpm workspace keeps a single lockfile at the repository root, so the
# build context for this image is the repo root (docker-compose sets
# `context: .` / `dockerfile: apps/web/Dockerfile`). `turbo prune` reduces the
# workspace to just kraivor-frontend: `out/json` holds the manifests + pruned
# lockfile, `out/full` holds the source. Canonical pattern from the bundled
# turbo docs (docs/guides/tools/docker.mdx).
FROM node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1 AS base

# turbo publishes a glibc binary; alpine needs libc6-compat for it.
# corepack pins pnpm via the `packageManager` field in the root package.json.
RUN apk add --no-cache libc6-compat && \
    corepack enable

FROM base AS prepare
WORKDIR /app
COPY . .
RUN pnpm dlx turbo@2.11.7 prune kraivor-frontend --docker

FROM base AS builder
WORKDIR /app
COPY --from=prepare /app/out/json/ ./
RUN pnpm install --frozen-lockfile
COPY --from=prepare /app/out/full/ ./
RUN pnpm --filter kraivor-frontend build

FROM base
WORKDIR /app
ENV NODE_ENV=production
COPY --from=prepare /app/out/json/ ./
COPY --from=builder /app/apps/web/.next /app/apps/web/.next
COPY --from=builder /app/apps/web/public /app/apps/web/public
COPY --from=builder /app/apps/web/next.config.ts /app/apps/web/next.config.ts

# Alpine ships busybox rather than shadow-utils, so groupadd/useradd,
# --create-home and /bin/bash do not exist on this base image. addgroup and
# adduser are the Alpine equivalents; busybox provides no bash.
RUN addgroup -g 1001 appgroup && \
    adduser -u 1001 -G appgroup -h /home/appuser -D appuser && \
    chown -R appuser:appgroup /app

# Install as the runtime user so pnpm links from appuser's store; if a later
# pnpm action runs under a different user the store paths disagree (ERR_PNPM
# _UNEXPECTED_STORE). next.config.ts is loaded by `next start` at runtime and
# imports @next/bundle-analyzer, @sentry/nextjs and typescript (to transpile
# the config), so all three must be installed here. Omitting dev deps breaks
# config loading, not just the build.
USER appuser
ENV HOME=/home/appuser
RUN pnpm install --frozen-lockfile --prod

EXPOSE 3000
CMD ["pnpm", "--filter", "kraivor-frontend", "start"]