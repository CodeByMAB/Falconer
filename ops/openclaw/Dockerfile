# OpenClaw (TypeScript official) for Falconer PoC
# Builds from official repository: https://github.com/openclaw/openclaw
FROM node:22-alpine

RUN apk add --no-cache git wget

WORKDIR /app

# Clone official OpenClaw (main branch)
RUN git clone --depth 1 https://github.com/openclaw/openclaw.git .

# Install pnpm and dependencies
RUN corepack enable && corepack prepare pnpm@10.23.0 --activate
RUN pnpm install --frozen-lockfile || pnpm install

# Build (required before start)
RUN pnpm build || true

EXPOSE 3000 3001

# Start gateway (Web UI + WebSocket)
CMD ["pnpm", "start"]
