"""💬 Every proof from the chat: "create a PoB named Lakers v Suns 10/12". It makes the proof and it stays the one the chat is talking about, until the owner leaves it.

Pure: what a line asks for. The ask endpoint does the work, through the same doors a folder's own buttons use, so every guard and every plan question still applies."""
import re

KINDS = {'pow': 'pow', 'pop': 'pop', 'pob': 'pob', 'poc': 'poc', 'post': 'pos', 'pos': 'pos', 'postatic': 'pos', 'proof of work': 'pow', 'proof of perp': 'pop', 'proof of perps': 'pop', 'proof of bid': 'pob', 'proof of bids': 'pob', 'proof of content': 'poc', 'proof of static': 'pos'}
NAMES = {'pow': 'PoW', 'pop': 'PoP', 'pob': 'PoB', 'poc': 'PoC', 'pos': 'PoStatic'}
OPEN_IN = {'pow': 'pow', 'pop': 'pop', 'pob': 'bids', 'poc': 'features', 'pos': 'features'}
_ASK = re.compile(r'(?is)^\s*(/|(?:create|make|new|start|open|begin|run|do|file)\b)\s*(?:(?:a|an|the|new|my)\s+)*(proof of (?:work|perps?|bids?|content|static)|postatic|post|pow|pop|pob|poc|pos)\b\s*(?:(?:named|called|titled|on|for|about)\b|[:\-\u2013])?\s*(.*)$')
_LEAVE = re.compile(r'(?i)^\s*/?(?:back to (?:the )?desk|leave (?:this|the|it)?\s*(?:proof|folder)?|done with (?:this|it)|close (?:this )?proof)\s*[.!]?\s*$')
_LINE = {'pow': 'file a PoW', 'pop': 'file a perp'}


def parse(text):
    """→ {kind, name, ask} or None. A bare "post about the lakers" is a word, not a proof: PoST needs its capitals, a verb that is not "make a post", or a slash."""
    t = str(text or ''); m = _ASK.match(t)
    if not m:
        return None
    word = m.group(2); low = word.lower()
    if low == 'post' and m.group(1) != '/' and word != 'PoST' and word != 'POST':
        return None
    rest = m.group(3).strip(); name, _, ask = rest.partition(':')
    return {'kind': KINDS[low], 'name': name.strip()[:80], 'ask': ask.strip()[:3000]}


def leaving(text):
    return bool(_LEAVE.match(str(text or '')))


def line_for(got):
    """The words the existing handlers already understand. PoStatic has its own folder, so it has no line."""
    if got['kind'] in _LINE:
        return _LINE[got['kind']]
    if got['kind'] in ('pob', 'poc'):
        return f"file a {got['kind']} {got['name']}".strip()
    return None


def focus(got, now, ws=None):
    return {'kind': got['kind'], 'label': NAMES[got['kind']], 'name': got['name'] or NAMES[got['kind']], 'open': OPEN_IN[got['kind']], 'at': round(now), **({'ws': ws} if ws else {})}


def note_for(desk, text):
    return f"The owner is working with you on your {desk['label']} \"{desk['name']}\". They just said: {str(text)[:500]}"


COMMANDS = [('create a PoB named ', 'Makes a PoB on what you name, then keep talking to it here: "create a PoB named Lakers v Suns 10/12"'),
            ('create a PoC named ', 'Makes a PoC: both minds read what is trending and propose blind. Paid model calls, nothing is posted'),
            ('create a PoST named ', 'Makes a PoStatic folder. Add what to build after a colon, or tell it next: "create a PoST named Tip page: a tip jar"'),
            ('create a PoW', 'Files a PoW: 4 coins, the minds agree on 1, then it trades by its own rules'),
            ('create a PoP', 'Files a PoP: each mind reads its sources and calls SOL, ETH or BTC, paper perps'),
            ('back to the desk', 'Stops talking to the open proof. It keeps its folder')]
