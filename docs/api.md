# Falconer API Documentation

This document provides a comprehensive reference for Falconer's API endpoints, CLI commands, and programmatic interfaces.

## Table of Contents

- [CLI Commands](#cli-commands)
- [AI Agent API](#ai-agent-api)
- [Funding Proposals API](#funding-proposals-api)
- [Market Analysis API](#market-analysis-api)
- [Policy Engine API](#policy-engine-api)
- [Webhook Server API](#webhook-server-api)
- [Configuration API](#configuration-api)

## CLI Commands

### Core Commands

#### `falconer fee-brief`
Generate a fee intelligence brief with current market conditions.

```bash
falconer fee-brief [--output FORMAT] [--detailed]
```

**Options:**
- `--output FORMAT`: Output format (json, text, table) [default: text]
- `--detailed`: Include detailed mempool analysis

**Example:**
```bash
falconer fee-brief --output json --detailed
```

#### `falconer mempool-health`
Check current mempool health and congestion status.

```bash
falconer mempool-health [--threshold PERCENT] [--history HOURS]
```

**Options:**
- `--threshold PERCENT`: Congestion threshold percentage [default: 80]
- `--history HOURS`: Hours of historical data to include [default: 24]

#### `falconer ai-agent`
Start the AI agent for autonomous Bitcoin earning.

```bash
falconer ai-agent [--autonomous] [--model MODEL] [--interval SECONDS]
```

**Options:**
- `--autonomous`: Run in autonomous mode (continuous cycles)
- `--model MODEL`: Ollama model to use [default: llama3.1:8b]
- `--interval SECONDS`: Cycle interval in seconds [default: 300]

**Example:**
```bash
falconer ai-agent --autonomous --model llama3.1:13b --interval 600
```

### Funding Proposals Commands

#### `falconer proposals list`
List all funding proposals with optional filtering.

```bash
falconer proposals list [--status STATUS] [--limit N] [--format FORMAT]
```

**Options:**
- `--status STATUS`: Filter by status (pending, approved, rejected, expired)
- `--limit N`: Maximum number of proposals to show [default: 50]
- `--format FORMAT`: Output format (table, json, csv)

#### `falconer proposals show <id>`
Show detailed information for a specific proposal.

```bash
falconer proposals show <proposal-id> [--include-context]
```

**Options:**
- `--include-context`: Include AI context and market data used

#### `falconer proposals stats`
Display funding proposal statistics and performance metrics.

```bash
falconer proposals stats [--period DAYS] [--detailed]
```

**Options:**
- `--period DAYS`: Time period for statistics [default: 30]
- `--detailed`: Include detailed breakdown by status and performance

#### `falconer webhook-server`
Start the webhook server for handling funding proposal approvals.

```bash
falconer webhook-server [--host HOST] [--port PORT] [--debug]
```

**Options:**
- `--host HOST`: Server host [default: 0.0.0.0]
- `--port PORT`: Server port [default: 8080]
- `--debug`: Enable debug logging

#### `falconer proposal-test`
Test n8n integration and webhook connectivity.

```bash
falconer proposal-test [--dry-run] [--webhook-url URL]
```

**Options:**
- `--dry-run`: Test without sending actual webhook
- `--webhook-url URL`: Override webhook URL for testing

## AI Agent API

### Programmatic Interface

#### `AIAgent` Class

```python
from falconer.ai.agent import AIAgent
from falconer.config import Config

# Initialize agent
config = Config()
agent = AIAgent(config)

# Start autonomous mode
await agent.start_autonomous_mode()

# Get agent status
status = await agent.get_agent_status()
```

#### Key Methods

##### `start_autonomous_mode()`
Start the autonomous earning mode with continuous decision cycles.

```python
async def start_autonomous_mode(self) -> None:
    """Start the autonomous earning mode."""
```

##### `stop_autonomous_mode()`
Stop the autonomous earning mode.

```python
async def stop_autonomous_mode(self) -> None:
    """Stop the autonomous earning mode."""
```

##### `get_agent_status()`
Get current status and metrics of the AI agent.

```python
async def get_agent_status(self) -> Dict[str, Any]:
    """Get current status of the AI agent."""
    return {
        "is_active": bool,
        "model": str,
        "host": str,
        "state": AIAgentState,
        "recent_decisions_count": int,
        "last_decision_time": str
    }
```

### AI Agent State

```python
class AIAgentState(BaseModel):
    """Current state of the AI agent."""
    
    is_active: bool = False
    current_balance_sats: int = 0
    daily_earnings_sats: int = 0
    active_strategies: List[str] = []
    last_decision_time: Optional[datetime] = None
    risk_level: str = "medium"  # low, medium, high
    confidence_score: float = 0.0
```

## Funding Proposals API

### Programmatic Interface

#### `FundingProposalManager` Class

```python
from falconer.funding.manager import FundingProposalManager

# Initialize manager
manager = FundingProposalManager(config, persistence, lnbits_adapter)

# Generate proposal
proposal = manager.generate_proposal(ai_context)

# List proposals
proposals = manager.list_proposals(status="pending")

# Update proposal status
manager.update_proposal_status(proposal_id, "approved", approval_data)
```

#### Key Methods

##### `generate_proposal(ai_context)`
Generate a new funding proposal based on AI context.

```python
def generate_proposal(self, ai_context: Dict[str, Any]) -> FundingProposal:
    """Generate a funding proposal based on AI context."""
```

##### `list_proposals(status=None)`
List funding proposals with optional status filtering.

```python
def list_proposals(self, status: Optional[str] = None) -> List[FundingProposal]:
    """List funding proposals with optional status filtering."""
```

##### `update_proposal_status(proposal_id, status, data)`
Update the status of a funding proposal.

```python
def update_proposal_status(
    self, 
    proposal_id: str, 
    status: str, 
    data: Optional[Dict[str, Any]] = None
) -> FundingProposal:
    """Update proposal status with optional additional data."""
```

### Funding Proposal Schema

```python
class FundingProposal(BaseModel):
    """Funding proposal data structure."""
    
    proposal_id: str
    created_at: datetime
    requested_amount_sats: int
    justification: str
    roi_analysis: Dict[str, Any]
    market_context: Dict[str, Any]
    status: str  # pending, approved, rejected, expired
    n8n_workflow_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    approval_data: Optional[Dict[str, Any]] = None
```

## Market Analysis API

### Programmatic Interface

#### `MarketAnalyzer` Class

```python
from falconer.ai.market_analyzer import MarketAnalyzer

# Initialize analyzer
analyzer = MarketAnalyzer(config)

# Analyze current conditions
market_data = await analyzer.analyze_current_conditions()

# Perform deep analysis
deep_analysis = await analyzer.perform_deep_analysis()
```

#### Key Methods

##### `analyze_current_conditions()`
Analyze current market conditions and fee rates.

```python
async def analyze_current_conditions(self) -> Dict[str, Any]:
    """Analyze current Bitcoin market conditions."""
    return {
        "fee_rates": Dict[str, float],
        "mempool_health": Dict[str, Any],
        "market_trends": Dict[str, Any],
        "risk_assessment": str,
        "timestamp": datetime
    }
```

##### `perform_deep_analysis()`
Perform comprehensive market analysis with historical data.

```python
async def perform_deep_analysis(self) -> Dict[str, Any]:
    """Perform deep market analysis with historical context."""
```

## Policy Engine API

### Programmatic Interface

#### `PolicyEngine` Class

```python
from falconer.policy.engine import PolicyEngine

# Initialize policy engine
engine = PolicyEngine(config)

# Validate action
is_allowed = engine.validate_action(action, context)

# Get policy limits
limits = engine.get_policy_limits()
```

#### Key Methods

##### `validate_action(action, context)`
Validate if an action is allowed under current policy.

```python
def validate_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Validate if action is allowed under current policy."""
```

##### `get_policy_limits()`
Get current policy limits and restrictions.

```python
def get_policy_limits(self) -> Dict[str, Any]:
    """Get current policy limits and restrictions."""
```

## Webhook Server API

### HTTP Endpoints

#### `POST /webhook/approval`
Handle funding proposal approval notifications from n8n.

**Request Body:**
```json
{
    "proposal_id": "string",
    "status": "approved|rejected",
    "workflow_id": "string",
    "approval_data": {
        "approved_by": "string",
        "approval_time": "ISO8601",
        "notes": "string"
    }
}
```

**Response:**
```json
{
    "success": true,
    "message": "Proposal status updated",
    "proposal_id": "string"
}
```

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "ISO8601",
    "version": "string"
}
```

### Webhook Server Class

```python
from falconer.funding.webhook_server import WebhookServer

# Initialize server
server = WebhookServer(config, proposal_manager)

# Start server
await server.start(host="0.0.0.0", port=8080)

# Stop server
await server.stop()
```

## Configuration API

### Environment Variables

#### Bitcoin Node Configuration
```bash
BITCOIN_RPC_URL=http://localhost:8332
BITCOIN_RPC_USER=your-rpc-user
BITCOIN_RPC_PASSWORD=your-rpc-password
BITCOIN_RPC_TIMEOUT=30
```

#### Lightning Network Configuration
```bash
LNBITS_URL=https://your-lnbits-instance.com
LNBITS_API_KEY=your-api-key
LNBITS_WALLET_ID=your-wallet-id
```

#### AI Configuration
```bash
OLLAMA_MODEL=llama3.1:8b
OLLAMA_HOST=http://localhost:11434
OLLAMA_TIMEOUT=60
```

#### Funding Proposals Configuration
```bash
FUNDING_PROPOSAL_ENABLED=true
FUNDING_PROPOSAL_THRESHOLD_SATS=10000
FUNDING_PROPOSAL_MAX_PENDING=3
FUNDING_PROPOSAL_EXPIRY_HOURS=24
```

#### n8n Integration Configuration
```bash
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/falconer
N8N_SHARED_SECRET=your-secret-key
N8N_TIMEOUT=30
```

#### Policy Limits Configuration
```bash
MAX_DAILY_SPEND_SATS=50000
MAX_SINGLE_TX_SATS=10000
MAX_DAILY_PROPOSALS=5
RISK_TOLERANCE=medium
```

### Configuration Class

```python
from falconer.config import Config

# Load configuration
config = Config()

# Access configuration values
bitcoin_url = config.bitcoin_rpc_url
lnbits_key = config.lnbits_api_key
ollama_model = config.ollama_model
```

## Error Handling

### Common Error Types

#### `FalconerError`
Base exception for all Falconer-specific errors.

```python
class FalconerError(Exception):
    """Base exception for Falconer errors."""
    pass
```

#### `ConfigurationError`
Raised when configuration is invalid or missing.

```python
class ConfigurationError(FalconerError):
    """Configuration error."""
    pass
```

#### `PolicyViolationError`
Raised when an action violates policy rules.

```python
class PolicyViolationError(FalconerError):
    """Policy violation error."""
    pass
```

#### `MarketAnalysisError`
Raised when market analysis fails.

```python
class MarketAnalysisError(FalconerError):
    """Market analysis error."""
    pass
```

### Error Response Format

```json
{
    "error": {
        "type": "FalconerError",
        "message": "Human readable error message",
        "code": "ERROR_CODE",
        "details": {
            "field": "Additional error details"
        }
    }
}
```

## Rate Limiting

### Default Limits
- **Market Analysis**: 10 requests per minute
- **Funding Proposals**: 5 proposals per hour
- **AI Decisions**: 1 decision per 5 minutes in autonomous mode
- **Webhook Endpoints**: 100 requests per minute

### Custom Limits
Rate limits can be configured via environment variables:

```bash
RATE_LIMIT_MARKET_ANALYSIS=10
RATE_LIMIT_PROPOSALS=5
RATE_LIMIT_AI_DECISIONS=1
RATE_LIMIT_WEBHOOK=100
```

## Authentication

### API Key Authentication
Some endpoints require API key authentication:

```bash
curl -H "X-API-Key: your-api-key" \
     https://your-falconer-instance.com/api/status
```

### Webhook Authentication
Webhook endpoints use shared secret authentication:

```bash
curl -H "X-Webhook-Secret: your-shared-secret" \
     -H "Content-Type: application/json" \
     -d '{"proposal_id": "123", "status": "approved"}' \
     https://your-falconer-instance.com/webhook/approval
```

## Examples

### Complete AI Agent Setup

```python
import asyncio
from falconer.config import Config
from falconer.ai.agent import AIAgent

async def main():
    # Load configuration
    config = Config()
    
    # Initialize AI agent
    agent = AIAgent(config)
    
    # Start autonomous mode
    await agent.start_autonomous_mode()
    
    # Let it run for a while
    await asyncio.sleep(3600)  # 1 hour
    
    # Stop the agent
    await agent.stop_autonomous_mode()

if __name__ == "__main__":
    asyncio.run(main())
```

### Funding Proposal Workflow

```python
from falconer.funding.manager import FundingProposalManager
from falconer.funding.n8n_adapter import N8nAdapter

async def create_funding_proposal():
    # Initialize components
    manager = FundingProposalManager(config, persistence, lnbits_adapter)
    n8n_adapter = N8nAdapter(config)
    
    # Generate proposal
    ai_context = {
        "current_balance_sats": 5000,
        "market_conditions": market_data,
        "active_strategies": ["fee_analysis", "mempool_monitoring"]
    }
    
    proposal = manager.generate_proposal(ai_context)
    
    # Send to n8n for approval
    response = await n8n_adapter.send_proposal(proposal)
    
    print(f"Proposal sent: {proposal.proposal_id}")
    print(f"n8n workflow ID: {response.get('workflow_id')}")
```

### Custom Market Analysis

```python
from falconer.ai.market_analyzer import MarketAnalyzer

async def analyze_market():
    analyzer = MarketAnalyzer(config)
    
    # Get current conditions
    current = await analyzer.analyze_current_conditions()
    
    # Perform deep analysis
    deep = await analyzer.perform_deep_analysis()
    
    # Combine results
    analysis = {
        "current": current,
        "deep": deep,
        "recommendation": "buy" if current["fee_rates"]["fast"] < 10 else "wait"
    }
    
    return analysis
```

---

For more examples and advanced usage patterns, see the [Strategy Development Guide](strategies.md) and [Security Guide](security.md).
