FROM node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1 AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1
WORKDIR /app
COPY --from=builder /app/.next /app/.next
COPY --from=builder /app/public /app/public
COPY --from=builder /app/package*.json /app/
# next.config.ts is loaded by `next start` at runtime and imports
# @next/bundle-analyzer and @sentry/nextjs at the top level, so both must be
# installed here. Omitting dev deps breaks config loading, not just the build.
RUN npm ci --omit=dev

# Alpine ships busybox rather than shadow-utils, so groupadd/useradd,
# --create-home and /bin/bash do not exist on this base image. addgroup and
# adduser are the Alpine equivalents; busybox provides no bash.
RUN addgroup -g 1001 appgroup && \
    adduser -u 1001 -G appgroup -h /home/appuser -D appuser && \
    chown -R appuser:appgroup /app
USER appuser

EXPOSE 3000
CMD ["npm", "start"]
