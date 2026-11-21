#!/usr/bin/env python3
"""🧪 Slice 0 · one TEST proof on Sicario's agent (free local minds only: OSSY + G4 on the owner's own LM Studio, $0, no money).
It goes through the live service (feecat_service on :5088, which has the LAN route to G4), files into that kind's own folder marked TEST,
and adds a Test bench row. A TEST PoW is a proposal (nothing bought, never the card seat), a TEST PoB never bids, nothing is posted.

  .venv/bin/python scripts/test-proof.py --kind pob --topic "best nba picks tonight" --wait
  .venv/bin/python scripts/test-proof.py --kind poe --wait
  .venv/bin/python scripts/test-proof.py --kind pop --stop        # an open paper PoP files now
  .venv/bin/python scripts/test-proof.py --state                  # the last TEST of every kind
  .venv/bin/python scripts/test-proof.py --kind pos --model ox-805187f02f8e424cb11b4f7c3a63a1c3 --size 1.6 --turn 35 --spin 6 --wait
                                                                 # Slice 2: a PoStatic carrying a 3D studio piece (size m, turn °, spin)
  .venv/bin/python scripts/test-proof.py --kind pos --ws wd1234567890 --topic "add a pools table" --wait
  .venv/bin/python scripts/test-proof.py --kind pos --ws wd1234567890 --inspect h1 --topic "make the headline say what it does" --wait
                                                                 # Slice 9: the element is clicked through the page's own inspect tool, then fixed
                                                                 # Slice 3: a new version of a TEST PoStatic folder (it must keep every part that worked)

The internal key is read from backend/data/internal.key and sent as a header; it is never printed."""
import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = 'http://127.0.0.1:5088/api/cats/internal/test-proof'


AGENT = ''


def call(method, body=None):
    key = (ROOT / 'backend' / 'data' / 'internal.key').read_text().strip()
    url = BASE + (f'?agent={AGENT}' if AGENT and method == 'GET' else '')
    if AGENT and isinstance(body, dict):
        body = {**body, 'agent': AGENT}
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'x-feeless-internal': key, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b'{}')


def summary(last):
    if not last:
        return 'no TEST filed yet'
    ch = ' · '.join(f"{c['key']} {'✓' if c['ok'] else '✗'}" for c in last.get('checks') or [])
    ran = ', '.join(f"{r['asked']}→{'/'.join(r.get('answered') or [])} ({r['calls']})" for r in last.get('ran') or [] if r.get('ok')) or 'none'
    return (f"#{last.get('n')} {last.get('id')} · {ch}\n  minds that ran: {ran}\n  sources: {len((last.get('read') or {}).get('sites') or [])} sites"
            f" {((last.get('read') or {}).get('sites') or [])[:6]}\n  footprint: {(last.get('foot') or {})}\n  bench: {(last.get('test') or {}).get('bench')}"
            + (f"\n  no trade: {last.get('why')}" if last.get('noTrade') else '')
            + (lambda b: f"\n  stash: {b.get('hits')} hits / {b.get('browsed')} browsed ({b.get('stale')} stale) · kept {b.get('kept')} · saved {b.get('savedSecs')} s, ${b.get('savedUsd')} (paid-eq ${b.get('paidEqUsd')}) · cats {b.get('cats')} · from {b.get('from')}" if b else '\n  stash: none recorded')(last.get('stash'))
            + ''.join(f"\n  studio piece: {r.get('name')} · {r.get('height')} m · turn {r.get('turn')} · spin {r.get('spin')} · {'IN THE PAGE' if r.get('used') else 'MISSING'}" for r in (last.get('studio') if isinstance(last.get('studio'), list) else []))
            + (f"\n  version {last.get('version')} · brief {(last.get('brief') or {}).get('centre')} + {(last.get('brief') or {}).get('layout')}" if last.get('brief') or last.get('version') else '')
            + (lambda w: f"\n  started with: {w.get('direction') or 'pitch approved'} · kits {w.get('kits') or 'its own pick'} · {w.get('start')} · research {(w.get('research') or {}).get('by')} ok={(w.get('research') or {}).get('ok')} refs={len((w.get('research') or {}).get('refs') or [])}" if w else '')(last.get('wizard'))
            + ''.join(f"\n  kit {k.get('name')}: {k.get('did')}" for k in last.get('kitsDid') or [])
            + (lambda u: f"\n  unique: page {u.get('centre')} + {u.get('layout')}, {round(float(u.get('like') or 0) * 100)}% like #{u.get('nearest')}{' COPY' if u.get('copy') else ''}" if u else '')(last.get('unique'))
            + (lambda c: f"\n  code check: {c.get('passed')}/{c.get('total')} failed {c.get('failed')}{' NOT RUN ' + str(c.get('notRun')) if c.get('notRun') else ''}" if c else '')(last.get('codeCheck'))
            + ''.join(f"\n  inspect {r.get('sel')}: {'CHANGED' if r.get('changed') else 'GONE' if r.get('gone') else 'SAME'} · before {((r.get('before') or {}).get('text') or '')[:60]!r} → after {((r.get('after') or {}).get('text') or '')[:60]!r}" for r in ((last.get('inspect') or {}).get('run') or {}).get('rows') or [])
            + (lambda k: f"\n  progress: kept {k.get('kept')}/{k.get('had')} of page {k.get('from')}, lost {k.get('lost')}" if k and k.get('from') else '')(last.get('keep'))
            + (lambda s: f"\n  PoC trend: {(s.get('trend') or {}).get('text')} ({(s.get('trend') or {}).get('source')})\n  PoC files: {sum(1 for x in s.get('files') or [] if x.get('url'))}/{len(s.get('files') or []) or 12} · goal {(s.get('goal') or {}).get('target')} {(s.get('goal') or {}).get('type')} by {(s.get('goal') or {}).get('by')}"
               if s else '')(last.get('studio') if isinstance(last.get('studio'), dict) else None)
            + (lambda l: f"\n  earn: {l.get('title')} ({l.get('src')}) · {l.get('pay')} · {l.get('cat')} · score {l.get('score')} · minds ${l.get('cost')} · expected profit ${l.get('expProfit')}\n  bids: {[(b.get('mind'), b.get('score')) for b in last.get('bids') or []]} kept {last.get('kept')} · stage {last.get('stage')} · kits {last.get('kits')}"
               if l else '')(last.get('listing') if last.get('kind') == 'earn' else None))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--agent', default='', choices=('', 'sicarios', 'happy'), help="the TEST agent: Sicario's (default, free local minds) or Happy's (its paid minds, proposals + paper only, $0.50 cap)")
    ap.add_argument('--kind', choices=('pow', 'pop', 'pob', 'poc', 'pos', 'poe'))
    ap.add_argument('--topic', default='')
    ap.add_argument('--wait', action='store_true', help='wait until the TEST files (up to --mins)')
    ap.add_argument('--mins', type=float, default=40)
    ap.add_argument('--stop', action='store_true', help='PoP only: stop the open paper trade so it files now')
    ap.add_argument('--state', action='store_true')
    ap.add_argument('--model', default='', help='PoStatic only: a real model id from the 3D library, added through the studio step before the build')
    ap.add_argument('--size', type=float, default=0, help='its size in metres, as the studio sets it')
    ap.add_argument('--turn', type=float, default=0, help='its turn in degrees')
    ap.add_argument('--spin', type=float, default=0)
    ap.add_argument('--clip', default='', help='PoC only (Slice 15): a video file (≤ 5 min) uploaded to the clip farm, through the same upload door the owner uses')
    ap.add_argument('--ws', default='', help='PoStatic only: a TEST folder to change (its next version)')
    ap.add_argument('--earn', action='store_true', help="PoEco only (Slice 16): an earn filing: a real open listing from the public feeds, both minds bid blind, nothing sent (--topic = a listing id from the board; '' = its best)")
    ap.add_argument('--dash', action='store_true', help='PoB only: file through the PoB dashboard door (op pob: a tap on What to file next), not the chat line')
    ap.add_argument('--slip', default='', help='PoB only, with --dash: his own slip as JSON, [{"ticker": "...", "side": "yes|no", "title": "..."}]')
    ap.add_argument('--wizard', default='', help='PoEco --earn (Slice 33): the start wizard\'s choices as JSON, {"direction": {"text": "", "approved": true}, "kits": [], "start": "fresh", "research": {"by": "comp"}}')
    ap.add_argument('--inspect', action='append', default=[], help='PoStatic + --ws: a CSS query for the element to click with inspect (repeatable); --topic is the fix')
    a = ap.parse_args()
    global AGENT
    AGENT = a.agent
    if a.state or not a.kind:
        code, j = call('GET')
        for k, v in (j.get('tests') or {}).items():
            print(f"{k}: {'RUNNING · ' if v.get('running') else ''}{summary(v.get('last'))}")
        return 0 if code == 200 else 1
    if a.clip:
        return clip_farm(a)
    code, j = call('GET'); before = (((j.get('tests') or {}).get(a.kind) or {}).get('last') or {}).get('id')
    code, j = call('POST', {'kind': a.kind, 'topic': a.topic, 'op': 'stop' if a.stop else 'start',
                            **({'model': {'id': a.model, 'height': a.size, 'turn': a.turn, 'spin': a.spin}} if a.model and a.kind == 'pos' else {}),
                            **({'ws': a.ws} if a.ws and a.kind == 'pos' else {}),
                            **({'door': 'dash'} if a.dash and a.kind == 'pob' else {}), **({'door': 'earn'} if a.earn and a.kind == 'poe' else {}), **({'wizard': json.loads(a.wizard)} if a.wizard and a.earn and a.kind == 'poe' else {}), **({'slip': json.loads(a.slip)} if a.slip and a.kind == 'pob' else {}),
                            **({'inspect': [{'click': q, 'note': a.topic} for q in a.inspect]} if a.inspect and a.ws and a.kind == 'pos' else {})})
    print(code, json.dumps({k: v for k, v in j.items() if k != 'chat'})[:600])
    if code != 200 or not a.wait:
        return 0 if code == 200 else 1
    t0 = time.time(); gone = None
    while time.time() - t0 < a.mins * 60:
        time.sleep(20)
        code, j = call('GET'); st = (j.get('tests') or {}).get(a.kind) or {}; last = st.get('last') or {}
        if last.get('id') and last.get('id') != before:
            print(f'filed after {round(time.time() - t0)} s:\n{summary(last)}'); return 0
        if not st.get('running'):   # a reload drops the in-memory claim, but a PoW/PoB run carries its own TEST mark and still files TEST
            gone = gone or time.time()
            if a.kind not in ('pow', 'pob') or time.time() - gone > 600:
                print('the TEST claim ended with no TEST folder filed (see the agent chat)'); return 1
    print(f'still running after {a.mins} min'); return 2


def clip_farm(a):
    """✂ Slice 15: a TEST clip-farm run. The file goes up through the owner's own upload door (internal key = marked TEST), then every step's
    progress line is printed until it is done, with every candidate, each mind's blind score and each filed clip PoC's record."""
    from urllib.parse import quote
    if a.kind != 'poc':
        print('--clip is for --kind poc'); return 1
    code, j = call('GET'); cid = j.get('id')
    if code != 200 or not cid:
        print(code, j); return 1
    f = pathlib.Path(a.clip); key = (ROOT / 'backend' / 'data' / 'internal.key').read_text().strip()
    base = f'http://127.0.0.1:5088/api/cats/{cid}/clipfarm'
    req = urllib.request.Request(f'{base}/upload?rights=1&name={quote(f.name)}&note={quote(a.topic)}', method='POST', data=f.read_bytes(),
                                 headers={'x-feeless-internal': key, 'Content-Type': 'video/mp4' if f.suffix.lower() != '.webm' else 'video/webm'})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            run = json.loads(r.read())['run']
    except urllib.error.HTTPError as e:
        print(e.code, e.read()[:400].decode(errors='replace')); return 1
    print(f"uploaded {f.stat().st_size / 1e6:.1f} MB in {time.time() - t0:.1f} s → run {run['id']} ({run['secs']} s, {run['w']}×{run['h']})"); seen = {}
    while time.time() - t0 < a.mins * 60:
        time.sleep(5)
        with urllib.request.urlopen(urllib.request.Request(base, headers={'x-feeless-internal': key}), timeout=60) as r:
            r_ = next((x for x in json.loads(r.read())['runs'] if x['id'] == run['id']), {})
        for s in r_.get('steps') or []:
            line = f"{s['state']:8} {s['label']}: {s.get('note', '')}{' · ' + str(s['secs']) + ' s' if s.get('secs') is not None else ''}"
            if seen.get(s['key']) != line:
                seen[s['key']] = line; print(f'  [{time.time() - t0:5.0f} s] {line}', flush=True)
        if r_.get('status') in ('done', 'failed'):
            print(f"\n{r_['status'].upper()} · first clip filed at {r_.get('firstClipS')} s · all at {r_.get('doneS')} s · minds ${r_.get('cost')}" + (f" · {r_.get('err')}" if r_.get('err') else ''))
            for c in r_.get('cands') or []:
                print(f"  #{c['n']} {c['s']:.1f}-{c['e']:.1f} s local {c['local']} both {c.get('both')} · " + ' · '.join(f"{'AB'[m['mind'] % 2]} {m['score']}{'*' if m['picked'] else ''}" for m in c.get('minds') or []) + f" · \"{c['first2'][:50]}\"")
            for m in r_.get('minds') or []:
                print(f"  mind {'AB'[m['mind'] % 2]} {m['model']}: read={m['read']} scored {m['scored']} picked {m['picked']} {m.get('err') or ''}")
            code, j = call('GET'); last = ((j.get('tests') or {}).get('poc') or {}).get('last')
            print(f"  clips filed: {r_.get('clips')}\n  last TEST PoC: {summary(last)}")
            return 0 if r_['status'] == 'done' else 1
    print(f'still running after {a.mins} min'); return 2


if __name__ == '__main__':
    sys.exit(main())
