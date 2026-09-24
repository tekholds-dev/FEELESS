---
name: Preview Cat persistence
description: Restart-safe lifecycle storage for preview Paper Cats and the recovery-key secrecy boundary.
---

Preview Paper Cat lifecycle state is stored in an atomic, permission-restricted local state file. The raw recovery key remains write-only; only its session-secret hash is durable, and all public Cat responses stay paper-labeled.

**Why:** The preview API can run without the production database, but losing recovery confirmation or expiry state across a process restart can revive an unfunded Cat or strand its owner.

**How to apply:** Keep recovery, funding, wallet-mode, coin-plan, expiry, and paper ledger mutations on the persistence path. Treat expired Cats as terminal until a separate, verified funding/recovery flow is designed.