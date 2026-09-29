# Bounded recovery checkpoint

Implemented in this pass:
- Replaced the incorrectly labelled local-call-ledger chat integration with Pump's current coin-activity callout contract, in both Python and preview APIs.
- Chat retains the latest three returned callouts timestamped before coin entry, then appends/deduplicates new arrivals every 15 seconds. Author, message, entry market cap, timestamp, and original Pump link are displayed. Polling is not a websocket and cannot guarantee no gaps outside the provider's returned window.
- Removed automatic reopening of the global previous coin when entering Trenches.
- Preserved provider market-cap ordering for Python Pump top coins (previously reordered oldest first).

External blocker:
- Verified Pump's published client contract on 2026-09-29: GET /coin-activity/{mint}, includeCallouts=true. The live endpoint returned 401 without authorization; old /replies/{mint} returned 404.
- Deployment requires legitimately authorized `PUMP_CALLOUT_TOKEN` server-side. No credentials were read, copied, invented, or committed. UI reports unavailable until access works. Authenticated end-to-end import remains unverified. Never present local calls as Pump users' calls.

Still needs separate bounded work, not certified complete:
- FeeCat runtime diagnosis, strategy settings and dip-add risk controls; paper execution must not be represented as real execution.
- Badge command-center mechanics/UI validation.
- Bolt ranking provenance and shared reputation-hook race (duplicate hook consumers can miss the same response).
- Remaining historical fee/treasury/reward requests require separate verification; no assurance of fund destinations is made by this checkpoint.

Do not overwrite unrelated work or force-push main. Current delivery branch: recovery/codex-sept28.
