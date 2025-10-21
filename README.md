# Falconer 🦅

**A Bitcoin-native AI agent that autonomously hunts for insights and earns sats while maintaining human custody and security.**

Falconer is an intelligent Bitcoin earning system that combines AI decision-making with strict security controls. It operates as a semi-autonomous agent that can analyze market conditions, execute earning strategies, and manage funding proposals—all while keeping your private keys secure through air-gapped signing and policy-enforced limits.

## 🎯 Core Philosophy

Falconer operates on three fundamental principles:

- **🔐 Security First**: No hot signing, only PSBT proposals for air-gapped approval
- **💰 Autonomous Earning**: AI-driven micro-services and market analysis to generate sats
- **👤 Human Oversight**: Policy engine ensures every action stays within approved budgets and rules

## 🏗️ Architecture

### Security Model
- **Air-gapped Signing**: All transactions require manual PSBT signing on offline devices
- **Allowance Wallet**: LNbits/LND integration with strict spending caps and allowlists
- **Policy Engine**: Every action validated against configurable budgets and risk rules
- **Multi-layer Validation**: Market analysis, risk assessment, and human approval gates

### AI Components
- **Market Analyzer**: Real-time Bitcoin market condition analysis using multiple data sources
- **Decision Engine**: Ollama-powered AI that makes earning decisions based on market data
- **Strategy Manager**: Executes and manages various Bitcoin earning strategies
- **Autonomous Agent**: Self-managing system that operates within defined parameters

### Earning Strategies
- **Micro-services**: Deploy small Bitcoin-payable services (APIs, data feeds, etc.)
- **Market Analysis**: Provide fee intelligence and mempool insights
- **Arbitrage Opportunities**: Identify and execute profitable Bitcoin operations
- **Custom Strategies**: Extensible framework for new earning methods

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Bitcoin Core/Knots node
- LNbits or LND instance
- Ollama (for AI capabilities)

### Installation
```bash
# Clone the repository
git clone https://github.com/CodeByMAB/Falconer.git
cd Falconer

# Install dependencies
pip install -e .

# Copy and configure environment
cp .env.example .env
# Edit .env with your Bitcoin node and LNbits endpoints
```

### Basic Usage
```bash
# Run development checks
make dev

# Generate fee intelligence sample
python -m falconer.cli fee-brief

# Check mempool health
python -m falconer.cli mempool-health

# Start autonomous AI agent
python -m falconer.cli ai-agent --autonomous
```

## 🤖 AI Agent Features

### Autonomous Operation
The AI agent runs continuous cycles that:
1. **Analyze Market Conditions**: Real-time fee rates, mempool status, and market trends
2. **Assess Wallet Balance**: Monitor LNbits balance and earning performance
3. **Make Decisions**: Use AI to determine optimal earning strategies
4. **Execute Actions**: Deploy services, adjust pricing, or wait for better conditions
5. **Learn & Adapt**: Improve decisions based on historical performance

### Market Intelligence
- **Fee Analysis**: Real-time Bitcoin fee rate monitoring and prediction
- **Mempool Health**: Network congestion analysis and transaction timing
- **Market Trends**: Price movement analysis and opportunity identification
- **Risk Assessment**: Dynamic risk level adjustment based on market conditions

## 💸 Funding Proposals & n8n Integration

Falconer can autonomously generate funding proposals when its Bitcoin balance runs low. The system integrates with n8n for human approval workflows.

### How It Works
1. **Balance Monitoring**: AI agent continuously monitors wallet balance during autonomous cycles
2. **Threshold Detection**: When balance drops below configured threshold, funding proposal is triggered
3. **AI Justification**: System generates detailed proposal with ROI analysis and market justification
4. **Human Approval**: Proposal sent to n8n webhook for human review via email, Slack, SMS, etc.
5. **PSBT Creation**: Approved proposals trigger PSBT generation for air-gapped signing
6. **Fund Transfer**: After manual signing, funds are transferred to the allowance wallet

### Setup
```bash
# 1. Configure n8n integration in .env
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/falconer
N8N_SHARED_SECRET=your-secret-key

# 2. Start webhook server for approvals
python -m falconer.cli webhook-server

# 3. Enable funding proposals in AI configuration
FUNDING_PROPOSAL_ENABLED=true
FUNDING_PROPOSAL_THRESHOLD_SATS=10000
```

### Commands
```bash
# List all funding proposals
falconer proposals list

# Show detailed proposal information
falconer proposals show <proposal-id>

# View proposal statistics and performance
falconer proposals stats

# Start webhook server for handling approvals
falconer webhook-server

# Test n8n integration
falconer proposal-test
```

## 🔧 Configuration

### Environment Variables
Key configuration options in `.env`:

```bash
# Bitcoin Node
BITCOIN_RPC_URL=http://localhost:8332
BITCOIN_RPC_USER=your-rpc-user
BITCOIN_RPC_PASSWORD=your-rpc-password

# Lightning Network
LNBITS_URL=https://your-lnbits-instance.com
LNBITS_API_KEY=your-api-key

# AI Configuration
OLLAMA_MODEL=llama3.1:8b
OLLAMA_HOST=http://localhost:11434
FUNDING_PROPOSAL_ENABLED=true

# Policy Limits
MAX_DAILY_SPEND_SATS=50000
MAX_SINGLE_TX_SATS=10000
FUNDING_PROPOSAL_THRESHOLD_SATS=10000
```

### Policy Engine
Configure spending limits and risk parameters:
- Daily spending caps
- Maximum single transaction amounts
- Risk tolerance levels
- Strategy-specific limits
- Time-based restrictions

## 📊 Monitoring & Analytics

### Real-time Metrics
- Current wallet balance and daily earnings
- Active earning strategies and their performance
- Market condition analysis and fee predictions
- AI decision history and success rates
- Funding proposal statistics

### Logging & Observability
- Structured logging with configurable levels
- Performance metrics and timing data
- Error tracking and alerting
- Decision audit trails
- Market analysis history

## 🛡️ Security Considerations

### Key Management
- **No Hot Wallets**: Private keys never stored on internet-connected devices
- **PSBT Workflow**: All transactions require air-gapped signing
- **Multi-signature Support**: Configurable for additional security
- **Hardware Wallet Integration**: Compatible with popular hardware wallets

### Operational Security
- **Policy Enforcement**: All actions validated against configured rules
- **Rate Limiting**: Built-in protection against rapid-fire transactions
- **Audit Trails**: Complete logging of all decisions and actions
- **Emergency Stops**: Manual override capabilities for immediate shutdown

## 🔄 Development

### Project Structure
```
src/falconer/
├── ai/                 # AI agent and decision engine
├── adapters/           # External service integrations
├── funding/            # Funding proposal system
├── policy/             # Policy engine and validation
├── tasks/              # Background tasks and utilities
└── wallet/             # PSBT and wallet management
```

### Testing
```bash
# Run all tests
make test

# Run specific test suites
python -m pytest tests/test_ai.py
python -m pytest tests/test_funding.py
python -m pytest tests/test_policy.py
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run `make dev` to ensure quality
5. Submit a pull request

## 📚 Documentation

- **[AI Setup Guide](AI_SETUP.md)**: Detailed AI configuration and n8n workflow examples
- **[API Documentation](docs/api.md)**: Complete API reference
- **[Security Guide](docs/security.md)**: Security best practices and recommendations
- **[Strategy Development](docs/strategies.md)**: Guide to creating custom earning strategies

## ⚠️ Disclaimer

Falconer is experimental software designed for Bitcoin enthusiasts and developers. Always:
- Start with small amounts for testing
- Understand the risks of autonomous Bitcoin operations
- Keep your private keys secure and air-gapped
- Monitor the system regularly
- Have emergency procedures in place

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

**Built with ❤️ for the Bitcoin community. Hunt for sats, stay secure.**