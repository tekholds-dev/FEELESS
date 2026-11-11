"""🪞 VOICE MIRROR (owner 2026-11-11: "agent brains truly build a true persona based on how the user speaks to them, and can be slightly tweaked").
Every message its owner sends updates a small running profile of HOW they write: length, lowercase, caps for emphasis, slang and shorthand,
swearing, emoji, punctuation, the words they lean on. persona_line adds one plain instruction from it, scaled by the owner's mirror setting
(0 off · 1 a hint · 2 match · 3 talk just like me). Words only: the mirror never touches a buy, a size or a rule. Pure."""
import re
from collections import Counter

SLANG = ('lol', 'lmao', 'asl', 'fr', 'ngl', 'tbh', 'imo', 'idk', 'rn', 'bro', 'bruh', 'fam', 'yall', 'ya', 'u', 'ur', 'pls', 'plz', 'gonna', 'wanna', 'gotta',
         'dope', 'lit', 'fire', 'degen', 'wagmi', 'ngmi', 'ser', 'gm', 'lfg', 'sus', 'cap', 'bet', 'lowkey', 'highkey', 'finna', 'tryna', 'ish', 'sumn', 'wit', 'lmk')
SWEAR = ('fuck', 'fuckin', 'fucking', 'shit', 'damn', 'ass', 'bitch', 'hell', 'crap', 'asf', 'af')
STOP = set('the a an and or but to of in on for is it this that with be are was i you me my we our your at as by so if not do does can just like what when how all any its'.split())
EMOJI = re.compile('[\U0001F300-\U0001FAFF☀-➿]')
LEVEL = {0: '', 1: 'Lean a little toward the way your owner writes', 2: 'Match the way your owner writes', 3: 'Talk just like your owner writes'}


def learn(prof, text):
    """→ the profile with one more of the owner's messages folded in."""
    p = dict(prof or {}); t = str(text or '').strip()
    if not t:
        return p
    words = re.findall(r"[a-zA-Z']+", t); low = [w.lower() for w in words]
    p['n'] = p.get('n', 0) + 1
    p['words'] = p.get('words', 0) + len(words)
    p['lower'] = p.get('lower', 0) + (1 if t == t.lower() else 0)
    p['shout'] = p.get('shout', 0) + (1 if re.search(r'\b[A-Z]{4,}\b', t) else 0)
    p['bang'] = p.get('bang', 0) + (1 if '!!' in t else 0)
    p['emoji'] = p.get('emoji', 0) + (1 if EMOJI.search(t) else 0)
    p['swear'] = p.get('swear', 0) + (1 if any(w.startswith(SWEAR) for w in low) else 0)
    p['nopunct'] = p.get('nopunct', 0) + (1 if not re.search(r'[.?!]\s*$', t) else 0)
    sl = Counter(p.get('slang') or {}); sl.update(w for w in low if w in SLANG); p['slang'] = dict(sl.most_common(12))
    lean = Counter(p.get('lean') or {}); lean.update(w for w in low if len(w) > 3 and w not in STOP and w not in SLANG); p['lean'] = dict(lean.most_common(20))
    return p


def traits(prof):
    """→ [plain trait] the profile shows, strongest first. Needs 5 messages before it says anything."""
    p = prof or {}; n = p.get('n', 0)
    if n < 5:
        return []
    r = lambda k: p.get(k, 0) / n
    avg = p.get('words', 0) / n; out = []
    out.append('short, quick messages' if avg < 14 else 'long, detailed messages' if avg > 40 else 'medium-length messages')
    if r('lower') > .6: out.append('mostly lowercase')
    if r('shout') > .2: out.append('CAPS for emphasis')
    if r('bang') > .2: out.append('lots of !!')
    if r('nopunct') > .6: out.append('drops end punctuation')
    if r('swear') > .15: out.append('swears casually')
    if r('emoji') > .2: out.append('uses emoji')
    slang = [w for w, c in sorted((p.get('slang') or {}).items(), key=lambda x: -x[1]) if c >= 2][:6]
    if slang: out.append('slang like ' + ', '.join(slang))
    return out


def line(prof, level):
    """One instruction for the system prompt, or '' when the mirror is off or there is not enough to go on."""
    try:
        level = max(0, min(3, int(level or 0)))
    except (TypeError, ValueError):
        level = 0
    t = traits(prof)
    if not level or not t:
        return ''
    keep = ' Keep it readable and never copy insults aimed at anyone.' if level == 3 else ''
    return f"{LEVEL[level]}: {'; '.join(t)}.{keep}"


def view(prof, level):
    p = prof or {}
    return {'n': p.get('n', 0), 'traits': traits(p), 'level': max(0, min(3, int(level or 0))), 'words': [w for w, _ in sorted((p.get('lean') or {}).items(), key=lambda x: -x[1])][:8], 'ready': p.get('n', 0) >= 5}
