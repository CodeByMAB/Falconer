# OpenClaw PoC – Falconer Test API

Specification of the Falconer test API endpoints used by the OpenClaw integration PoC.

## Base URL

When running via Docker PoC: `http://falconer-api:8000` (from OpenClaw container) or `http://localhost:8000` (from host).

## Authentication

**API Key Authentication** (for Bitcoin endpoints)

- **Header**: `X-API-Key: your-api-key-here`
- **Required**: For all `/api/bitcoin/*` endpoints when OpenClaw integration is enabled
- **Configuration**: Set `OPENCLAW_API_KEY` in `.env` and `FALCONER_API_KEY` in `.env.openclaw`

**Note**: Health check and test endpoints (`/api/health`, `/api/test/*`) do not require authentication.

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

### Bitcoin Blockchain Information

**GET** `/api/bitcoin/blockchain-info`

Returns current Bitcoin blockchain information from the connected Bitcoin node.

**Authentication**: Required (X-API-Key header)

**Response** (200):

```json
{
  "blocks": 800000,
  "headers": 800000,
  "chain": "main",
  "difficulty": 123456789.1234567,
  "size_on_disk": 1000000000,
  "pruned": false,
  "timestamp": "2023-12-01T12:34:56.789012"
}
```

**Example:**

```bash
curl http://localhost:8000/api/bitcoin/blockchain-info \
  -H "X-API-Key: your-api-key"
```

---

### Bitcoin Mempool Information

**GET** `/api/bitcoin/mempool-info`

Returns current mempool statistics and information.

**Authentication**: Required (X-API-Key header)

**Response** (200):

```json
{
  "loaded": true,
  "size": 5000,
  "bytes": 1000000,
  "usage": 500000,
  "maxmempool": 300000000,
  "mempoolminfee": 0.00001,
  "timestamp": "2023-12-01T12:34:56.789012"
}
```

**Example:**

```bash
curl http://localhost:8000/api/bitcoin/mempool-info \
  -H "X-API-Key: your-api-key"
```

---

### Bitcoin Fee Estimates

**GET** `/api/bitcoin/fee-estimates`

Returns current fee estimates for different confirmation targets.

**Authentication**: Required (X-API-Key header)

**Response** (200):

```json
{
  "fast": 20,
  "medium": 10,
  "slow": 5,
  "economical": 2,
  "minimum": 1,
  "timestamp": "2023-12-01T12:34:56.789012"
}
```

**Example:**

```bash
curl http://localhost:8000/api/bitcoin/fee-estimates \
  -H "X-API-Key: your-api-key"
```

---

### Bitcoin Network Statistics

**GET** `/api/bitcoin/network-stats`

Returns comprehensive Bitcoin network statistics and health indicators.

**Authentication**: Required (X-API-Key header)

**Response** (200):

```json
{
  "network": "main",
  "block_height": 800000,
  "electrs_tip_height": 800000,
  "difficulty": 123456789.1234567,
  "mempool_size": 5000,
  "mempool_bytes": 1000000,
  "hash_rate": 123456789012345,
  "is_synced": true,
  "timestamp": "2023-12-01T12:34:56.789012"
}
```

**Example:**

```bash
curl http://localhost:8000/api/bitcoin/network-stats \
  -H "X-API-Key: your-api-key"
```

---

### Bitcoin Market Analysis

**GET** `/api/bitcoin/market-analysis`

Returns AI-powered Bitcoin market analysis (simplified for OpenClaw integration).

**Authentication**: Required (X-API-Key header)

**Response** (200):

```json
{
  "fee_trend": "stable",
  "mempool_congestion": "low",
  "network_activity": "normal",
  "opportunity_score": 0.75,
  "risk_level": "medium",
  "recommendation": "Good conditions for transactions",
  "timestamp": "2023-12-01T12:34:56.789012"
}
```

**Example:**

```bash
curl http://localhost:8000/api/bitcoin/market-analysis \
  -H "X-API-Key: your-api-key"
```

---

### Bitcoin Address Information

**GET** `/api/bitcoin/address-info?address={address}`

Returns information about a specific Bitcoin address.

**Authentication**: Required (X-API-Key header)

**Parameters:**
- `address` (required): Bitcoin address to query

**Response** (200):

```json
{
  "address": "bc1qtest123",
  "balance_sats": 1000000,
  "tx_count": 10,
  "unconfirmed_balance_sats": 50000,
  "timestamp": "2023-12-01T12:34:56.789012"
}
```

**Example:**

```bash
curl "http://localhost:8000/api/bitcoin/address-info?address=bc1qtest123" \
  -H "X-API-Key: your-api-key"
```

---

### Bitcoin Transaction Information

**GET** `/api/bitcoin/transaction?tx_id={tx_id}`

Returns information about a specific Bitcoin transaction.

**Authentication**: Required (X-API-Key header)

**Parameters:**
- `tx_id` (required): Transaction ID to query

**Response** (200):

```json
{
  "txid": "abc123def456",
  "confirmations": 6,
  "size": 225,
  "weight": 500,
  "fee": 1000,
  "fee_rate": 4.44,
  "timestamp": "2023-12-01T12:34:56.789012"
}
```

**Example:**

```bash
curl "http://localhost:8000/api/bitcoin/transaction?tx_id=abc123def456" \
  -H "X-API-Key: your-api-key"
```

---

## Error Handling

- **400** – Invalid request parameters or malformed requests
- **401** – Missing or invalid API key (for authenticated endpoints)
- **404** – Resource not found (e.g., transaction not found)
- **500** – Internal server error; check logs

All error responses follow this format:

```json
{
  "error": "Error message",
  "status_code": 404,
  "timestamp": "2023-12-01T12:34:56.789012"
}
```

## Security

- **API Key Authentication**: All Bitcoin endpoints require a valid API key when OpenClaw integration is enabled
- **Security Headers**: All responses include security headers (CSP, XSS protection, etc.)
- **CORS**: Cross-Origin Resource Sharing is enabled for all endpoints
- **HTTPS**: Recommended for production use (configure reverse proxy)

## Rate Limiting

The API does not currently implement rate limiting, but this may be added in future versions. Consider implementing rate limiting at the reverse proxy level for production deployments.

## OpenClaw Skill Integration

See the [OpenClaw Skills Documentation](#) for examples of how to integrate these endpoints into OpenClaw skills.

## Changelog

### v0.2.0 (Current)
- Added Bitcoin blockchain endpoints with authentication
- Enhanced security with API key validation
- Added comprehensive error handling
- Improved documentation and examples

### v0.1.0 (Initial)
- Basic health check and test endpoints
- No authentication required
- Minimal error handling
