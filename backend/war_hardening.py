"""SEC-1 hardening list: recent real crypto-attack patterns (researched 2026-11-13) each turned into a concrete FEELESS defence item,
plus whether FEELESS already covers it. Static reference data the War Room renders; no network calls. Sources are named per row.
"""

# each: (id, attack, how it worked, FEELESS item, state: done|partial|todo, source)
ITEMS = [
    ('key-ops', 'Binance $6.3B (Oct 2026)', 'No contract bug — a compromised DevOps laptop led to key/infra control (FBI: TraderTraitor).',
     'Signing stays on the owner wallet only; server never holds a spend key; no key in env on a dev box.', 'done', 'crystalintelligence.com'),
    ('social-multisig', 'Drift $285M (Apr 2026)', 'In-person social engineering + Solana durable nonces got multisig signers to pre-authorise routine-looking txns.',
     'Every order shows coins/side/amount and is re-verified signed==quoted; no pre-authorised or resubmitted txns.', 'done', 'cryptotimes.io'),
    ('rpc-trust', 'KelpDAO $292M (Apr 2026)', 'Compromised internal RPC nodes fed false data to a bridge, releasing funds against a phantom burn.',
     'RPC reads are cross-checked (singleflight + pool + retry); money decisions never trust one node unverified.', 'partial', 'ccn.com'),
    ('addr-poison', 'Address poisoning (65M+ txns since 2025)', 'A lookalike address seeded into history; the victim copies it from history and sends to the attacker.',
     'Never copy a destination from history; the UI shows full address + a verified label before any send; warn on first-seen counterparties.', 'todo', 'blockaid.io'),
    ('sig-phish', 'Signature-phishing drainers (~$90M Solana H1-25)', 'Users tricked into approving a malicious txn / owner-reassignment; kits now bypass wallet simulation.',
     'Only sign an order matching what is on screen; refuse coin->coin with no SOL/USDC side; show the exact program + effect pre-sign.', 'partial', 'kerberus / dev.to'),
    ('owner-reassign', 'SlowMist $3M owner-permission tamper', 'A phishing txn changed the token-account owner authority of victims.',
     'Our flows never set owner/authority on a user account; a quote that would is refused and flagged.', 'done', 'slowmist'),
    ('drainer-sim-bypass', 'Drainer kits bypassing simulation (2026)', 'Kits craft txns that simulate benign then drain, defeating wallet preview.',
     'Server re-derives the expected effect and compares to the signed txn; a mismatch cancels — no resubmit.', 'partial', 'dev.to'),
    ('lazarus-approve', 'Lazarus $3.2M Solana (May 2025)', 'State actor tricked users into approving malicious transactions.',
     'High-value actions need a fresh signed order; staff-only routes gated by _is_staff; session replays revoked (War Room).', 'done', 'karcrypto.com'),
    ('session-theft', 'Stolen admin/session reuse', 'A lifted dashboard session reused from another machine.',
     'HQ signature bound to one device; reuse from a second device is revoked (War Room note_sig) and tarpitted (defence.seen_sig).', 'done', 'FEELESS'),
    ('scanner-recon', 'Automated recon / drainer infra scanning', 'Bots probe /.env, /wp-login, key-export paths before an attack.',
     'Decoys capture + canary the recon; a subnet sending many scanners is banned (War Room); learned UA rules block the tool.', 'done', 'FEELESS'),
]


def view():
    by = {}
    for i in ITEMS:
        by[i[4]] = by.get(i[4], 0) + 1
    return {'items': [{'id': i[0], 'attack': i[1], 'how': i[2], 'item': i[3], 'state': i[4], 'source': i[5]} for i in ITEMS],
            'counts': by, 'total': len(ITEMS)}


# ATTACKER-METHODS ENCYCLOPEDIA (defender view / "Hacking 101 for defenders"). How each attack CLASS works at a concept level and the signals
# a defender watches — so FEELESS knows what it is defending against. No targets, no payloads, no step-by-step offense: this is threat
# intel (MITRE-ATT&CK style), the exact opposite of an offensive kit, which stays OFF THE TABLE per the SEC-1 card.
ENCYCLOPEDIA = [
    ('recon', 'Reconnaissance & scanning', 'Attackers map a target before striking: automated bots request known-sensitive paths (/.env, admin panels, key exports), fingerprint servers and enumerate endpoints.',
     'Decoys at those paths, captured + canaried; subnet bans on many scanners; learned rules on scanner user-agents; no server version leakage.'),
    ('phishing', 'Phishing & fake sites', 'Lookalike domains and fake wallet-connect pages trick users into signing. Typosquats and paid search ads impersonate the real app.',
     'Users bookmark the real domain; we never ask for seed phrases/keys; signing shows the exact effect; wallet-connect only from our origin.'),
    ('drainer', 'Wallet drainers & malicious approvals', 'A crafted transaction or token-approval, often simulating benign, actually transfers assets or hands over account authority on sign.',
     'Only sign an order matching the on-screen coins/side/amount; server re-derives expected effect vs the signed txn; refuse owner/authority changes.'),
    ('addr-poison', 'Address poisoning', 'A lookalike address is seeded into the victim\'s history so a later copy-paste sends funds to the attacker.',
     'Full address + verified label shown before send; never copy a destination from history; first-seen counterparty warnings.'),
    ('key-compromise', 'Key & infrastructure compromise', 'Malware on a dev/ops machine, leaked secrets in env or repos, or a poisoned dependency give attackers the signing keys or server control.',
     'No spend key on the server; secrets never in env on a dev box or in git; least-privilege; the owner wallet signs money, nothing else can.'),
    ('social-eng', 'Social engineering of signers', 'Trust is built over time (even in person), then signers are nudged to approve a "routine" transaction or pre-authorise one.',
     'No pre-authorised or resubmitted txns; every money action re-verifies signed==quoted; multi-party review for anything that moves funds.'),
    ('supply-chain', 'Supply-chain & dependency attacks', 'A compromised npm/pip package or build step injects code that exfiltrates keys or alters transactions.',
     'Pinned dependencies; review of new packages; build integrity; the quote-vs-signed check catches an altered transaction at sign time.'),
    ('infra-trust', 'Trusting a single data source', 'A compromised RPC/oracle feeds false balances or prices, releasing funds against phantom state (bridge-style).',
     'RPC reads cross-checked across a pool with retry; money decisions never trust one unverified node; DexScreener + our own indexes, no single oracle.'),
    ('session-theft', 'Session / token theft & replay', 'A stolen admin session or API token is reused from another machine to act as the victim.',
     'HQ session bound to one device; reuse from a second device is revoked + tarpitted; short-lived signatures; scoped roles.'),
    ('laundering', 'Cash-out & laundering', 'Stolen funds are hopped through mixers and swaps to an exchange; tracing + fast exchange freezes are how real recoveries happen — not counter-hacks.',
     'On-chain trace of a suspect wallet + an evidence pack ready for an exchange compliance desk / IC3. FEELESS reports; it never attacks back.'),
]


def encyclopedia():
    return {'intro': 'How attacks work, so we can defend — threat intel for defenders, not an offensive guide. Each class maps to a FEELESS defence.',
            'entries': [{'id': e[0], 'name': e[1], 'how': e[2], 'defence': e[3]} for e in ENCYCLOPEDIA], 'total': len(ENCYCLOPEDIA)}
