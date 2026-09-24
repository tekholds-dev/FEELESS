---
name: Paper brain adapters
description: Provider-backed Cat recommendations and the safety boundary around them.
---

Paper Cats may ask a configured, server-side brain adapter for a buy, sell, or hold recommendation from a market snapshot. When credentials are missing or a provider fails, the transparent rule engine must take over and the audit event must identify that fallback.

**Why:** Brain selection should change paper decisions without creating a path to wallet custody, signing, or transaction broadcast.

**How to apply:** Keep adapter credentials server-side, pass no wallet or transaction material to providers, expose availability and estimated per-cycle cost before running, and retain the paper-only execution boundary.