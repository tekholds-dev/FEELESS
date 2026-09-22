---
name: Preview API boundary
description: The launch preview uses a same-origin Node API bridge when backend runtime variables are absent.
---

The preview can provide live public GeckoTerminal/DexScreener discovery and read-only contract routes without MongoDB or backend credentials. Wallet connection remains browser-controlled, while signed swap execution must stay disabled until a real Jupiter and Solana RPC backend is configured. Social mutations use a server-verified wallet message proof; client-supplied wallet identity or private-profile ownership is never sufficient.

**Why:** The workspace may start only the frontend and may not have backend packages, database variables, or trading credentials available; constructing `undefined/api/...` URLs caused the terminal to appear empty. Treating a query-string address as proof would also expose private profile data.

**How to apply:** Keep public discovery and read-only routes functional in preview, but do not silently claim on-chain balances, metadata supply, simulation, or execution when the production backend boundary is unavailable. Require a challenge signature for profile saves, chat posts, likes, replies, and flags; only authenticated self-reads may reveal private profile details.