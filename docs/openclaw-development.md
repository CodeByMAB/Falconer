# OpenClaw PoC Development Workflow

How to run, debug, and extend the OpenClaw + Falconer PoC environment.

## Start/Stop PoC Environment

**Start (detached):**

```bash
docker-compose -f ops/docker-compose.poc.yml up -d
```

**Start (foreground, with logs):**

```bash
docker-compose -f ops/docker-compose.poc.yml up
```

**Stop:**

```bash
docker-compose -f ops/docker-compose.poc.yml down
```

**Stop and remove volumes:**

```bash
docker-compose -f ops/docker-compose.poc.yml down -v
```

## View Logs and Debug

**All services:**

```bash
docker-compose -f ops/docker-compose.poc.yml logs -f
```

**Single service:**

```bash
docker-compose -f ops/docker-compose.poc.yml logs -f openclaw
docker-compose -f ops/docker-compose.poc.yml logs -f falconer-api
```

**Shell inside container:**

```bash
docker exec -it falconer-openclaw sh
docker exec -it falconer-api sh
```

## Testing Changes

**Falconer API (local, no Docker):**

```bash
# From project root, with venv activated
pip install -e .
falconer api-server --host 0.0.0.0 --port 8000
# In another terminal:
curl http://localhost:8000/api/health
curl http://localhost:8000/api/test/fee-brief
curl -X POST http://localhost:8000/api/test/echo -H "Content-Type: application/json" -d '{"x":1}'
```

**With Docker:** See [Rebuilding Falconer API](#rebuilding-falconer-api) below.

**OpenClaw:** Code changes require rebuilding the image:

```bash
docker-compose -f ops/docker-compose.poc.yml build openclaw
docker-compose -f ops/docker-compose.poc.yml up -d openclaw
```

## Adding New Skills (Phase 2)

OpenClaw supports custom skills. For Phase 2:

1. Place skill code in a directory that is mounted into the OpenClaw container (e.g. `openclaw-skills` volume or a bind mount).
2. Configure OpenClaw to load that skill (see [OpenClaw docs](https://docs.openclaw.ai)).
3. From within a skill, call Falconer’s API at `FALCONER_API_URL` (e.g. `http://falconer-api:8000`) for fee brief or future endpoints.

See [openclaw-setup.md](openclaw-setup.md) and [openclaw-architecture.md](openclaw-architecture.md) for context.

## Rebuilding Falconer API

Falconer API uses a dedicated `Dockerfile.api` that pre-builds dependencies into the image, optimizing container startup (no `pip install` on each start). After changing Falconer source code, rebuild and restart:

```bash
docker-compose -f ops/docker-compose.poc.yml build falconer-api
docker-compose -f ops/docker-compose.poc.yml up -d falconer-api
```

For a full rebuild without cache:

```bash
docker-compose -f ops/docker-compose.poc.yml build --no-cache falconer-api
docker-compose -f ops/docker-compose.poc.yml up -d falconer-api
```
