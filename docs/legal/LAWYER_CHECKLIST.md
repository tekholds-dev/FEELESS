# ⚖ Lawyer checklist — the ONE read before real volume (drafted by Claude 2026-11-13; not legal advice)

Goal: one paid hour with a crypto/fintech lawyer, not ten. Send them this page, `docs/specs/money.md` › COUNSEL_BRIEF (the detailed
questions), and the three drafts in this folder. Answers become dated lines in `docs/RULINGS.md`.

## A · The owner decides before the call (RULINGS › Open questions)
1. Entity + state (an LLC is the usual minimum so the risk is not personal). 2. Is US traffic served for every feature? 3. Q2 custody, Q3 perps.

## B · Ranked by risk (highest first) — what to ask
| # | Feature | Why it is the risk | Ask |
|---|---|---|---|
| 1 | **Agent wallets on `auto`** (Crossmint, server signs) + COL-16 agent sends | Server-signed moves of user money = custody → money-transmitter (FinCEN MSB / state MTL) exposure; contradicts "non-custodial" | Is an API-key smart wallet we can sign for custody? What changes if the user's key is co-signer on every move? |
| 2 | **Real perps for US users** via Jupiter Perps (owner's call) | Leveraged crypto derivatives to US retail = CFTC territory; the venue is offshore-style | Does building + relaying the user-signed order make FEELESS an introducing broker? Geo-gate required? |
| 3 | **Swap fee (10%)** on non-custodial swaps | Fee inside a signed tx is usually fine; must stay non-custodial | Confirm no MSB/MTL exposure while the user signs every tx |
| 4 | **Agents proposing trades + public paper records** | Could read as investment advice / performance advertising | Is a "proposal + evidence, user signs" model advice? Disclaimer wording? |
| 5 | **Own tokens ($FEE, FEECAT, rFEE) + Launch wizard + creator revenue shares** | Securities exposure if anything promises profit | What we may and may not say; holder-tier fee discounts OK? |
| 6 | **Points → FEECAT, raffles, rep market, Bids/PoB, Familia raids** | Sweepstakes/lottery/betting rules when a prize has value | Free-entry structure OK? Which states block it? |
| 7 | **Real leverage (Jupiter Lend borrow), Money Desk deposits, brokers (SnapTrade)** | "Earn program" / retail commodity transaction / broker referral | Interface-only = fine? Disclaimers needed? |
| 8 | **Data: wallets, chats, proofs, Telegram** | Privacy law (CCPA if CA users), data deletion | Is the privacy draft enough? |

## C · Already in the product that helps
Users sign every swap · no pooled family money · fees off P&L · "non-custodial … not financial advice" banner · every money desk shows its risk line.

## D · Engineering the lawyer will likely ask for (cards, not built yet)
Per-feature geo-gate (today none exists) · terms acceptance on first wallet connect (versioned, stored per wallet) · data export/delete per wallet.
