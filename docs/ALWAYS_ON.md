# Always-on host (so real cards are managed while your Mac sleeps)

Everything that trades or watches runs inside the backend as loops — the runner engine, Arena battles, the tier cards + Fuse-wallet
keeper, FeeCat, candles. Today they only run while your Mac is awake. One container runs them all, 24/7:

| # | Step | Where |
|---|------|-------|
| 1 | Create a project on **Railway** (https://railway.app) → *Deploy from GitHub repo* → pick this repo. | Railway |
| 2 | Settings → Build → **Dockerfile path** `deploy/Dockerfile`. | Railway |
| 3 | Add a **Volume** mounted at `/app/backend/data` (your cards, books, ledger, profiles live there — copy your current `backend/data` up once). | Railway › Volumes |
| 4 | Variables: paste everything from `backend/.env` (RPC / Helius, Alchemy, Jupiter, Circle `CIRCLE_API_KEY` + `ENTITY_SECRET`, admin wallets, `ALLOWED_ORIGINS` = your site, `FEELESS_TRUST_PROXY=1`). Never commit `.env`. | Railway › Variables |
| 5 | Networking: expose **5001** (trading API) and **5077** (reputation / Fuse / HQ API) as public domains; point the frontend `REACT_APP_*` API URLs at them. 5088 / 5099 stay internal. | Railway › Networking |
| 6 | Turn the Mac's backend OFF once the host is live (two keepers on one Fuse wallet would race). Keep the frontend wherever you host it. | you |
| 7 | Check: HQ › Lag catcher green, HQ › Fuse › 👛 shows the wallet, a tier card's next-round clock ticks. | HQ |

`deploy/run-all.sh` restarts any service that crashes. Logs: Railway › Deployments › Logs.
⚠ Only ONE place may run the backend against the Fuse wallet at a time.
