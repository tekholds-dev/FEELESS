"""🧭 COL-24 NEW PROOF TYPES FROM REAL GAPS (owner 2026-11-07 #12: "he names them, or the Collective proposes from real gaps; each needs a real
effect first"). Requests the agents got in chat that no proof kind covered (a job with no proof), grouped by their main word. A group asked
3+ times becomes a proposal the owner can pick; nothing is created on its own, and a proof type still needs a real effect before it ships.
Pure."""
import re
from collections import defaultdict

MIN_ASKS = 3
STOP = set('''a an the and or but if then than to of in on at by for with from into onto about as is are was were be been being it its this that
these those i me my we our you your he she they them their what which who whom how why when where can could should would will just also please
make do does did done get got give tell show find look check need want like some any all more most best new now today tonight one two
build page site write post read research site sites help me us via over under up down out off so very really'''.split())
COVERED = {'trade', 'coin', 'coins', 'token', 'buy', 'sell', 'pow', 'perp', 'perps', 'long', 'short', 'leverage', 'pop', 'bet', 'bets', 'pick',
           'picks', 'parlay', 'odds', 'game', 'games', 'pob', 'nba', 'nfl', 'content', 'thread', 'tweet', 'video', 'image', 'poc', 'website',
           'landing', 'dashboard', 'app', 'static', 'postatic', 'books', 'budget', 'invoice', 'bill', 'bills', 'expenses', 'poe', 'eco'}
WORD = re.compile(r"[a-z][a-z'-]{3,}")
URL = re.compile(r'https?://\S+|\b[\w-]+\.(?:com|net|network|org|io|xyz|app|ai|fun|gg)\S*')


def gaps(cats, min_asks=MIN_ASKS):
    """→ [{'name', 'word', 'asks', 'examples'}], most asked first. Only requests that were not a proof's own job."""
    by = defaultdict(list)
    for c in cats:
        for j in c.get('jobs') or []:
            if j.get('proof'):
                continue
            text = str(j.get('request') or '')
            words = [w for w in WORD.findall(URL.sub(' ', text.lower())) if w not in STOP]   # a site's name is not a kind of proof
            if not words or any(w in COVERED for w in words):
                continue
            top = max(set(words), key=words.count)
            by[top].append(text[:120])
    rows = [{'name': f'Proof of {w.title()}', 'word': w, 'asks': len(xs), 'examples': xs[:3]} for w, xs in by.items() if len(xs) >= min_asks]
    return sorted(rows, key=lambda r: -r['asks'])[:6]
