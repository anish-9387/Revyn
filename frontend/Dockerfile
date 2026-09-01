# syntax=docker/dockerfile:1

FROM node:22-slim AS deps
WORKDIR /app
# Every direct dependency is version-pinned in package.json, and `install` (not `ci`) keeps the
# image buildable from a lockfile written on another platform, where the optional native
# packages for Tailwind's oxide and lightningcss differ.
COPY package.json ./
RUN npm install --ignore-scripts --no-audit --no-fund

FROM node:22-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Baked in at build time: Next.js inlines NEXT_PUBLIC_* into the client bundle.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN npm run build

FROM node:22-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
