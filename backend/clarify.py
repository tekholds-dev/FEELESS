"""❓ FIRST ASKS GET 2–3 QUESTIONS (owner 2026-10-30: "my first requests are to make a coin and to make safe fast money — it should ask 2–3
questions max to verify the request and its entirety"). For a coin launch or a make-money ask, the agent first asks only what the ask is
missing (never more than 3), costs nothing (no model call), and the owner's next message is taken as the answers. Pure, tested."""
import re
import time

TTL = 1800   # an unanswered set of questions expires after 30 min
COIN = re.compile(r'\b(launch|make|create|deploy|mint)\b.{0,30}\b(coin|token|memecoin|meme coin)\b', re.I)
MONEY = re.compile(r'\b(make|earn|grow|get)\b.{0,25}\b(money|profit|profits|yield|returns|\$\s?\d)', re.I)
SITES = re.compile(r'pump\.?fun|letsbonk|bonk\.fun|launchlab|raydium', re.I)
TICKER = re.compile(r'\$[A-Za-z][A-Za-z0-9]{1,9}\b|\bticker\b|\bnamed?\b', re.I)
SOL_AMT = re.compile(r'\d+(\.\d+)?\s*(sol|◎)\b|\bno (first|dev) buy\b', re.I)
USD_AMT = re.compile(r'\$\s?\d|\d+\s*(usd|dollars|sol)\b', re.I)
RISK = re.compile(r'\b(safe|low risk|mid|medium|risky|high risk|degen)\b', re.I)
SPAN = re.compile(r'\b(today|tonight|day|week|month|ongoing|forever|hours?)\b', re.I)


def questions(text, has_files=False):
    """→ (intent, [≤3 questions]) for a coin / money ask missing details, else (None, [])."""
    t = str(text or '')
    if COIN.search(t):
        q = []
        if not TICKER.search(t):
            q.append('Name + ticker for the coin?' + ('' if has_files else ' (attach its image with +)'))
        if not SITES.search(t):
            q.append('Where should it launch — pump.fun, LetsBONK or Raydium LaunchLab? (never on FEELESS)')
        if not SOL_AMT.search(t):
            q.append('How much SOL for the first buy from its wallet? (0 = none)')
        return ('coin', q[:3]) if q else (None, [])
    if MONEY.search(t):
        q = []
        if not USD_AMT.search(t):
            q.append('How much may it use, in $ or SOL?')
        if not RISK.search(t):
            q.append('Risk — SAFE, MID or RISKY?')
        if not SPAN.search(t):
            q.append('For how long — today, this week, or ongoing?')
        return ('money', q[:3]) if q else (None, [])
    return None, []


def take(cat, text, has_files=False, now=None):
    """The ask flow. → ('ask', [questions]) when it should ask first (cat['clarify'] set), or ('go', full_text) to start the task."""
    now = now or time.time()
    pend = cat.pop('clarify', None)
    if pend and now - float(pend.get('at') or 0) < TTL:
        return 'go', f"{pend['text']}\nThe owner's answers: {text}"
    intent, q = questions(text, has_files)
    if q:
        cat['clarify'] = {'intent': intent, 'text': str(text)[:2000], 'at': round(now)}
        return 'ask', q
    return 'go', text
