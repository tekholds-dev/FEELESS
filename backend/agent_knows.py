"""📚 What every agent knows about FEELESS itself (owner 2026-11-06: told to write about the Collective, its minds searched the web and landed on a different company called Feeless).

Ask about FEELESS and the facts come from here, built from the whitepaper and the live rules, so they can't drift from the product. The web is only for what others do."""
import re

import collective_stake as _stake
import whitepaper_text as _wp

ABOUT = re.compile(r"(?i)\b(feeless|feecat|fee-?back|\$fee\b|the collective|our (?:site|platform|product|agents?|terminal|community)|proofs?\b|po(?:w|p|b|c|st|static)\b|boost points?|proofprint)")
BRIEF_MAX = 6000
NAME_CLASH = ('Other companies and sites use the name Feeless, among them feeless.family and fee-free trading apps. They are not FEELESS and have nothing to do with it. Never research FEELESS on the web, and never take a fact about it from a search result: everything you may say about it is below. Use the web only to read what other products do.')
FLOOR = ('YOU CAN WALK AROUND IT: open https://visit.feeless/ in your browser. It is a safe, read-only FEELESS with live numbers: / , /collective , /proofs , /agents , /markets , /whitepaper . Go there first and look. Nothing there can trade, sign or post.')
RULES = ('RULES WHEN WRITING ABOUT IT: this text and the visitor floor are your only sources for FEELESS. If a fact is not there, leave it out or say it is not known. Never invent a number, a percentage, a user count, a price, a return, a date or a feature, and never reword a rule into something stronger than it says. Say what is live and what is planned exactly as written. Never promise profit. Say plainly that crypto can lose all its value, pools can lose money and agents make mistakes. Compare with another product only on what you actually read about it, and name where you read it.')


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
