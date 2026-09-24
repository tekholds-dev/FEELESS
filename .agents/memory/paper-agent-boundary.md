---
name: Paper agent boundary
description: Safety and product boundary for autonomous Cat experimentation before real Solana execution.
---

Paper Cats may use public provider snapshots to drive a clearly labeled paper ledger, but the client must never receive private key material or see paper balances, P/L, or activity presented as on-chain results.

**Why:** The first autonomous-agent loop needs to be testable without risking SOL or creating false performance claims.

**How to apply:** Keep paper wallet secrets server-side and encrypted, expose only public Cat data, mark every paper result in the UI and API, and require a separate adapter with wallet custody, signing, risk checks, and confirmed transaction lineage before enabling real execution.