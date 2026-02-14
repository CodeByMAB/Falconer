# OpenClaw Skills for Falconer Integration

This directory contains OpenClaw skills that integrate with the Falconer Bitcoin API to provide Bitcoin market analysis, blockchain monitoring, and transaction tracking capabilities.

## 📦 Bitcoin Market Analyzer Skill

The `bitcoin_market_analyzer.py` skill provides comprehensive Bitcoin network monitoring and analysis capabilities for OpenClaw.

### Features

- **Blockchain Monitoring**: Track block height, difficulty, and network health
- **Mempool Analysis**: Monitor transaction backlog and fee market conditions
- **Fee Estimation**: Get real-time fee estimates for different confirmation targets
- **Market Analysis**: AI-powered market conditions and opportunity assessment
- **Address Tracking**: Query Bitcoin address balances and transaction history
- **Transaction Monitoring**: Track specific Bitcoin transactions

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Configuration

Set these environment variables in your OpenClaw container:

```bash
FALCONER_API_URL=http://falconer-api:8000
FALCONER_API_KEY=your-secure-api-key
```

### Usage

The skill provides two main interfaces:

#### 1. Direct API Access (for development/testing)

```python
from bitcoin_market_analyzer import BitcoinMarketAnalyzer

# Initialize the analyzer
analyzer = BitcoinMarketAnalyzer()

# Get blockchain information
blockchain = analyzer.get_blockchain_info()
print(f"Current block height: {blockchain['blocks']}")

# Get mempool status
mempool = analyzer.get_mempool_info()
print(f"Mempool size: {mempool['size']} transactions")

# Get fee estimates
fees = analyzer.get_fee_estimates()
print(f"Fast fee: {fees['fast']} sats/vbyte")

# Get comprehensive analysis
analysis = analyzer.get_comprehensive_analysis()
print(f"Opportunity score: {analysis['market']['opportunity_score']}")
```

#### 2. OpenClaw Skill Interface (for production use)

```python
from bitcoin_market_analyzer import openclaw_skill_main

# Execute skill with specific command
result = openclaw_skill_main("analysis")

if result["status"] == "success":
    analysis = result["data"]
    print(f"Blockchain height: {analysis['blockchain']['blocks']}")
    print(f"Opportunity score: {analysis['market']['opportunity_score']}")
else:
    print(f"Error: {result['error']}")

# Get specific information
address_result = openclaw_skill_main("address", address="bc1qtest123")
transaction_result = openclaw_skill_main("transaction", tx_id="abc123")
```

### API Endpoints Used

- `GET /api/bitcoin/blockchain-info` - Blockchain status
- `GET /api/bitcoin/mempool-info` - Mempool statistics
- `GET /api/bitcoin/fee-estimates` - Fee estimates
- `GET /api/bitcoin/network-stats` - Network health
- `GET /api/bitcoin/market-analysis` - AI analysis
- `GET /api/bitcoin/address-info` - Address information
- `GET /api/bitcoin/transaction` - Transaction details

## 🚀 Integration with OpenClaw

### Docker Setup

The skills are designed to work with the existing Docker setup:

```bash
# Start the PoC environment
docker-compose -f ops/docker-compose.poc.yml up -d
```

### OpenClaw Configuration

Add the skills directory as a volume in your `docker-compose.poc.yml`:

```yaml
services:
  openclaw:
    volumes:
      - openclaw-skills:/app/skills
      - ./openclaw-skills:/app/custom-skills  # Add this line
    environment:
      - FALCONER_API_URL=http://falconer-api:8000
      - FALCONER_API_KEY=${FALCONER_API_KEY:-default-key}
```

### Skill Registration

Register the skill in your OpenClaw configuration:

```javascript
// In your OpenClaw config
skills: {
  bitcoinMarketAnalyzer: {
    path: '/app/custom-skills/bitcoin_market_analyzer.py',
    enabled: true,
    description: 'Bitcoin market analysis and monitoring',
    commands: {
      analysis: 'Get comprehensive Bitcoin market analysis',
      blockchain: 'Get blockchain information',
      mempool: 'Get mempool status',
      fees: 'Get fee estimates',
      network: 'Get network statistics',
      market: 'Get market analysis',
      address: 'Query Bitcoin address (requires address parameter)',
      transaction: 'Query Bitcoin transaction (requires tx_id parameter)'
    }
  }
}
```

### OpenClaw Usage Examples

Users can interact with the skill through OpenClaw's interface:

```
!bitcoin analysis              # Comprehensive analysis
!bitcoin blockchain           # Blockchain info
!bitcoin mempool              # Mempool status
!bitcoin fees                 # Fee estimates
!bitcoin address bc1qtest123  # Address query
!bitcoin tx abc123def456       # Transaction query
```

## 🔧 Development

### Creating New Skills

1. **Create a new Python file** in this directory
2. **Follow the pattern** of existing skills
3. **Add dependencies** to `requirements.txt` if needed
4. **Test locally** before deploying to OpenClaw

### Testing

```bash
# Run the example analysis
python bitcoin_market_analyzer.py
```

### Dependencies

- Python 3.9+
- `requests` - HTTP client
- `python-dotenv` - Environment variable management

## 📚 API Documentation

For complete API documentation, see:
- [OpenClaw API Documentation](../docs/openclaw-api.md)
- [Falconer API Reference](../docs/api.md)

## 🛡️ Security

- **API Key Authentication**: All requests to Falconer API require authentication
- **Environment Variables**: Never commit API keys to version control
- **Error Handling**: Skills include comprehensive error handling
- **Timeouts**: All HTTP requests have timeouts to prevent hanging

## 📝 License

MIT License - see [LICENSE](../LICENSE) for details.