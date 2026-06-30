# ======================================================================
# DOC-007-AI web (Next.js 16 App Router) - production image
#
# Multi-stage build using Next.js standalone output (output: "standalone"
# in next.config.mjs). The final image only contains the minimal server
# bundle, static assets, and public files - no source, no node_modules dev
# tree.
#
# Local development still works: docker-compose.yml overrides this image's
# CMD with `npm run dev` and bind-mounts the source tree, so the production
# default below does not affect `docker compose up`.
# ======================================================================

# ---- deps: install production-resolved node_modules from the lockfile ----
FROM node:20-alpine AS deps
WORKDIR /app

# npm ci needs both package.json and the lockfile and installs exactly what
# is pinned. We install all deps here (dev deps are needed to build).
COPY package.json package-lock.json ./
RUN npm ci

# ---- build: compile the Next.js app into .next/standalone ----
FROM node:20-alpine AS build
WORKDIR /app

# NEXT_PUBLIC_* values are inlined into the client bundle at build time, so
# the API base URL must be provided here (via --build-arg / compose build
# args), not just at runtime.
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL} \
    NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN npm run build

# ---- runner: tiny runtime image that serves the standalone server ----
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Run as a non-root user.
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# The standalone output bundles a minimal node_modules plus server.js.
# Static assets and the public folder must be copied alongside it.
COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=build --chown=nextjs:nodejs /app/public ./public

USER nextjs

EXPOSE 3000

# server.js is emitted by the standalone build at the bundle root.
CMD ["node", "server.js"]
