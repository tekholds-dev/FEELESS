"""📊 PoEco (owner 2026-11-05): a business's books as a proof. Python does the math, so the same rows always give the same numbers and the same hash. The rows stay sealed for their owner; the folder keeps only totals and the hash. Books never reach the Stash, the wall or a repo."""
import csv
import hashlib
import io
import json
import re
import secrets

MAX_ROWS = 5000
CATS = [('Sales', r'sale|invoice|client|customer|stripe|shopify|revenue|payment received|deposit'), ('Payroll', r'payroll|salary|wage|contractor|freelanc'), ('Rent', r'\brent\b|lease|office'), ('Software', r'software|saas|subscription|hosting|github|aws|openai|anthropic|domain'), ('Ads', r'\bads?\b|advert|marketing|meta|google ads'), ('Tax', r'\btax\b|irs|vat|gst'), ('Travel', r'flight|hotel|uber|lyft|travel|fuel'), ('Supplies', r'supplies|equipment|inventory|stock|materials'), ('Fees', r'\bfees?\b|bank charge|interest')]


def _money(v):
    s = str(v or '').strip().replace('$', '').replace(',', '')
    neg = s.startswith('(') and s.endswith(')')
    n = float(s.strip('()'))
    return round(-n if neg else n, 2)


def category(desc, income):
    d = str(desc or '').lower()
    for name, rx in CATS:
        if re.search(rx, d):
            return name
    return 'Other income' if income else 'Other costs'


def parse(text):
    """(rows, skipped). Lines of date, description, amount and an optional category. A negative amount is a cost. A header or a broken line is skipped and counted, never guessed."""
    rows = []; skipped = 0
    for r in csv.reader(io.StringIO(str(text or '')[:800000])):
        if not r or not ''.join(r).strip():
            continue
        try:
            amt = _money(r[2]); date = str(r[0]).strip()[:10]
            if not re.match(r'^\d{4}-\d{2}', date) or not amt:
                raise ValueError
        except (ValueError, IndexError):
            skipped += 1; continue
        desc = str(r[1]).strip()[:120]
        rows.append({'date': date, 'desc': desc, 'amount': amt, 'cat': str(r[3]).strip()[:30] if len(r) > 3 and r[3].strip() else category(desc, amt > 0)})
        if len(rows) >= MAX_ROWS:
            break
    rows.sort(key=lambda x: x['date'])
    return rows, skipped


def summary(rows, tax_pct=25):
    income = round(sum(r['amount'] for r in rows if r['amount'] > 0), 2); costs = round(-sum(r['amount'] for r in rows if r['amount'] < 0), 2); net = round(income - costs, 2)
    months = {}; cats = {}
    for r in rows:
        m = months.setdefault(r['date'][:7], {'month': r['date'][:7], 'income': 0.0, 'costs': 0.0})
        m['income' if r['amount'] > 0 else 'costs'] += abs(r['amount'])
        if r['amount'] < 0:
            cats[r['cat']] = cats.get(r['cat'], 0.0) + -r['amount']
    series = [{**m, 'income': round(m['income'], 2), 'costs': round(m['costs'], 2), 'net': round(m['income'] - m['costs'], 2)} for _, m in sorted(months.items())]
    tax = round(max(0.0, net) * max(0, min(60, float(tax_pct or 0))) / 100, 2); burn = round(costs / len(series), 2) if series else 0.0
    return {'count': len(rows), 'income': income, 'costs': costs, 'net': net, 'margin': round(100 * net / income, 1) if income else None, 'months': series, 'cats': [{'cat': k, 'usd': round(v, 2)} for k, v in sorted(cats.items(), key=lambda kv: -kv[1])][:8], 'taxPct': tax_pct, 'taxSetAside': tax, 'keep': round(net - tax, 2), 'burnPerMonth': burn}


def book_hash(rows):
    """The same rows always give this hash, so anyone holding the rows can check the receipt."""
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def new_folder(n, name, rows, tax_pct, now):
    s = summary(rows, tax_pct)
    return {'id': 'pe' + secrets.token_hex(5), 'n': n, 'kind': 'PoEco', 'at': round(now), 'closedAt': round(now), 'status': 'closed', 'topic': str(name or 'Books')[:60], 'hash': book_hash(rows), 'graded': None, 'sent': None, **s}


def receipt(f):
    """What its owner can send: totals and the hash. Never a row."""
    return {'proof': 'FEELESS PoEco', 'name': f.get('topic'), 'filed': f.get('at'), 'entries': f.get('count'), 'income': f.get('income'), 'costs': f.get('costs'), 'net': f.get('net'), 'sha256': f.get('hash'), 'check': 'Sort the entries by date and hash them as compact sorted JSON: the sha256 must match.'}
