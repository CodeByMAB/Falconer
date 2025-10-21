# Falconer Operations Runbooks

This document contains operational procedures and troubleshooting guides for Falconer.

## Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Regtest Environment](#regtest-environment)
- [Common Operations](#common-operations)
- [Troubleshooting](#troubleshooting)
- [Monitoring](#monitoring)

## Development Environment Setup

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Git

### Initial Setup

1. Clone the repository:
   ```bash
   git clone git@github.com:CodeByMAB/Falconer.git
   cd Falconer
   ```

2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   make setup
   ```

4. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration (but NOT API keys)
   
   # For API keys, use one of these secure methods:
   # Option 1: Environment variables
   export LNBITS_API_KEY="your_api_key_here"
   export BITCOIND_RPC_PASS="your_rpc_password_here"
   
   # Option 2: Separate secrets file (add to .gitignore)
   echo "LNBITS_API_KEY=your_api_key_here" > .env.secrets
   echo "BITCOIND_RPC_PASS=your_rpc_password_here" >> .env.secrets
   source .env.secrets
   ```

## Regtest Environment

### Starting the Regtest Environment

```bash
make regtest
```

This will start:
- Bitcoin Core in regtest mode
- Electrs for address/transaction indexing
- LNbits for Lightning Network functionality
- Bitcoin Explorer for block exploration

### Stopping the Regtest Environment

```bash
make regtest-down
```

### Regtest Configuration

The regtest environment uses the following configuration:

- **Bitcoin Core**: RPC on port 18443, P2P on port 18444
- **Electrs**: REST API on port 50001
- **LNbits**: Web interface on port 5000
- **Bitcoin Explorer**: Web interface on port 3000

### Generating Test Blocks

```bash
# Connect to Bitcoin Core container
docker exec -it falconer-bitcoind bitcoin-cli -regtest -rpcuser=bitcoin -rpcpassword=bitcoin generatetoaddress 101 $(bitcoin-cli -regtest -rpcuser=bitcoin -rpcpassword=bitcoin getnewaddress)
```

### Creating Test Transactions

```bash
# Get a new address
docker exec -it falconer-bitcoind bitcoin-cli -regtest -rpcuser=bitcoin -rpcpassword=bitcoin getnewaddress

# Send some test coins
docker exec -it falconer-bitcoind bitcoin-cli -regtest -rpcuser=bitcoin -rpcpassword=bitcoin sendtoaddress <address> 1.0

# Generate a block to confirm
docker exec -it falconer-bitcoind bitcoin-cli -regtest -rpcuser=bitcoin -rpcpassword=bitcoin generatetoaddress 1 $(bitcoin-cli -regtest -rpcuser=bitcoin -rpcpassword=bitcoin getnewaddress)
```

## Common Operations

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_policy.py

# Run with coverage
pytest --cov=src/falconer --cov-report=html
```

### Code Quality Checks

```bash
# Run all quality checks
make dev

# Format code
make format

# Lint code
make lint

# Type checking
make type-check
```

### CLI Operations

```bash
# Generate fee brief
python -m falconer.cli fee-brief

# Check system status
python -m falconer.cli status

# Get wallet balance
python -m falconer.cli balance

# Send transaction (dry run)
python -m falconer.cli send --address bc1q... --amount 10000 --dry-run
```

## Troubleshooting

### Common Issues

#### Bitcoin Knots Connection Issues

**Problem**: Cannot connect to Bitcoin Knots RPC

**Solutions**:
1. Check if Bitcoin Knots is running: `docker ps | grep bitcoind` (for regtest) or check systemd service
2. Verify RPC credentials in `.env` file
3. Check firewall settings
4. Ensure Bitcoin Knots is fully synced

#### Electrs Connection Issues

**Problem**: Electrs API not responding

**Solutions**:
1. Check Electrs container status: `docker logs falconer-electrs`
2. Verify Electrs is connected to Bitcoin Core
3. Check if Electrs has finished initial indexing
4. Restart Electrs container if needed

#### LNbits Connection Issues

**Problem**: Cannot connect to LNbits

**Solutions**:
1. Check LNbits container status: `docker logs falconer-lnbits`
2. Verify API key in `.env` file
3. Check if wallet ID is correct
4. Ensure LNbits has finished initialization

#### PSBT Creation Failures

**Problem**: PSBT creation fails

**Solutions**:
1. Check if wallet has sufficient funds
2. Verify UTXO availability
3. Check fee rate settings
4. Ensure destination address is valid

### Log Analysis

#### Viewing Logs

```bash
# View all container logs
docker-compose -f ops/docker-compose.regtest.yml logs

# View specific service logs
docker-compose -f ops/docker-compose.regtest.yml logs bitcoind
docker-compose -f ops/docker-compose.regtest.yml logs electrs
docker-compose -f ops/docker-compose.regtest.yml logs lnbits
```

#### Log Levels

Falconer uses structured logging with the following levels:
- `DEBUG`: Detailed information for debugging
- `INFO`: General information about operations
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failed operations
- `CRITICAL`: Critical errors that may cause system failure

### Performance Issues

#### High Memory Usage

**Symptoms**: System becomes slow, containers restart

**Solutions**:
1. Increase Docker memory limits
2. Optimize Bitcoin Core configuration
3. Use pruning for Bitcoin Core
4. Monitor Electrs memory usage

#### Slow Transaction Processing

**Symptoms**: Transactions take long to confirm

**Solutions**:
1. Check mempool status
2. Adjust fee rates
3. Monitor network congestion
4. Use replace-by-fee if supported

## Monitoring

### Health Checks

#### Bitcoin Knots Health

```bash
# Check blockchain info (for regtest)
docker exec -it falconer-bitcoind bitcoin-cli -regtest -rpcuser=bitcoin -rpcpassword=bitcoin getblockchaininfo

# Check mempool status (for regtest)
docker exec -it falconer-bitcoind bitcoin-cli -regtest -rpcuser=bitcoin -rpcpassword=bitcoin getmempoolinfo

# Check network info (for regtest)
docker exec -it falconer-bitcoind bitcoin-cli -regtest -rpcuser=bitcoin -rpcpassword=bitcoin getnetworkinfo

# For production Bitcoin Knots, use the configured RPC credentials
bitcoin-cli -rpcuser=your_user -rpcpassword=your_pass getblockchaininfo
```

#### Electrs Health

```bash
# Check tip height
curl http://localhost:50001/blocks/tip/height

# Check fee estimates
curl http://localhost:50001/fee-estimates
```

#### LNbits Health

```bash
# Check wallet balance
curl -H "X-Api-Key: your-api-key" http://localhost:5000/api/v1/wallet/your-wallet-id
```

### Metrics Collection

#### Key Metrics to Monitor

1. **Bitcoin Knots**:
   - Block height
   - Mempool size
   - RPC response time
   - Memory usage

2. **Electrs**:
   - Indexing progress
   - API response time
   - Memory usage
   - Disk usage

3. **LNbits**:
   - Wallet balance
   - Payment success rate
   - API response time

4. **Falconer**:
   - Transaction success rate
   - Policy violations
   - Fee estimation accuracy
   - Error rates

### Alerting

Set up alerts for:
- Bitcoin Knots RPC failures
- Electrs indexing issues
- LNbits API failures
- High error rates in Falconer
- Policy violations
- Unusual fee rate spikes

### Backup Procedures

#### Regular Backups

1. **Bitcoin Knots wallet**: Backup wallet.dat file
2. **LNbits data**: Backup SQLite database
3. **Configuration**: Backup .env file
4. **Logs**: Archive old log files

#### Backup Commands

```bash
# Backup Bitcoin Knots wallet (for regtest)
docker cp falconer-bitcoind:/home/bitcoin/.bitcoin/wallet.dat ./backups/

# For production Bitcoin Knots, backup from the actual data directory

# Backup LNbits database
docker cp falconer-lnbits:/app/data/lnbits.db ./backups/

# Backup configuration
cp .env ./backups/
```

## Security Considerations

### API Key Management

**NEVER commit API keys to the repository!**

1. **Keep secrets out of committed files:**
   - Use placeholder values in env files: `LNBITS_API_KEY=`
   - Set actual keys via environment variables or separate secrets files

2. **Secure key storage:**
   ```bash
   # Option 1: Environment variables (recommended)
   export LNBITS_API_KEY="your_actual_key"
   export BITCOIND_RPC_PASS="your_actual_password"
   
   # Option 2: Separate secrets file (add to .gitignore)
   echo "LNBITS_API_KEY=your_actual_key" > .env.secrets
   source .env.secrets
   ```

3. **Production deployment:**
   - Set API keys in systemd environment file on production server only
   - Use proper file permissions: `chmod 600 /opt/Falconer/ops/systemd/falconer.env`

### Access Control

1. Use strong RPC passwords
2. Restrict network access to services
3. Use API keys for LNbits
4. Implement rate limiting

### Key Management

1. Use hardware wallets for production
2. Implement proper key rotation
3. Use secure key storage
4. Regular security audits

### Network Security

1. Use TLS for external connections
2. Implement proper firewall rules
3. Monitor network traffic
4. Use VPN for remote access
