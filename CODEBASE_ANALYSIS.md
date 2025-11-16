# FALCONER CODEBASE ANALYSIS REPORT

## EXECUTIVE SUMMARY

Falconer is a sophisticated Bitcoin-native AI agent designed to autonomously earn satoshis while maintaining strict security controls through air-gapped PSBT signing and policy enforcement. The project integrates Bitcoin Core, Lightning Network (LNbits), and AI decision-making via Ollama.

**Status:** Alpha (v0.2.0) - Experimental software with significant architectural design but several critical configuration issues discovered.

---

## 1. PROJECT STRUCTURE AND PURPOSE

### Overall Purpose
Falconer is an autonomous Bitcoin earning system that:
- Uses AI (Ollama) to make earning decisions based on market conditions
- Implements various Bitcoin earning strategies (fee intelligence, mempool monitoring, market analysis)
- Maintains security through policy-enforced transaction limits
- Integrates with n8n for human-in-the-loop funding approval workflow
- Provides air-gapped PSBT creation for transaction signing

### Architecture Philosophy
- **Security First**: No hot wallets or direct key management
- **Autonomous Earning**: AI-driven decision making within policy constraints
- **Human Oversight**: Policy engine ensures all actions stay within budgets and rules
- **Bitcoin Native**: Direct Bitcoin Core RPC integration with PSBT workflows

---

## 2. MAIN MODULES AND RESPONSIBILITIES

### Core Module Organization
```
src/falconer/
├── ai/                          # AI decision-making and earning strategies
│   ├── agent.py                 # Main autonomous AI agent orchestrator
│   ├── decision_engine.py       # Decision-making logic based on market context
│   ├── market_analyzer.py       # Real-time Bitcoin market analysis
│   └── earning_strategies.py    # Pluggable earning strategy implementations
│
├── adapters/                    # External service integrations
│   ├── bitcoind.py              # Bitcoin Core RPC adapter
│   ├── electrs.py               # Electrs REST API integration
│   ├── lnbits.py                # Lightning Network wallet integration
│   └── mempool.py               # Mempool.space API with Tor support
│
├── funding/                     # Autonomous funding proposal system
│   ├── manager.py               # Funding proposal lifecycle management
│   ├── n8n_adapter.py           # n8n webhook integration
│   ├── webhook_server.py        # FastAPI webhook receiver for approvals
│   └── schema.py                # Pydantic models for funding data
│
├── policy/                      # Policy enforcement engine
│   ├── engine.py                # Policy validation and transaction blocking
│   └── schema.py                # Policy and transaction request models
│
├── wallet/                      # Bitcoin transaction management
│   └── psbt.py                  # PSBT creation, signing, and broadcast
│
├── tasks/                       # Background tasks
│   └── fee_brief.py             # Fee intelligence report generation
│
├── config.py                    # Configuration management
├── cli.py                       # Command-line interface
├── logging.py                   # Structured logging setup
├── persistence.py               # File-based data persistence
├── validation.py                # Address validation
└── exceptions.py                # Custom exception definitions
```

### Module Responsibilities

#### ai/agent.py - Core Orchestrator
- **Autonomous Cycle Loop**: Runs every 5 minutes analyzing market conditions
- **Decision Making**: Uses Ollama to make earning decisions (create_service, adjust_pricing, wait, analyze_market)
- **Balance Monitoring**: Tracks wallet balance and triggers funding proposals when below threshold
- **State Management**: Tracks active strategies, risk levels, and decision history
- **Learning**: Maintains decision history and adjusts risk based on success rates

Key Classes:
- `AIAgent`: Main autonomous agent
- `AIAgentState`: Current state tracking

#### ai/decision_engine.py - Strategy Selection
- Scores available strategies based on multiple factors
- Makes context-aware decisions based on market opportunity score
- Handles high (>0.7), medium (0.4-0.7), and low (<0.4) opportunity scenarios
- Tracks decision statistics and history

#### ai/market_analyzer.py - Market Intelligence
- Analyzes Bitcoin Core blockchain info, mempool status, and fee estimates
- Calculates opportunity scores and confidence levels
- Identifies earning opportunities (fee_intelligence, transaction_optimization, market_analysis)
- Maintains historical data for trend analysis (last 100 records)
- Supports both async and sync API calls

#### ai/earning_strategies.py - Revenue Generation
Implements 5 core earning strategies:
1. **Fee Intelligence** (1000 sats base): Generate market fee analysis reports
2. **Mempool Monitoring** (500 sats base): Real-time congestion monitoring
3. **Transaction Optimization** (800 sats base): Fee optimization advice
4. **Market Analysis** (1500 sats base): Trend predictions and insights
5. **Lightning Services** (200 sats base): Lightning Network routing and payments

Dynamic pricing adjusts based on:
- Historical success rates (±20% adjustment)
- Scarcity (time since last use)
- Market demand

#### funding/manager.py - Proposal Lifecycle
- Generates funding proposals when balance drops below threshold
- Calculates expected ROI based on active strategies
- Assesses risk levels from market data
- Manages proposal status transitions (pending → approved → executed)
- Automatically expires old pending proposals (configurable)

#### funding/n8n_adapter.py - Human Integration
- Sends proposals to n8n webhooks for human review/approval
- Implements HMAC-SHA256 signature verification for webhook authenticity
- Formats proposals with human-readable descriptions
- Supports optional bearer token authentication
- Enforces 5-minute webhook timestamp window

#### policy/engine.py - Transaction Gating
- Validates transactions against policy rules before execution
- Enforces:
  - Single transaction size limits
  - Daily aggregate spending caps
  - Destination address whitelisting
  - Fee rate limits
  - Persistent daily spending tracking
- Logs all policy violations for audit

#### wallet/psbt.py - Bitcoin Transactions
- Creates PSBT (Partially Signed Bitcoin Transaction) proposals
- Implements UTXO selection (greedy by amount)
- Estimates transaction fees and sizes
- Handles change address generation
- Provides finalization and broadcasting of signed PSBTs
- All transactions require air-gapped signing

#### adapters/ - External Integrations

**bitcoind.py**: Bitcoin Core RPC adapter
- JSON-RPC calls with error handling
- Methods: getblockchaininfo, getmempoolinfo, estimatesmartfee, gettransaction, listunspent, etc.
- Persistent HTTP client connection

**electrs.py**: Electrs REST API
- Address information and UTXO queries
- Transaction lookup and status
- Block information retrieval
- Public key infrastructure support

**lnbits.py**: Lightning Network wallet
- Invoice creation and payment
- Wallet balance queries
- Payment history and status
- LNURL integration

**mempool.py**: Mempool space API
- LAN endpoint first (for self-hosted mempool)
- Automatic fallback to Tor endpoint
- Supports SOCKS5 proxy for anonymity
- Configurable via environment variables

---

## 3. BITCOIN NODE INTEGRATION

### Integration Points

#### Direct Bitcoin Core Integration
1. **RPC Interface** (bitcoind.py)
   - HTTP-based JSON-RPC calls to Bitcoin Core/Knots
   - Configurable username/password authentication
   - Persistent connection for performance

2. **Market Data Sources**
   - blockchain info (block height, chain state)
   - mempool info (size, usage, transaction count)
   - fee estimation (estimatesmartfee for multiple confirmation targets)
   - raw mempool transactions (for analysis)

3. **Transaction Creation**
   - UTXO enumeration via listunspent
   - Raw transaction creation via createrawtransaction
   - PSBT creation via walletcreatefundedpsbt
   - Transaction broadcasting via sendrawtransaction

#### Architecture Flow
```
Bitcoin Core RPC
    ↓
BitcoinAdapter (HTTP+JSON-RPC)
    ↓
├── Market Analyzer (fee/mempool data)
├── PSBT Manager (UTXO selection, TX creation)
├── Fee Brief Task (fee intelligence)
└── Earning Strategies (service generation)
    ↓
Decision Engine → AI Agent (Ollama) → Action Execution
    ↓
LNbits (Payments) / Bitcoin TX (Broadcast)
```

#### Transaction Workflow
1. **Request Creation**: Application requests transaction with destination, amount, optional fee rate
2. **Policy Validation**: PolicyEngine validates against daily/single-TX limits
3. **PSBT Generation**: PSBTManager creates funded PSBT from available UTXOs
4. **Air-Gapped Signing**: PSBT exported for offline signing on secure device
5. **Finalization**: Once signed, PSBT finalized to raw transaction
6. **Broadcasting**: Raw transaction sent to Bitcoin network via RPC

### Security Model
- **No Hot Signing**: All private key operations offline
- **PSBT Format**: Industry-standard Partially Signed Bitcoin Transaction format
- **Multi-Sig Ready**: Policy engine supports multi-signature validation
- **Hardware Wallet Compatible**: Works with Ledger, Trezor, etc.

---

## 4. CONFIGURATION SYSTEM

### Configuration Files

#### Primary: .env File
Environment variable based configuration (Pydantic BaseSettings)

**Bitcoin Core Settings:**
- BITCOIND_SCHEME: http/https
- BITCOIND_HOST_LOCAL: 127.0.0.1
- BITCOIND_HOST_IP: IP or hostname
- BITCOIND_PORT: 8332
- BITCOIND_RPC_USER: RPC username
- BITCOIND_RPC_PASS: RPC password

**Electrs Settings:**
- ELECTRS_SCHEME, HOST_LOCAL, HOST_IP, PORT

**LNbits Settings:**
- LNBITS_SCHEME, HOST_LOCAL, HOST_IP, PORT
- LNBITS_API_KEY: Admin key for wallet
- LNBITS_WALLET_ID: Specific wallet ID

**Mempool Settings:**
- MEMPOOL_MODE: auto|lan|tor
- MEMPOOL_LAN_SCHEME, MEMPOOL_LAN_HOST_LOCAL, MEMPOOL_LAN_PORT
- MEMPOOL_TOR_URL: Onion address
- TOR_SOCKS_URL: SOCKS5 proxy for Tor

**Policy Settings:**
- POLICY_PATH: Path to policy JSON file
- MAX_DAILY_SPEND_SATS: Daily limit
- MAX_SINGLE_TX_SATS: Single transaction limit
- ALLOWED_DESTINATIONS: CSV of whitelisted addresses

**Wallet Settings:**
- CHANGE_ADDRESS: Optional specific change address

**Logging:**
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- LOG_FILE: Optional log file path

#### Secondary: Policy JSON Files
Located in `policy/` directory:
- `dev.policy.json`: Development policy (loose limits)
- `staging.policy.json`: Staging policy
- `prod.policy.json`: Production policy (strict limits)

Example production policy:
```json
{
  "version": "1.0",
  "budgets": {
    "daily_sats_cap": 100000,
    "weekly_sats_cap": 500000,
    "per_counterparty_caps": {}
  },
  "actions": {
    "allowed_categories": [
      "invoice.create",
      "pay.invoice",
      "http.get.whitelist"
    ],
    "allowlist_domains": [
      "lvk6m7wpccq7u7wzb6tkrsolzslfdfile74xuks33ofczahnejaeyoqd.local",
      "lvk6m7wpccq7u7wzb6tkrsolzslfdfile74xuks33ofczahnejaeyoqd.onion"
    ],
    "denylist_domains": []
  },
  "psbt_rules": {
    "max_fee_sat_per_vb": 25,
    "no_address_reuse": true,
    "min_change_value_sats": 15000,
    "consolidate_when_feerate_below": 3
  },
  "splits": {
    "ops_percent": 40,
    "reserve_psbt_proposal_percent": 60
  }
}
```

#### Configuration Classes (config.py)
- `Config`: Main Pydantic BaseSettings class
- Single instance loads from .env file
- Validates configuration on instantiation
- Properties auto-compute URLs (bitcoind_url, electrs_url, lnbits_url)
- Field validators ensure consistency (e.g., single_tx < daily_tx)

---

## 5. CRITICAL ISSUES AND CONCERNS

### ISSUE 1: MISSING CONFIGURATION PARAMETERS (CRITICAL)
**Severity:** CRITICAL  
**Status:** BLOCKING - Code cannot run properly

The following configuration parameters are referenced in code but NOT defined in config.py:

**Funding Proposal Parameters:**
- `funding_proposal_enabled` - Referenced in ai/agent.py:66, 152
- `funding_proposal_threshold_sats` - Referenced in funding/manager.py:26
- `funding_proposal_max_pending` - Referenced in ai/agent.py:157, funding/manager.py:33
- `funding_proposal_default_amount_sats` - Referenced in funding/manager.py:43
- `funding_proposal_expiry_hours` - Referenced in ai/agent.py:408

**n8n Webhook Parameters:**
- `n8n_webhook_url` - Referenced in funding/n8n_adapter.py:23
- `n8n_webhook_auth_token` - Referenced in funding/n8n_adapter.py:24
- `n8n_webhook_secret` - Referenced in funding/n8n_adapter.py:25
- `n8n_webhook_timeout_seconds` - Referenced in funding/n8n_adapter.py:26

**AI/Ollama Parameters:**
- `ollama_model` - Used with getattr fallback in ai/agent.py:53 (WORKS but not configurable)
- `ollama_host` - Used with getattr fallback in ai/agent.py:54 (WORKS but not configurable)

**Impact:** 
- Funding proposal system will crash at runtime with AttributeError
- n8n integration will crash at runtime with AttributeError
- Ollama integration falls back to hardcoded defaults (works but not user-configurable)

**Fix Required:** Add missing fields to config.py with appropriate defaults and environment variable bindings.

---

### ISSUE 2: INCOMPLETE OLLAMA/AI CONFIGURATION
**Severity:** HIGH  
**Status:** FUNCTIONAL but not configurable via environment

The Ollama integration uses hardcoded defaults with getattr fallback:
```python
self.ollama_model = getattr(config, 'ollama_model', 'llama3.1:8b')
self.ollama_host = getattr(config, 'ollama_host', 'http://localhost:11434')
```

While this works, it's not user-configurable and doesn't follow project's configuration pattern.

---

### ISSUE 3: ASYNC/SYNC MIXING AND POTENTIAL DEADLOCKS
**Severity:** MEDIUM  
**Status:** POTENTIAL RUNTIME ISSUES

**Observed Problems:**
1. **Blocking Operations in Async Code** (market_analyzer.py)
   - `self.bitcoin_adapter.get_blockchain_info()` - SYNC call in async context
   - `self.bitcoin_adapter.estimate_smart_fee()` - SYNC call in async context
   - Should use `asyncio.to_thread()` for thread pool execution

2. **Example** (market_analyzer.py:119-130):
   ```python
   # IN ASYNC FUNCTION
   blockchain_info = self.bitcoin_adapter.get_blockchain_info()  # ❌ BLOCKING SYNC CALL
   mempool_info = self.bitcoin_adapter.get_mempool_info()        # ❌ BLOCKING SYNC CALL
   ```

3. **Correct Pattern Exists** (but not used everywhere):
   ```python
   # IN agent.py:131 - CORRECT
   balance_info = await asyncio.to_thread(self.lnbits_adapter.get_wallet_balance)
   ```

**Impact:** 
- Market analysis will block the event loop
- Decision cycles may not run on schedule
- Potential deadlocks under high load

---

### ISSUE 4: EXCEPTION HANDLING GAPS
**Severity:** MEDIUM  
**Status:** PARTIAL COVERAGE

**Missing Exception Safety:**

1. **HTTP Adapter Error Recovery** (all adapters)
   - BitcoinAdapter, ElectrsAdapter, LNbitsAdapter all use generic exception handlers
   - No retry logic on transient failures
   - No circuit breaker pattern for cascading failures

2. **PSBT Manager** (wallet/psbt.py)
   - `_select_utxos()` uses greedy algorithm with hardcoded 10k sats buffer
   - May select insufficient UTXOs under high fee conditions
   - No fallback to smaller outputs or dust consolidation

3. **Market Analyzer** (ai/market_analyzer.py)
   - Returns default neutral values on errors (opportunity_score=0.5)
   - Hides actual network/connectivity issues
   - Could make poor decisions based on stale data

---

### ISSUE 5: POLICY VIOLATION LOGGING INCONSISTENCY
**Severity:** LOW  
**Status:** MINOR CODE QUALITY

In policy/engine.py:101, there's an inconsistency:
```python
# Line 51: Uses model.dump() for violations
self.persistence.save_policy_violation(violation.model_dump())

# Line 101: Uses dict() for warnings
self.persistence.save_policy_violation(violation.dict())  # ❌ DEPRECATED METHOD
```

The `.dict()` method is deprecated in Pydantic v2, should use `.model_dump()` consistently.

---

### ISSUE 6: NO CLEANUP ON COMPONENT INITIALIZATION FAILURE
**Severity:** MEDIUM  
**Status:** RESOURCE LEAK POTENTIAL

The AIAgent initialization (ai/agent.py:46-72) creates multiple adapters but doesn't clean them up if initialization fails:

```python
def __init__(self, config: Config):
    # ... initializations ...
    self.decision_engine = DecisionEngine(config)       # ✓
    self.market_analyzer = MarketAnalyzer(config)       # Creates 3 adapters
    self.strategy_manager = EarningStrategyManager(config)  # Creates 3 more adapters
    
    if FundingProposalManager and N8nAdapter and config.funding_proposal_enabled:
        # If this fails, earlier created adapters are not cleaned up
        self.proposal_manager = FundingProposalManager(...)
```

**Risk:** If funding module initialization fails, zombie HTTP connections remain open.

---

### ISSUE 7: MARKET ANALYZER STATE MANAGEMENT
**Severity:** LOW  
**Status:** DESIGN ISSUE

MarketAnalyzer keeps in-memory history (last 100 records) that's lost on restart:
```python
self.fee_history: List[Dict[str, Any]] = []        # Lost on restart
self.mempool_history: List[Dict[str, Any]] = []    # Lost on restart
```

This data should be persisted to PersistenceManager for trend analysis across restarts.

---

### ISSUE 8: OLLAMA RESPONSE PARSING IS FRAGILE
**Severity:** MEDIUM  
**Status:** FUNCTIONAL BUT RISKY

The JSON extraction from Ollama (ai/agent.py:273-307) uses string manipulation:
```python
json_start = response.find('{')        # ❌ Fragile
json_end = response.rfind('}') + 1     # ❌ Fragile
json_str = response[json_start:json_end]
```

If Ollama response contains JSON in explanation text, this breaks. Should use proper JSON decoder with fallback.

---

### ISSUE 9: LNBITS API KEY EXPOSURE
**Severity:** MEDIUM  
**Status:** CONFIGURATION ISSUE

LNbits adapter stores API key in plain HTTP header:
```python
self.client = httpx.Client(
    base_url=self.base_url,
    headers={"X-Api-Key": self.api_key},  # In HTTP if scheme is http://
    timeout=30.0,
)
```

**Risk:** If using HTTP instead of HTTPS, API keys are transmitted unencrypted.

**Mitigation:** Enforce HTTPS in production, document this requirement clearly.

---

### ISSUE 10: MEMPOOL ADAPTER TOR/SOCKS NOT PRODUCTION TESTED
**Severity:** MEDIUM  
**Status:** FEATURE INCOMPLETE

The Mempool adapter supports Tor and SOCKS proxies but:
- No timeout configuration for Tor (uses default 20-30 seconds)
- No retry logic for onion network failures
- No fallback if both LAN and Tor fail gracefully

---

## 6. ARCHITECTURE STRENGTHS

### Strong Design Aspects

1. **Modular Architecture**
   - Clear separation of concerns (adapters, AI, policy, wallet)
   - Easy to swap implementations (e.g., replace BitcoinAdapter)
   - Pluggable earning strategies

2. **Security-Focused**
   - PSBT workflow prevents private key exposure
   - Policy engine gates all spending
   - Multi-layer validation (policy → PSBT → broadcast)

3. **Async-Ready**
   - Async market analysis and decision loops
   - Background task scheduling (5-minute cycles)
   - FastAPI webhook server for integrations

4. **Well-Documented**
   - README with architecture overview
   - API documentation exists
   - Inline logging throughout

5. **Testing Infrastructure**
   - pytest with coverage reporting
   - Integration tests
   - Mock adapters for testing

---

## 7. MISSING FEATURES AND IMPROVEMENTS

### High Priority

1. **Configuration Completion**
   - Add funding proposal parameters to config.py
   - Add n8n webhook parameters to config.py
   - Add Ollama parameters to config.py
   - Environment variable support for all

2. **Async/Sync Consistency**
   - Wrap sync Bitcoin adapter calls with asyncio.to_thread()
   - Create async wrappers for blocking operations
   - Use asyncio properly throughout

3. **Error Recovery**
   - Implement retry logic with exponential backoff
   - Add circuit breaker pattern for failing services
   - Implement fallback strategies

### Medium Priority

4. **State Persistence**
   - Persist market analyzer history
   - Save decision history across restarts
   - Load previous state on startup

5. **Monitoring & Observability**
   - Add prometheus metrics
   - Export decision/execution logs
   - Create dashboard for real-time monitoring

6. **Testing**
   - Add more unit tests for core modules
   - Integration tests for end-to-end flows
   - Load testing for autonomous cycles

---

## 8. SECURITY CONSIDERATIONS

### Strengths
✓ Air-gapped PSBT signing prevents hot wallet risk
✓ Policy engine enforces budget limits
✓ HMAC-SHA256 webhook signature verification
✓ Structured logging for audit trails

### Weaknesses
✗ No rate limiting on webhook endpoints
✗ HTTP could expose LNbits API keys
✗ No encryption for persisted proposal data
✗ No secret rotation mechanism for webhooks

### Recommendations
1. Enforce HTTPS for all external communications
2. Implement API key rotation for LNbits
3. Encrypt sensitive data in persistence layer
4. Add rate limiting to webhook server
5. Implement request signing for webhook verification
6. Add audit logging for all approvals/rejections

---

## 9. PERFORMANCE CONSIDERATIONS

### Current Limitations
- Greedy UTXO selection may be inefficient
- Bitcoin adapter connections persist (good) but not pooled
- In-memory history limited to last 100 records
- Ollama responses not cached (each decision queries model)

### Optimization Opportunities
1. Implement UTXO consolidation strategy
2. Add connection pooling for HTTP clients
3. Cache common Ollama responses
4. Use local fee estimate caching
5. Implement lazy loading for adapters

---

## SUMMARY OF ISSUES BY SEVERITY

| Severity | Issue | Component | Status |
|----------|-------|-----------|--------|
| CRITICAL | Missing funding/n8n config params | config.py, funding/*, ai/agent.py | Blocking |
| HIGH | Incomplete Ollama config | ai/agent.py | Functional |
| MEDIUM | Async/sync blocking calls | market_analyzer.py, strategies.py | Potential |
| MEDIUM | Missing exception handling | all adapters | Partial |
| MEDIUM | Resource leak on init failure | ai/agent.py | Potential |
| MEDIUM | Mempool Tor not production tested | adapters/mempool.py | Feature |
| MEDIUM | LNbits API key HTTP exposure | adapters/lnbits.py | Configuration |
| LOW | Pydantic dict() vs model_dump() | policy/engine.py | Code Quality |
| LOW | Market analyzer state loss | ai/market_analyzer.py | Design |
| LOW | Fragile JSON parsing | ai/agent.py | Functional |

---

## RECOMMENDATIONS FOR NEXT STEPS

### Immediate (Week 1)
1. Add missing configuration parameters to config.py
2. Update .env.example with funding/n8n parameters
3. Fix async/sync mixing in market_analyzer.py
4. Test funding proposal system end-to-end

### Short Term (Week 2-3)
1. Implement retry logic for adapters
2. Add proper exception hierarchy
3. Persist market analyzer state
4. Create comprehensive integration tests

### Medium Term (Month 1)
1. Add monitoring and observability
2. Implement state persistence across restarts
3. Security audit and hardening
4. Load and stress testing

### Long Term
1. Performance optimization (caching, pooling)
2. Advanced strategy implementations
3. Multi-wallet support
4. Enterprise deployment capabilities

