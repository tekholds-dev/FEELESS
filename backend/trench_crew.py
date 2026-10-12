"""🪖 THE TRENCH CREW — hard-coded roles for TRENCHING (open mode) (owner, 2026-10-12: "a trench crew that keeps digging until it understands
what's happening, then lets Warden / Courier enforce only the few things that can actually blow up execution"). Pure + tested
(`tests/test_trench_crew.py`). The plain-words version is docs/TRENCH_CREW.md — change both together.

Tally discovers · Sherlock investigates · Weather contextualizes · Trigger times · Devil challenges · Warden sizes · Courier executes ·
Reaper manages · Archivist remembers · Judge improves.

The ONLY hard wall is the money boundary: can it be traded safely, can it be sold, is the data real, is the execution path healthy.
Everything before that is curious, adaptive and evidence-weighted — a confidence or size change, never a "no".
"""
from types import MappingProxyType as _frozen

CREW = _frozen({
    'tally':     ('MARKET TRUTH / DISCOVERY', 'says what is happening — newness · cap · price · liquidity · volume and buyer velocity · trades · acceleration · candle / tape freshness · source',
                  'never decides good / bad; a weird coin stays visible unless its data is unusable'),
    'sherlock':  ('DEEP INVESTIGATOR', 'chases public clues — deployer / funders · first buyers · clusters · bundles · early-wallet behaviour · site / X · narrative · copycats · prior launches · whales accumulating or distributing',
                  'never "no verification = reject": missing proof is UNKNOWN / UNPROVEN, a research state'),
    'weather':   ('MARKET CONTEXT', 'reads the whole trench — is Pump hot or dead, do launches follow through, do rugs dominate',
                  'changes how aggressive the desk sizes, never shuts the office (its size floor in trench mode is ×0.5)'),
    'trigger':   ('ENTRY TIMING', 'decides WHEN from the live FEELESS chart / tape — early acceleration · first pullback · reclaim · breakout · momentum resumption; newborn charts read as newborn',
                  'never needs a textbook setup or a long history'),
    'devil':     ('ADVERSARIAL THINKER', 'asks what could make us wrong and weighs each objection by severity',
                  'most objections are confidence deductions; only the hard wall is a no'),
    'warden':    ('RISK TRANSLATOR', 'answers "how much can we risk here?" — strong + uncertain = smaller; excellent = the creator cap',
                  'shrinks, never rejects (except execution health and a seat too small for its own costs)'),
    'courier':   ('EXECUTION TRUTH', 'confirms route · price · slippage · fill · signature · duplicate-order protection · that the coin can be bought AND sold, through the one keeper path',
                  'mechanically strict, zero opinion on narrative'),
    'reaper':    ('POSITION MANAGER', 'watches P/L velocity · peak · support · structure · liquidity · early-wallet exits · challengers on the LIVE chart every 6 seconds',
                  'never dumps an accelerating winner on a clock, never babysits a dead loser'),
    'archivist': ('MEMORY / EVIDENCE', 'stores what really happened — every round, source, entry reason, clue, P/L path, MFE / MAE, exit, outcome; wins and losses',
                  'never turns a pattern into an instant hard restriction'),
    'judge':     ('ACCOUNTABILITY / EVOLUTION', 'after a loss: selection · timing · size · hold · exit · execution · variance; after a win: what worked — adjusts WEIGHTS through repeated evidence',
                  'never adds a hard veto after a bad trade'),
})

# 🧱 THE HARD WALL — the money boundary. Nothing else may stop a trench buy.
HARD_WALL = ('no live price', 'no trades in the last 5 minutes', 'outside the universe (0 < cap < $200K, ≤ 6h)', 'pool under what the keeper can buy into',
             'market data invalid / malformed / a bot ladder', 'the live chart collapsing or distributing', 'the dev / creator dumping now',
             'no route back to SOL / a sell-back tax (keeper)', 'price far from market (keeper)', 'keeper halted / Courier BAD / office not live',
             'a seat too small for its own round-trip cost')

# ⚖ Devil's objection severities in trench mode: HARD → the wall; everything else is a confidence weight on the ranking
DEVIL_HARD = ('data_integrity', 'chart_bot_ladder')                      # corrupt data (sell impossibility / dev dump are checked by the wall itself)
DEVIL_STRONG = ('rug_meter', 'busted_read')                              # ×0.85 each (the coin's own danger, on evidence of THIS pass / its read's settled record)
DEVIL_MIN = 0.6                                                          # all objections together never cut a coin's rank below ×0.6


def devil_factor(row, strong=None):
    """→ (factor, [evidence ids]) — Devil CHALLENGES: each piece of evidence against the coin (row `ev`, trench_kernel.senses.evidence) is
    a confidence deduction (strong ×0.85 — or the live Devil generation's own `strong` — other ×0.95), floored. The paper desk's
    objections (`objs` / `drule`) are not read."""
    objs = [o[0] for o in (row or {}).get('ev') or [] if o]
    m, s_ = 1.0, (0.85 if strong is None else max(0.75, min(0.9, float(strong))))
    for o in objs:
        if o in DEVIL_HARD:
            continue   # the wall handles these (market data)
        m *= s_ if o in DEVIL_STRONG else 0.95
    return max(DEVIL_MIN, round(m, 3)), objs


def dev_dumping(row):
    """The one Devil objection that IS the wall: the creator / dev selling into us right now (early-wallet pressure HIGH from the creator)."""
    li = (row or {}).get('li') or {}
    return li.get('press') == 'HIGH' and 'creator' in str(li.get('pressWhy') or '').lower()


# 🛡 Warden in trench mode: these rules SHRINK (never below SHRINK_FLOOR); only the execution rules can veto
WARDEN_SHRINK = ('W0', 'W2', 'W4', 'W20', 'W21')   # the brain's own uncertainty · weather · a newborn · early-wallet exit risk · concentrated holders
WARDEN_EXEC = ('W1', 'W3', 'W17')            # execution health · pool share · each open seat its share of the cash
SHRINK_FLOOR = 0.5


def warden_rules(rules):
    """Trench-mode filter for the Warden's rule hits: execution rules as they are; uncertainty rules shrink to ≥ ×SHRINK_FLOOR; the rest drop."""
    out = []
    for r in rules or []:
        rid = str(r.get('id') or '').split(' ')[0]
        if rid in WARDEN_EXEC:
            out.append(r)
        elif rid in WARDEN_SHRINK:
            out.append({**r, 'mult': max(SHRINK_FLOOR, float(r.get('mult') or 0)), 'why': f"{r.get('why')} — trench mode: size, not a no"})
    return out
