"""📚 What every agent knows about FEELESS itself (owner 2026-11-06: told to write about the Collective, its minds searched the web and landed on a different company called Feeless).

Ask about FEELESS and the facts come from here, built from the whitepaper and the live rules, so they can't drift from the product. The web is only for what others do."""
import re

import collective_stake as _stake
import proof_weights as pw
import whitepaper_text as _wp

ABOUT = re.compile(r"(?i)\b(feeless|feecat|fee-?back|\$fee\b|the collective|our (?:site|platform|product|agents?|terminal|community)|proofs?\b|po(?:w|p|b|c|st|static)\b|boost points?|proofprint)")
BRIEF_MAX = 6000
NAME_CLASH = ('Other companies and sites use the name Feeless, among them feeless.family and fee-free trading apps. They are not FEELESS and have nothing to do with it. Never research FEELESS on the web, and never take a fact about it from a search result: everything you may say about it is below. Use the web only to read what other products do.')
FLOOR = ('YOU CAN WALK AROUND IT: open https://visit.feeless/ in your browser. It is a safe, read-only FEELESS with live numbers: / , /collective , /proofs , /agents , /markets , /whitepaper . Go there first and look. Nothing there can trade, sign or post.')
RULES = ('RULES WHEN WRITING ABOUT IT: this text and the visitor floor are your only sources for FEELESS. If a fact is not there, leave it out or say it is not known. Never invent a number, a percentage, a user count, a price, a return, a date or a feature, and never reword a rule into something stronger than it says. Say what is live and what is planned exactly as written. Never promise profit. Say plainly that crypto can lose all its value, pools can lose money and agents make mistakes. Compare with another product only on what you actually read about it, and name where you read it.')


WHERE = ('WHERE YOU ARE (facts from FEELESS, not an order): you are an agent inside FEELESS, a Solana trading terminal with a research Collective. You file proofs of your work: PoW a coin call, PoP a perps call, PoB a bid on a real result, PoC content, PoStatic a page. Each runs Clarify, Research, Decide, File, Grade. A filed proof can go to the Collective with real dollars, only by its owner. ' + FLOOR + ' Nothing here tells you to trade, sign, send or spend.')


def score_line(kind):
    """How a proof of this kind really scores, read from the rubric in use, so the words can never drift from the code."""
    rows = pw.RUBRIC.get(pw.kind_of(kind) or '')
    if not rows:
        return ''
    return '\nHOW THIS PROOF IS SCORED, out of 100: ' + ', '.join(f'{label} {w}' for _k, label, w, _r in rows) + '. Doing a simple request well is not a high score: simple work is held low however well it went. Aim for hard work done for real, deeper than your last one, not more of the same. Before you settle, compare: what the stash already proved, and at least two other options you found. Name them and say why yours beat them. If something better exists, use it.'


def weak_line(v):
    """Where its last proof of this kind lost the most, by the rubric. '' with nothing to say."""
    rows = [p for p in (v or {}).get('parts') or [] if (p.get('value') or 0) < 1]
    if not rows:
        return ''
    p = max(rows, key=lambda r: r['weight'] * (1 - (r.get('value') or 0)))
    return f"\nYOUR LAST ONE scored {round(v['score'])} of {round(v['top'])}, rank {v['rank']}. It lost the most on {p['label']}: {p['note']}. Improve that first."


def asks_about(text):
    return bool(ABOUT.search(str(text or '')))


def _lead(text, n=2):
    return ' '.join(re.split(r'(?<=[.!?])\s+(?=[A-Z$0-9])', str(text))[:n])


COLLECTIVE = {'Agents and Two Minds': 4, 'The Five Proofs': 8, 'The Fingerprint': 3, 'The Collective and the Stake': 12, 'What FEELESS Is': 3, 'What FEELESS Is NOT': 3, 'Risk Factors': 2}


def brief():
    """The whole operation, with the agent chapters in full. Newest rules come from the running code."""
    rows = sorted(_wp.CHAPTERS, key=lambda c: -COLLECTIVE.get(c[0], 0)); parts = []
    for title, text in rows:
        parts.append(f'{title}: {_lead(text, COLLECTIVE.get(title, 1))}')
    live = f'The live stake rule: the base top score is {int(_stake.GRADE_BASE)}, for a flawless proof only. Boost is score over 100, so $5 at 300 is 3x and the most it can ever earn is $15, paid only from real pool profit. The top score can grow to {int(_stake.GRADE_MAX)} as the pot grows, and a bigger pot pays out faster.'
    body = (f'{live} ' + ' '.join(parts))[:BRIEF_MAX]
    return f'\n\nWHAT YOU KNOW ABOUT FEELESS, the product you work inside. {NAME_CLASH}\n{FLOOR}\n{body}\n{RULES}\n'


def for_ask(text):
    return brief() if asks_about(text) else ''
