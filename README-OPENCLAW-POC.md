# OpenClaw + Falconer PoC – Quick Start

Proof-of-concept for integrating [OpenClaw](https://github.com/openclaw/openclaw) (multi-channel AI gateway) with **Falconer** (Bitcoin intelligence). This setup runs OpenClaw and a minimal Falconer test API in Docker and connects to vLLM on the host (OpenAI-compatible API).

## Quick Start

1. **Prerequisites:** Docker, Docker Compose, vLLM (OpenAI-compatible API) running on the host (e.g. port 8000).

2. **Configure OpenClaw:**

   ```bash
   cp .env.openclaw.example .env.openclaw
   # Edit .env.openclaw: set TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USERS if using Telegram
   ```

3. **Start the stack:**

   ```bash
   docker-compose -f ops/docker-compose.poc.yml up -d
   ```

4. **Verify:**

   - Web UI: <http://localhost:3000>
   - Falconer API: `curl http://localhost:8000/api/health`
   - Telegram: create a bot via @BotFather, set token and your user ID in `.env.openclaw`, restart OpenClaw, then message the bot.

## What’s Included

- **OpenClaw** (TypeScript, official): Web UI (3000), WebSocket (3001), Telegram bot, vLLM/OpenAI-compatible LLM, calls Falconer API.
- **Falconer API**: Test endpoints only (`/api/health`, `/api/test/fee-brief`, `/api/test/echo`). No real Bitcoin operations.

## Docs

| Document | Description |
|----------|-------------|
| [docs/openclaw-setup.md](docs/openclaw-setup.md) | Full setup, prerequisites, Telegram bot creation |
| [docs/openclaw-architecture.md](docs/openclaw-architecture.md) | Architecture and data flow |
| [docs/openclaw-api.md](docs/openclaw-api.md) | Falconer test API reference |
| [docs/openclaw-troubleshooting.md](docs/openclaw-troubleshooting.md) | Common issues and fixes |
| [docs/openclaw-development.md](docs/openclaw-development.md) | Development workflow and testing |

## Run Falconer API Locally (no Docker)

```bash
pip install -e .
falconer api-server --host 0.0.0.0 --port 8000
```

## Security

- `.env.openclaw` is gitignored; do not commit tokens.
- Telegram access is restricted to `TELEGRAM_ALLOWED_USERS`.
- PoC endpoints are test-only; no production secrets or real funds.

## Next Steps (Post-PoC)

After validating the PoC: security assessment, Bitcoin fee intelligence skill, full Telegram integration, and performance benchmarking (see implementation plan).
