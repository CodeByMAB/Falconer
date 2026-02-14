# OpenClaw PoC – Falconer Test API

Specification of the Falconer test API endpoints used by the OpenClaw integration PoC.

## Base URL

When running via Docker PoC: `http://falconer-api:8000` (from OpenClaw container) or `http://localhost:8000` (from host).

## Endpoints

### Health Check

**GET** `/api/health`

Used for Docker health checks and connectivity verification. No authentication.

**Response** (200):

```json
{
  "status": "healthy",
  "service": "falconer-api",
  "version": "0.2.0"
}
```

**Example:**

```bash
curl http://localhost:8000/api/health
```

---

### Fee Brief Test

**GET** `/api/test/fee-brief`

Returns simplified fee intelligence data for PoC. Mock data only; no real Bitcoin queries.

**Response** (200):

```json
{
  "current_fee_rate": 10,
  "mempool_size": 45000,
  "recommendation": "Good time for transactions"
}
```

**Example:**

```bash
curl http://localhost:8000/api/test/fee-brief
```

---

### Echo Test

**POST** `/api/test/echo`

Echoes the request body. Used to validate request/response and JSON handling.

**Request body:** Any JSON object.

**Response** (200):

```json
{
  "echo": { ... }
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/api/test/echo \
  -H "Content-Type: application/json" \
  -d '{"message": "hello"}'
```

---

## Error Handling

- **400** – Invalid JSON or bad request (e.g. malformed body on `/api/test/echo`).
- **500** – Internal server error; check logs.

Responses are JSON. Future phases may add authentication (e.g. API key) and additional endpoints.
