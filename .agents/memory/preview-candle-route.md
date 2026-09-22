---
name: Preview candle route parity
description: The preview API must mirror production market candle routes for charts to work in Replit preview.
---

The frontend requests market candles through the same `/api/market/candles/{chain}/{address}` contract in preview and production. Keep the preview server's GeckoTerminal OHLCV route aligned with the backend route whenever chart behavior changes.

**Why:** Feed and pair routes can appear healthy while charts silently fail if the preview-only API omits the candle route.

**How to apply:** When changing chart components or market endpoints, test one discovered pool through the preview candle URL and verify a 200 response with a candle array.