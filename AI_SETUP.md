# Falconer AI Integration Setup Guide

This guide will help you set up Falconer with AI capabilities using vLLM (OpenAI-compatible API) for autonomous Bitcoin earning.

## Prerequisites

### 1. Install and Run vLLM

vLLM serves an OpenAI-compatible API. Install and run it on your system:

**Install vLLM:**
```bash
pip install vllm
```

**Start vLLM server** (with a supported model, e.g. from Hugging Face or local path):

```bash
# Example: serve a model (adjust model name to your setup)
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3.2-3B-Instruct \
  --host 0.0.0.0 \
  --port 8000
```

The API will be available at `http://localhost:8000/v1` (OpenAI-compatible).

**Verify it's working:**
```bash
curl http://localhost:8000/v1/models
```

### 2. Model Selection

Use any model compatible with vLLM. Examples:

- **Small/fast**: 3B-class models (e.g. Llama-3.2-3B-Instruct)
- **Balanced**: 7B–8B models (e.g. meta-llama/Llama-3.1-8B-Instruct)
- **Larger**: 13B+ for higher quality (more GPU/RAM required)

The model name you pass to vLLM (e.g. `meta-llama/Llama-3.1-8B-Instruct`) is what you set as `VLLM_MODEL` in Falconer.

## Falconer AI Setup

### 1. Install Dependencies

```bash
# Install Falconer with AI dependencies
pip install -e .

# AI stack uses OpenAI client to talk to vLLM
pip install openai langchain numpy pandas scikit-learn schedule
```

### 2. Configure Environment

Add AI configuration to your `.env` file:

```bash
# AI Configuration (vLLM)
VLLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
VLLM_BASE_URL=http://localhost:8000/v1
AI_RISK_TOLERANCE=medium
AI_CONFIDENCE_THRESHOLD=0.6
AI_DECISION_INTERVAL_MINUTES=5

# Existing Bitcoin configuration
BITCOIND_RPC_USER=bitcoin
BITCOIND_RPC_PASS=your_rpc_password
LNBITS_API_KEY=your_lnbits_api_key
LNBITS_WALLET_ID=your_wallet_id
```

### 3. Test AI Integration

```bash
# Test AI market analysis
python -m falconer.cli ai-analyze

# List available earning strategies
python -m falconer.cli ai-strategies

# Check AI agent status
python -m falconer.cli ai-status
```

## AI Earning Strategies

Falconer includes several AI-driven earning strategies:

### 1. Fee Intelligence Service
- **Description**: Generate comprehensive fee intelligence reports
- **Base Price**: 1,000 sats (10k sats)
- **Risk Level**: Low
- **Requirements**: Bitcoin Core, Electrs, Mempool data

### 2. Mempool Monitoring
- **Description**: Real-time mempool monitoring and congestion alerts
- **Base Price**: 500 sats (5k sats)
- **Risk Level**: Low
- **Requirements**: Mempool data, real-time updates

### 3. Transaction Optimization
- **Description**: Optimize transaction timing and fee rates
- **Base Price**: 800 sats (8k sats)
- **Risk Level**: Medium
- **Requirements**: Fee estimation, timing analysis, UTXO analysis

### 4. Market Analysis
- **Description**: Deep market analysis and trend predictions
- **Base Price**: 1,500 sats (15k sats)
- **Risk Level**: Medium
- **Requirements**: Historical data, trend analysis, prediction models

### 5. Lightning Network Services
- **Description**: Lightning Network routing and payment services
- **Base Price**: 200 sats (2k sats)
- **Risk Level**: Low
- **Requirements**: Lightning node, routing capacity

## Autonomous Mode

### Start Autonomous Earning

```bash
# Start AI agent in autonomous mode
python -m falconer.cli ai-start

# With custom model
python -m falconer.cli ai-start --model meta-llama/Llama-3.1-8B-Instruct

# With custom vLLM base URL
python -m falconer.cli ai-start --base-url http://192.168.1.100:8000/v1
```

### Monitor AI Performance

```bash
# Check AI agent status
python -m falconer.cli ai-status

# View market analysis
python -m falconer.cli ai-analyze

# List strategies with performance metrics
python -m falconer.cli ai-strategies
```

### Manual Strategy Execution

```bash
# Execute specific strategy
python -m falconer.cli ai-execute --strategy fee_intelligence

# Dry run (simulate without creating services)
python -m falconer.cli ai-execute --strategy mempool_monitoring --dry-run
```

## AI Decision Making Process

The AI agent follows this decision-making process:

1. **Market Analysis**: Analyzes current Bitcoin network conditions
2. **Opportunity Detection**: Identifies earning opportunities
3. **Strategy Selection**: Chooses optimal earning strategy
4. **Risk Assessment**: Evaluates risks and policy compliance
5. **Execution**: Creates Lightning invoices and services
6. **Learning**: Updates performance metrics and adjusts strategies

### Decision Factors

- **Market Conditions**: Fee trends, mempool congestion, network activity
- **Opportunity Score**: Calculated based on market analysis (0.0-1.0)
- **Risk Tolerance**: Configurable (low, medium, high)
- **Policy Limits**: Daily spending limits, transaction limits
- **Historical Performance**: Success rates, earnings history

## Configuration Options

### AI Risk Tolerance

```bash
# Conservative approach
AI_RISK_TOLERANCE=low

# Balanced approach (default)
AI_RISK_TOLERANCE=medium

# Aggressive approach
AI_RISK_TOLERANCE=high
```

### Decision Interval

```bash
# Make decisions every 5 minutes (default)
AI_DECISION_INTERVAL_MINUTES=5

# More frequent decisions
AI_DECISION_INTERVAL_MINUTES=2

# Less frequent decisions
AI_DECISION_INTERVAL_MINUTES=10
```

### Confidence Threshold

```bash
# Only execute high-confidence decisions
AI_CONFIDENCE_THRESHOLD=0.8

# Balanced confidence (default)
AI_CONFIDENCE_THRESHOLD=0.6

# Execute lower-confidence decisions
AI_CONFIDENCE_THRESHOLD=0.4
```

## Troubleshooting

### Common Issues

**1. vLLM Connection Failed**
```bash
# Check if vLLM server is running
curl http://localhost:8000/v1/models

# Ensure VLLM_BASE_URL in .env matches (e.g. http://localhost:8000/v1)
```

**2. Model Not Found**
- Use the exact model name vLLM is serving (see vLLM logs or `/v1/models`).
- Set `VLLM_MODEL` to that name (e.g. `meta-llama/Llama-3.1-8B-Instruct`).

**3. AI Decisions Not Executing**
- Check policy limits in your configuration
- Verify Lightning Network connectivity
- Ensure sufficient balance for service creation

**4. Low Performance**
- Use a smaller model (3B instead of 8B)
- Increase decision interval
- Lower confidence threshold

### Performance Optimization

**Hardware Requirements:**
- **Minimum**: 8GB RAM, 4 CPU cores (small models only)
- **Recommended**: 16GB RAM, 8 CPU cores or GPU
- **Optimal**: 32GB RAM, 16 CPU cores or capable GPU

**Model Selection:**
- **3B class**: Fast, good for basic decisions
- **7B–8B**: Balanced performance and capability
- **13B+**: Best quality, requires more resources

## Security Considerations

### Local AI Processing
- All AI processing can run locally with vLLM
- No data need be sent to external services
- Bitcoin private keys never exposed to AI

### Policy Enforcement
- All AI decisions checked against policy engine
- Spending limits enforced
- Risk assessments validated

### Air-Gapped Signing
- AI can only create PSBT proposals
- Human approval required for actual transactions
- No hot signing capabilities

## Monitoring and Analytics

### Performance Metrics
- Daily earnings tracking
- Strategy success rates
- Decision confidence scores
- Market opportunity detection accuracy

### Logging
- All AI decisions logged with reasoning
- Market analysis results stored
- Performance metrics tracked over time

### Alerts
- Policy violations
- Low performance periods
- Market opportunity alerts
- System health monitoring

## Advanced Configuration

### Custom Strategies
You can extend Falconer with custom earning strategies by implementing the `EarningStrategy` interface.

### Model Fine-tuning
For specialized Bitcoin analysis, you can fine-tune models with Bitcoin-specific data.

### Integration with External Services
The AI can be extended to integrate with external Bitcoin services and APIs.

## Support

For issues and questions:
- Check the logs: `tail -f falconer.log`
- Review configuration: `python -m falconer.cli ai-status`
- Test individual components: `python -m falconer.cli ai-analyze`

## Example Workflow

1. **Setup**: Install vLLM and start the API server with your model
2. **Configure**: Set `VLLM_BASE_URL` and `VLLM_MODEL` in `.env`
3. **Test**: Run `ai-analyze` to verify setup
4. **Start**: Launch autonomous mode with `ai-start`
5. **Monitor**: Use `ai-status` to track performance
6. **Optimize**: Adjust risk tolerance and intervals based on results

The AI agent will now autonomously analyze Bitcoin market conditions and create earning opportunities while respecting your policy limits and risk tolerance.

## Funding Proposals & n8n Integration

### Overview

Falconer's AI agent can autonomously request additional Bitcoin when its balance runs low. Instead of directly accessing funds, it generates detailed funding proposals that are sent to you via n8n for approval. This maintains human-in-the-loop control while enabling autonomous operation.

### Configuration

Add to your `.env` file:

```bash
# Funding Proposal Settings
FUNDING_PROPOSAL_ENABLED=true
FUNDING_PROPOSAL_THRESHOLD_SATS=50000  # Request funds when balance drops below 50k sats
FUNDING_PROPOSAL_DEFAULT_AMOUNT_SATS=500000  # Request 500k sats by default
FUNDING_PROPOSAL_MAX_PENDING=3  # Maximum 3 pending proposals at once
FUNDING_PROPOSAL_EXPIRY_HOURS=24  # Proposals expire after 24 hours

# n8n Integration
N8N_WEBHOOK_URL=https://your-n8n.com/webhook/falconer-proposal
N8N_WEBHOOK_AUTH_TOKEN=your_bearer_token
N8N_WEBHOOK_SECRET=your_hmac_secret_key

# Webhook Server
WEBHOOK_SERVER_HOST=0.0.0.0
WEBHOOK_SERVER_PORT=8080
```

### n8n Workflow Setup

**1. Create Proposal Reception Workflow:**
- Add Webhook node (POST) to receive proposals from Falconer
- Configure authentication (Bearer token or Header Auth)
- Extract proposal data: proposal_id, requested_amount_sats, justification, intended_use, expected_roi_sats
- Format notification message for human review
- Send notification via your preferred channel (Email, Slack, SMS, etc.)
- Include approval/rejection buttons or links

**2. Create Approval Response Workflow:**
- Add HTTP Request node to send approval to Falconer webhook
- POST to `http://your-falconer-host:8080/webhook/approval`
- Include headers: X-Signature (HMAC-SHA256), X-Timestamp
- Body: `{"proposal_id": "...", "status": "approved", "approved_by": "human_name", "approval_notes": "..."}`
- Calculate HMAC signature: `HMAC-SHA256(timestamp + body, N8N_WEBHOOK_SECRET)`

### Starting the Webhook Server

```bash
# Start webhook server to receive approvals
python -m falconer.cli webhook-server

# Or run in background
nohup python -m falconer.cli webhook-server > webhook.log 2>&1 &
```

### Managing Proposals

```bash
# List all proposals
falconer proposals list

# Show specific proposal
falconer proposals show <proposal-id>

# View statistics
falconer proposals stats

# Manually approve (for testing)
falconer proposals approve <proposal-id> --notes "Approved for testing"

# Test n8n integration
falconer proposal-test --amount 100000
```

### Proposal Lifecycle

1. **Generation**: AI agent detects low balance and generates proposal with detailed justification
2. **Submission**: Proposal sent to n8n webhook with all details
3. **Notification**: n8n sends notification to human via configured channel
4. **Review**: Human reviews proposal and decides to approve/reject
5. **Approval**: n8n sends approval notification to Falconer webhook server
6. **Execution**: Falconer creates PSBT for approved amount
7. **Signing**: Human signs PSBT air-gapped and broadcasts transaction
8. **Completion**: Proposal marked as executed with transaction ID

### Security Considerations

- All webhook communications use HMAC-SHA256 signatures for authentication
- Proposals expire after 24 hours if not approved
- Maximum pending proposals limit prevents spam
- Webhook server validates signatures and timestamps
- PSBT creation still requires human signing (air-gapped)
- No hot wallet access - AI cannot spend funds directly

### Troubleshooting

**Proposals not appearing in n8n:**
- Check N8N_WEBHOOK_URL is correct
- Verify n8n webhook is active (production URL)
- Check n8n logs for incoming requests
- Test with `falconer proposal-test`

**Approvals not reaching Falconer:**
- Ensure webhook server is running
- Check WEBHOOK_SERVER_PORT is accessible
- Verify N8N_WEBHOOK_SECRET matches in both systems
- Check webhook server logs for signature validation errors

**Proposals expiring too quickly:**
- Increase FUNDING_PROPOSAL_EXPIRY_HOURS
- Check n8n notification delivery time
- Ensure human has sufficient time to review
