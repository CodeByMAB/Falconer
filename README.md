# Falconer
A Bitcoin-native AI agent built to hunt for insights and earn sats —
while staying tethered to human custody.

- **No hot signing**: only PSBT proposals (you sign air-gapped).
- **Allowance wallet**: LNbits/LND with strict caps & allowlists.
- **Policy engine**: every action checked against budgets and rules.
- **Earning**: micro-services billed in sats.

## Quickstart
1. Copy `.env.example` → `.env` and fill Bitcoin Knots + LNbits endpoints.
2. `make dev` to run lint/type/test.
3. `python -m falconer.cli fee-brief` to generate a fee intel sample.
4. `python -m falconer.cli mempool-health` to check mempool status.