# Frontend production image for the local demo and E2E only, never for Netlify (TRD 15 DEP-017, DEP-023;
# FEAT-077). Build context: frontend/
#   docker build --build-arg NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 --build-arg NEXT_PUBLIC_APP_ENV=local frontend
# NEXT_PUBLIC_* values are public and inlined at build time: rebuild after changing them (TRD 21 §8).

# --- dependencies: lockfile-exact install (npm ci, TRD 16 CIC-081) ---
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# --- build: next build with the public build arguments (lib/config.ts fails the build when they are missing) ---
FROM node:20-alpine AS build
WORKDIR /app
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_APP_ENV
ARG GIT_SHA=unknown
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL} \
    NEXT_PUBLIC_APP_ENV=${NEXT_PUBLIC_APP_ENV} \
    GIT_SHA=${GIT_SHA} \
    NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# --- runtime: production dependencies and the build output only, non-root ---
FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund && npm cache clean --force
COPY --from=build /app/next.config.js ./next.config.js
COPY --from=build /app/.next ./.next
USER node
EXPOSE 3000
CMD ["node_modules/.bin/next", "start", "-p", "3000"]
