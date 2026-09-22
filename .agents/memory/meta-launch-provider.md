---
name: Meta Launch provider boundary
description: Non-custodial contract and readiness rules for the Meta Launch deployment flow.
---

The Meta Launch provider boundary is intentionally opt-in: an approved provider URL, explicit approval flag, and Solana RPC endpoint must all be configured before deployment is enabled. The provider prepares unsigned transactions for each launch phase; the browser validates the connected wallet as fee payer, requests wallet signatures after review, submits through RPC, and reports confirmed, failed, or uncertain/pending results.

**Why:** FEELESS must not hold private keys or claim a launch succeeded based only on a provider response. RPC confirmation is the source of truth for submitted transactions, while an unknown confirmation must remain pending.

**How to apply:** Keep provider credentials server-side or in the provider service. Only expose public client configuration (`REACT_APP_LAUNCH_API_URL`, approval status, provider name/network, and Solana RPC URL) to the frontend, and preserve the review gate before any wallet request.