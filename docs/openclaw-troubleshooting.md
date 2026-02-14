# OpenClaw PoC Troubleshooting

Common issues and fixes for the OpenClaw + Falconer PoC environment.

## vLLM Connection Failures

**Symptom:** OpenClaw logs show timeouts or connection errors to vLLM.

**Checks:**

1. vLLM running on host and serving OpenAI-compatible API: `curl http://localhost:8000/v1/models`
2. From host: ensure the model is loaded and the `/v1` endpoint responds.
3. On Mac/Windows, containers use `host.docker.internal:8000`. On Linux, ensure `extra_hosts: - "host.docker.internal:host-gateway"` is set in `ops/docker-compose.poc.yml` (it is by default), or run vLLM in a container on the same network.

**Fix:** Start vLLM, confirm port 8000 is not blocked, and that `OPENAI_BASE_URL` (or equivalent) in OpenClaw env points to `http://host.docker.internal:8000/v1`.

---

## Docker Networking Issues

**Symptom:** OpenClaw cannot reach `falconer-api:8000` or health checks fail.

**Checks:**

1. All services on `falconer-network`: `docker network inspect falconer_falconer-network`
2. Falconer API responding: `docker exec falconer-openclaw wget -qO- http://falconer-api:8000/api/health`

**Fix:** Restart the stack: `docker-compose -f ops/docker-compose.poc.yml down && docker-compose -f ops/docker-compose.poc.yml up -d`. Ensure no port conflicts (3000, 3001, 8000).

---

## Telegram Bot Not Responding

**Symptom:** Messages to the bot get no reply.

**Checks:**

1. `.env.openclaw` has `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USERS` set.
2. Your Telegram user ID is in `TELEGRAM_ALLOWED_USERS` (comma-separated if multiple).
3. OpenClaw container was restarted after changing `.env.openclaw`.
4. Container logs: `docker-compose -f ops/docker-compose.poc.yml logs openclaw`

**Fix:** Verify token with BotFather, add your user ID, and restart OpenClaw. Do not commit the token.

---

## OpenClaw Container Crashes

**Symptom:** OpenClaw container exits or restarts repeatedly.

**Checks:**

1. Logs: `docker-compose -f ops/docker-compose.poc.yml logs openclaw`
2. Build: `docker-compose -f ops/docker-compose.poc.yml build openclaw`
3. Node/memory: Official OpenClaw may require sufficient memory; increase Docker memory if needed.

**Fix:** Ensure `.env.openclaw` has no syntax errors and required vars are set. Rebuild with `docker-compose -f ops/docker-compose.poc.yml build --no-cache openclaw` if the image is suspect.

---

## API Connectivity Problems

**Symptom:** OpenClaw cannot call Falconer API or health check fails.

**Checks:**

1. From host: `curl http://localhost:8000/api/health`
2. Falconer API logs: `docker-compose -f ops/docker-compose.poc.yml logs falconer-api`
3. From OpenClaw container: `docker exec falconer-openclaw wget -qO- http://falconer-api:8000/api/health`

**Fix:** Ensure `falconer-api` is healthy and that `FALCONER_API_URL=http://falconer-api:8000` is set in OpenClaw’s environment. Restart `falconer-api` if the install failed: `docker-compose -f ops/docker-compose.poc.yml up -d falconer-api`.

---

## Environment Variable Configuration Errors

**Symptom:** OpenClaw or Falconer API misbehaves; logs mention missing or invalid config.

**Checks:**

1. `.env.openclaw` is based on `.env.openclaw.example`.
2. No stray spaces around `=` or values.
3. Required vars for your use case (e.g. Telegram) are set.

**Fix:** Copy `.env.openclaw.example` to `.env.openclaw` again, fill in only the needed values, and restart the relevant containers.
