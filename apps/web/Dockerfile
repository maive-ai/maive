# syntax=docker/dockerfile:1.4
# Build stage
FROM node:22-alpine AS builder

WORKDIR /app

# Install pnpm
RUN corepack enable pnpm

# Copy root package files first (these change less frequently)
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

# Copy package.json files for dependencies and devDependencies
COPY apps/web/package.json ./apps/web/
# TODO: Pull these from package repository instead of local copy?
COPY packages/api/package.json ./packages/api/
COPY packages/brand/package.json ./packages/brand/
COPY packages/tailwind-config/package.json ./packages/tailwind-config/

# Install dependencies with BuildKit cache mount for better performance
RUN --mount=type=cache,target=/root/.pnpm-store \
    pnpm install --frozen-lockfile

# Copy only the source code needed for the web app build
COPY apps/web/src ./apps/web/src
COPY apps/web/public ./apps/web/public
COPY apps/web/index.html ./apps/web/
COPY apps/web/vite.config.ts ./apps/web/
COPY apps/web/tsconfig*.json ./apps/web/
COPY apps/web/package.json ./apps/web/

# Copy shared packages that the web app depends on
COPY packages/api/client ./packages/api/client
COPY packages/api/package.json ./packages/api/
COPY packages/brand/logos ./packages/brand/logos
COPY packages/brand/fonts ./packages/brand/fonts
COPY packages/brand/package.json ./packages/brand/
COPY packages/tailwind-config/shared-styles.css ./packages/tailwind-config/

# Copy TypeScript configuration files
COPY tools/typescript ./tools/typescript

# Build the web app
WORKDIR /app/apps/web

# Build arguments for environment variables with defaults
ARG PUBLIC_SERVER_URL=http://localhost:8080
ARG PUBLIC_BASE_PATH=/
ARG PUBLIC_COGNITO_DOMAIN=http://localhost:8080
ARG PUBLIC_COGNITO_CLIENT_ID=test
ARG PUBLIC_COGNITO_SCOPES=openid+email+profile
ARG PUBLIC_OAUTH_REDIRECT_ROUTE=api/auth/callback

# Set environment variables for build
ENV PUBLIC_SERVER_URL=${PUBLIC_SERVER_URL}
ENV PUBLIC_BASE_PATH=${PUBLIC_BASE_PATH}
ENV PUBLIC_COGNITO_DOMAIN=${PUBLIC_COGNITO_DOMAIN}
ENV PUBLIC_COGNITO_CLIENT_ID=${PUBLIC_COGNITO_CLIENT_ID}
ENV PUBLIC_COGNITO_SCOPES=${PUBLIC_COGNITO_SCOPES}
ENV PUBLIC_OAUTH_REDIRECT_ROUTE=${PUBLIC_OAUTH_REDIRECT_ROUTE}

RUN pnpm build

# Production stage
FROM nginx:stable-alpine AS production

# Install curl for healthcheck
RUN apk add --no-cache curl

# Copy nginx configuration
COPY apps/web/nginx.conf /etc/nginx/nginx.conf

# Copy built files
COPY --from=builder /app/apps/web/dist /usr/share/nginx/html

# Copy healthcheck file
COPY apps/web/public/healthcheck /usr/share/nginx/html/healthcheck

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl --fail --silent http://0.0.0.0:80/healthcheck || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
