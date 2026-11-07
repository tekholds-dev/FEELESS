"""🔁 ONE LOOP FOR EVERY PROOF (owner 2026-11-05). Each proof runs the same loop as a PoW: clarify, research, decide, file, grade. What differs is its steps, how far it digs, and what it falls back on when it finds too little. A kind's agent asks first in chat unless its owner set that kind to just do it. Pure."""
import re

KINDS = ('pow', 'pop', 'pob', 'poc', 'pos')
LOOP = ('Clarify', 'Research', 'Compare', 'Decide', 'File', 'Grade')   # owner 2026-11-06: find and compare better before settling, stash included
PLANS = {
    'pow': {'code': 'PoW', 'what': 'a trade', 'steps': {'Research': 'Scout coins, 2 snapshots a site, every coin checked again', 'Decide': '3 turns pick one coin, its size and exits', 'File': 'Bought on FEELESS, watched until it sells', 'Grade': 'By its real result'}, 'fallback': 'If the coins look bad, it files a no-trade instead of forcing one.',
            'question': 'Anything to avoid or prefer before I look?', 'chips': ['Go', 'Only safer coins', 'Newest coins', 'Keep it small']},
    'pop': {'code': 'PoP', 'what': 'a perp call', 'steps': {'Research': 'Each mind reads 2 free sources of its own', 'Decide': 'Each calls blind, against true prices', 'File': 'A practice trade runs', 'Grade': 'By the practice result'}, 'fallback': 'If the sources disagree or say nothing, it files no trade.',
            'question': 'Any market or side you have in mind?', 'chips': ['Go', 'BTC', 'SOL', 'Whatever looks best']},
    'pob': {'code': 'PoB', 'what': 'a pick', 'steps': {'Research': 'One good search, then 4 sites, 3 to 6 steps on each, one snapshot a site', 'Decide': 'Each mind picks blind, then they compare', 'File': 'Nothing staked', 'Grade': 'When the real result is in'}, 'fallback': 'If it reads too little, it uses the free scores and market odds, and says so. If there is still nothing, it files no picks.',
            'question': 'Which sport or event, and how many picks?', 'chips': ['Go, best games now', 'NFL', 'NBA', 'Just 2 picks', '3 leg parlay', '5 leg parlay']},
    'poc': {'code': 'PoC', 'what': 'a post idea', 'steps': {'Research': 'Reads 5 trend sources, snapshots what it finds', 'Decide': 'Each mind pitches an angle and a post', 'File': 'Nothing is posted', 'Grade': 'By your mark and what it earned'}, 'fallback': 'If trends are thin, it works from your notes and says so.',
            'question': 'Any topic, and which platform?', 'chips': ['Go, whatever fits me', 'X', 'TikTok', 'YouTube']},
    'pos': {'code': 'PoStatic', 'what': 'a page', 'steps': {'Research': 'Reads the best current builds a visitor can open', 'Decide': 'Writes a plan for you to approve', 'File': 'One mind builds, the other reviews', 'Grade': 'By your mark'}, 'fallback': 'If it finds no references, it builds from its own judgment and says so.',
            'question': 'What should it do, and who is it for?', 'chips': []},
}
ASK_TTL_S = 3600
_NO = re.compile(r'(?i)^\s*(no|stop|cancel|never ?mind|nah)\b')
_GO = re.compile(r'(?i)^\s*(go|yes|yep|yeah|do it|ok|okay|sure|y)\b[\s,.!]*(?:,?\s*(?:best games now|whatever fits me|whatever looks best))?\s*$')
_POC = re.compile(r'(?i)^\s*(?:file|make|start)\s+a\s+poc\b')


def auto(cat, kind):
    return bool(((cat or {}).get('proofCfg') or {}).get('auto', {}).get(kind))


def set_auto(cat, kind, on):
    if kind not in KINDS:
        raise ValueError('Pick one of the proofs.')
    cfg = dict((cat.get('proofCfg') or {})); a = dict(cfg.get('auto') or {}); a[kind] = bool(on); cfg['auto'] = a; cat['proofCfg'] = cfg
    return cfg


def public():
    return {'loop': list(LOOP), 'plans': {k: {x: v[x] for x in ('code', 'what', 'steps', 'fallback')} for k, v in PLANS.items()}}


def kind_of(text, pow_cmd, pop_cmd, pob_cmd, pob_topic):
    """Which proof a chat line asks for, or None."""
    if _POC.match(str(text or '')):
        return 'poc'
    if pob_topic or pob_cmd:
        return 'pob'
    if pop_cmd:
        return 'pop'
    if pow_cmd:
        return 'pow'
    return None


def ask_message(kind, now):
    p = PLANS[kind]; steps = ' → '.join(p['steps'].values())
    return {'by': 'cats', 'text': f"Before I file {p['what']}: {steps}. {p['fallback']} {p['question']} Answer here, or say go.", 'at': now, 'ask': {'kind': kind, 'chips': p['chips']}}


def answer(pending, text, now):
    """The owner's reply to a clarifying question. → ('cancel', None), ('go', the line to run, the note) or ('stale', None)."""
    if not pending or now - float(pending.get('at') or 0) > ASK_TTL_S:
        return 'stale', None, ''
    t = str(text or '').strip()
    if _NO.match(t):
        return 'cancel', None, ''
    base = str(pending.get('text') or '')
    if _GO.match(t) or re.match(r'(?i)^go,?\s+(best games now|whatever fits me)$', t):
        return 'go', base, ''
    if pending.get('kind') in ('pob', 'poc'):   # its answer sharpens the topic itself
        joined = f"{base} {re.sub(r'(?i)[,.;\s]*go[.!]?$', '', t)}".strip()   # "NBA, just 2 picks, go": the go is an answer, not part of the topic
        return 'go', joined[:200], ''
    return 'go', base, t[:300]   # a trade or a perp keeps the line, and its answer goes to both minds as a note


def goal_for_bid(topic, sites, angle=None):
    look = f"Your angle: {angle[0]}. Search for {topic} {angle[1]}. Another mind has the other angle and other sites, so never open its sites first or run its search. " if angle else "Do one good search first. Look for today's lines, odds, injuries, form and what the market prices. "
    return (f"PROOF OF BID research. The owner asks: {topic}. {look}Then open these and read each in 3 to 6 steps, no more: {', '.join(sites[:4])}. "
            "If a site has nothing, move on and say so. Then answer in at most 6 lines, each number with the site you read it on. Do not sign in, bet or buy anything.")
