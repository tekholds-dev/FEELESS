"""🚀 PRIORITY SETUP (owner 2026-11-04): a new agent starts with a short list of asks. The desktop button stays lit with how many are left.

What it is used for decides which sites come first. A step is done by the real thing (its mailbox exists, its colony share is signed), or by the owner saying later: nothing here moves money or signs anything.
Pure and tested. The service stores `cat['setup']`.
"""
USES = ('trade', 'bids', 'content', 'research', 'all')
TERMS_V = 2
STEPS = ('use', 'face', 'email', 'sites', 'fund', 'limits', 'colony', 'post', 'trades', 'security', 'terms')
# step → the uses that need it. A step that is not listed is for everyone.
ONLY = {'post': ('content', 'all'), 'trades': ('trade', 'bids', 'all')}
# what to sign in to first, by use: [site, what it is for]. The owner signs in by hand in every one of them.
PRIORITY = {
    'trade': [['pump.fun', 'Coin trades on its own account'], ['axiom.trade', 'A second trading desk'], ['dexscreener.com', 'Charts and alerts']],
    'bids': [['polymarket.com', 'Prediction markets'], ['kalshi.com', 'US regulated markets'], ['stake.us', 'Sports and social betting']],
    'content': [['bsky.app', 'Bluesky: bots are welcome by its open API'], ['mastodon.social', 'Mastodon: bots are welcome on most servers'], ['x.com', 'X: post through its official API, or by hand']],
    'research': [['reddit.com', 'What people are saying'], ['coingecko.com', 'Market data'], ['x.com', 'Live news']],
}
PRIORITY['all'] = [PRIORITY['trade'][0], PRIORITY['bids'][0], PRIORITY['content'][0], PRIORITY['research'][1]]


def _done(cat, step, s):
    if step == 'use':
        return s.get('use') in USES
    if step == 'terms':
        return int(s.get('termsV') or 0) >= TERMS_V
    said = step in (s.get('done') or [])
    if step == 'face':
        return bool((cat.get('face') or {}).get('id')) or said
    if step == 'email':
        return bool((cat.get('mailbox') or {}).get('address')) or said
    if step == 'sites':
        return bool(cat.get('siteSessions')) or said
    if step == 'fund':
        return bool(cat.get('agentFunded')) or said
    if step == 'colony':
        return bool((cat.get('colonyShare') or {}).get('on')) or said
    return said


def view(cat):
    """→ what the page draws: every step that applies, how many are left, the sites that come first."""
    s = cat.get('setup') or {}
    use = s.get('use')
    rows = [{'k': k, 'done': _done(cat, k, s)} for k in STEPS if k not in ONLY or not use or use in ONLY[k]]
    return {'use': use, 'steps': rows, 'left': sum(1 for r in rows if not r['done']), 'total': len(rows), 'termsV': TERMS_V, 'termsAt': s.get('termsAt'), 'sites': PRIORITY.get(use) or []}


def apply(cat, job, text, now):
    """One answer. Raises ValueError on anything else, so a page can't mark a step it does not have."""
    s = cat.setdefault('setup', {})
    if job == 'use':
        if text not in USES:
            raise ValueError('Pick what it will be used for.')
        s['use'] = text
    elif job == 'done':
        if text not in STEPS or text in ('use', 'terms'):
            raise ValueError('No such step.')
        s['done'] = sorted({*(s.get('done') or []), text})
    elif job == 'undo':
        s['done'] = [x for x in s.get('done') or [] if x != text]
    elif job == 'terms':
        s.update(termsV=TERMS_V, termsAt=round(now))
    else:
        raise ValueError('No such answer.')
    return view(cat)
