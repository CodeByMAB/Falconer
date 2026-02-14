# OpenClaw PoC Setup Guide

Step-by-step instructions to set up the OpenClaw development environment for Falconer integration proof-of-concept.

## Prerequisites

- **Docker** and **Docker Compose** (v2+)
- **vLLM** installed and running locally (OpenAI-compatible API, e.g. port 8000) (see [AI_SETUP.md](../AI_SETUP.md))
- **Telegram** account (for bot testing)
- **Node.js 22+** and **pnpm** (optional, only if running OpenClaw outside Docker)

## Installation

### 1. OpenClaw Version

This PoC uses the **TypeScript OpenClaw** (official):

- Repository: <https://github.com/openclaw/openclaw>
- Full feature set, active community, and official documentation
- Alternative (Phase 2): Python port at <https://github.com/zhaoyuong/openclaw-python> for native Falconer integration

### 2. Docker Environment

From the Falconer project root:

```bash
# Copy OpenClaw environment template
cp .env.openclaw.example .env.openclaw

# Edit .env.openclaw and set TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS, etc.
# Do not commit .env.openclaw (it is in .gitignore)

# Start PoC stack (OpenClaw + Falconer API)
docker-compose -f ops/docker-compose.poc.yml up -d

# View logs
docker-compose -f ops/docker-compose.poc.yml logs -f
```

### 3. vLLM

Ensure vLLM is running on the host and exposes an OpenAI-compatible API (e.g. at `http://localhost:8000/v1`):

```bash
curl http://localhost:8000/v1/models
# Should list your loaded model
```

Containers use `host.docker.internal:8000` to reach vLLM (Mac/Windows; on Linux you may need `extra_hosts` or host network).

### 4. Telegram Bot

1. Open Telegram and message **@BotFather**.
2. Send `/newbot`.
3. Choose a name (e.g. "Falconer PoC Bot") and a username (e.g. `falconer_poc_bot`).
4. Copy the **bot token** (e.g. `123456789:ABCdefGHI...`).
5. Get your Telegram user ID (e.g. use @userinfobot or check BotFather instructions).
6. In `.env.openclaw` set:
   - `TELEGRAM_BOT_TOKEN=<token>`
   - `TELEGRAM_ALLOWED_USERS=<your_telegram_user_id>`
7. Restart the OpenClaw container so it picks up the new env.

### 5. Verification

- **Web UI**: <http://localhost:3000>
- **Falconer API health**: `curl http://localhost:8000/api/health`
- **Telegram**: Send "Hello" to your bot and confirm a response.

## Troubleshooting

See [openclaw-troubleshooting.md](openclaw-troubleshooting.md) for common issues (vLLM, Docker networking, Telegram, API).

## Screenshots

After a successful setup:

- Web UI at `http://localhost:3000` shows the OpenClaw interface.
- Telegram bot replies to allowed users.
- `curl http://localhost:8000/api/health` returns `{"status":"healthy","service":"falconer-api","version":"..."}`.
