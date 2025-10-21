# Falconer AI Integration Setup Guide

This guide will help you set up Falconer with AI capabilities using Ollama for autonomous Bitcoin earning.

## Prerequisites

### 1. Install Ollama

First, install Ollama on your system:

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
Download from [ollama.ai](https://ollama.ai/download)

### 2. Download AI Model

Download a suitable model for Bitcoin analysis:

```bash
# Recommended model for Bitcoin analysis (8B parameters)
ollama pull llama3.1:8b

# Alternative models (choose based on your hardware):
ollama pull llama3.1:7b    # Smaller, faster
ollama pull llama3.1:13b   # Larger, more capable
ollama pull codellama:7b   # Code-focused model
```

### 3. Start Ollama Service

```bash
# Start Ollama service
ollama serve

# In another terminal, verify it's working
ollama list
```

## Falconer AI Setup

### 1. Install Dependencies

```bash
# Install Falconer with AI dependencies
pip install -e .

# Or install specific AI dependencies
pip install ollama langchain langchain-ollama numpy pandas scikit-learn schedule
```

### 2. Configure Environment

Add AI configuration to your `.env` file:

```bash
# AI Configuration
OLLAMA_MODEL=llama3.1:8b
OLLAMA_HOST=http://localhost:11434
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
python -m falconer.cli ai-start --model llama3.1:13b

# With custom Ollama host
python -m falconer.cli ai-start --host http://192.168.1.100:11434
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

**1. Ollama Connection Failed**
```bash
# Check if Ollama is running
ollama list

# Restart Ollama service
ollama serve
```

**2. Model Not Found**
```bash
# List available models
ollama list

# Pull the required model
ollama pull llama3.1:8b
```

**3. AI Decisions Not Executing**
- Check policy limits in your configuration
- Verify Lightning Network connectivity
- Ensure sufficient balance for service creation

**4. Low Performance**
- Use a smaller model (7b instead of 8b)
- Increase decision interval
- Lower confidence threshold

### Performance Optimization

**Hardware Requirements:**
- **Minimum**: 8GB RAM, 4 CPU cores
- **Recommended**: 16GB RAM, 8 CPU cores
- **Optimal**: 32GB RAM, 16 CPU cores

**Model Selection:**
- **llama3.1:7b**: Fast, good for basic decisions
- **llama3.1:8b**: Balanced performance and capability
- **llama3.1:13b**: Best quality, requires more resources

## Security Considerations

### Local AI Processing
- All AI processing happens locally with Ollama
- No data sent to external services
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

1. **Setup**: Install Ollama and download model
2. **Configure**: Set up environment variables
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

**Example n8n Workflow JSON:**

```json
{
  "nodes": [
    {
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "path": "falconer-proposal",
        "authentication": "headerAuth",
        "responseMode": "responseNode"
      }
    },
    {
      "name": "Format Message",
      "type": "n8n-nodes-base.function",
      "parameters": {
        "functionCode": "// Format proposal for human review\nconst proposal = items[0].json;\nreturn [{\n  json: {\n    message: `🤖 Falconer Funding Request\n\nAmount: ${proposal.requested_amount_sats} sats\nCurrent Balance: ${proposal.current_balance_sats} sats\n\nJustification:\n${proposal.justification}\n\nIntended Use:\n${proposal.intended_use}\n\nExpected ROI: ${proposal.expected_roi_sats} sats\nRisk: ${proposal.risk_assessment}\nTimeframe: ${proposal.time_horizon_days} days\n\nProposal ID: ${proposal.proposal_id}`\n  }\n}];"
      }
    },
    {
      "name": "Send Email",
      "type": "n8n-nodes-base.emailSend",
      "parameters": {
        "subject": "Falconer Funding Proposal",
        "text": "={{$json.message}}"
      }
    }
  ]
}
```

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
