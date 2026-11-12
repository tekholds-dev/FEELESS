"""🚀 COMP v2: the prompt never sees what was written after a proof settled, the split is stable and stratified, the exam scores right,
the MLX log parses, and the routes refuse a second run (training and the exam processes are faked; MLX is never imported)."""
import asyncio
import json
from types import SimpleNamespace

import pytest

import comp_v2 as cv


def _rows():
    rows = []
    for i in range(30):
        rows.append({'kind': 'PoB' if i % 2 else 'PoW', 'title': f'pick {i}', 'plan': f'plan {i}', 'result': 'it WON big', 'verdict': 'right',
                     'source': 'own read', 'outcome': 'won' if i % 3 else 'lost', 'at': 1000 + i})
    rows.append({'kind': 'PoW', 'title': 'flat one', 'outcome': 'flat', 'at': 5})
    return rows


def test_the_prompt_only_holds_what_was_known_before_it_settled():
    p = cv.prompt_of(_rows()[0])
    assert 'plan 0' in p and 'Kind: PoW' in p
    assert 'WON' not in p and 'right' not in p          # result / verdict are written after: they would leak the answer
    assert cv.chat_of({'outcome': 'flat'}) is None
    m = cv.chat_of(_rows()[1])['messages']
    assert [x['role'] for x in m] == ['system', 'user', 'assistant'] and m[2]['content'] == 'won'


def test_split_is_stable_stratified_and_never_overlaps(tmp_path):
    a = cv.split(_rows()); b = cv.split(list(reversed(_rows())))
    assert [r['title'] for r in a[2]] == [r['title'] for r in b[2]]           # same held-out exam whatever order the proofs come in
    tr, va, te = a
    titles = [r['title'] for r in tr + va + te]
    assert len(titles) == len(set(titles)) == 30                                # flat dropped, nothing in two parts
    assert {(r['kind'], r['outcome']) for r in te} == {(r['kind'], r['outcome']) for r in tr}
    c = cv.write_dataset(_rows(), tmp_path)
    assert c['train'] + c['valid'] + c['test'] == 30 and (tmp_path / 'train.jsonl').read_text().count('\n') == c['train']
    assert len(json.loads((tmp_path / 'test_rows.json').read_text())) == c['test']


def test_answers_scores_and_the_baseline():
    assert cv.answer_of('<think>maybe lost</think> Won.') == 'won'
    assert cv.answer_of('a loss') == 'lost' and cv.answer_of('no idea') is None
    rows = [{'kind': 'PoB', 'outcome': 'won'}, {'kind': 'PoB', 'outcome': 'lost'}, {'kind': 'PoW', 'outcome': 'won'}]
    s = cv.score(rows, ['won', None, 'lost'])
    assert s['right'] == 1 and s['unsure'] == 1 and s['acc'] == round(1 / 3, 4) and s['kinds']['PoB'] == {'n': 2, 'right': 1}
    assert cv.majority(rows) == 'won' and cv.majority([{'outcome': 'lost'}]) == 'lost'


def test_the_mlx_log_parses_in_both_formats():
    old = cv.parse_log('Iter 5: Train loss 2.100, x\nIter 25: Val loss 1.500, y')
    assert old == {'train': [[5, 2.1]], 'val': [[25, 1.5]], 'last': 25}
    table = cv.parse_log('  iter   train_loss     tok/s     tokens\n     1    val 3.584    22.56s\n\x1b[1m     5\x1b[0m    2.410 ▼        0      0.1k\n')
    assert table['val'] == [[1, 3.584]] and table['train'] == [[5, 2.41]] and table['last'] == 5


@pytest.fixture()
def lab(monkeypatch, tmp_path):
    import rep_model_lab as lab
    import reputation_service as rs
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'OWNER')
    monkeypatch.setattr(cv, 'DATA', tmp_path)
    monkeypatch.setattr(cv, 'BASE', tmp_path)          # "the base is on this Mac"
    monkeypatch.setattr(cv, 'MLX_PY', tmp_path)
    monkeypatch.setattr(lab, '_export', lambda rs: _rows())
    started = []
    monkeypatch.setattr(cv, 'start_train', lambda iters, folder=None: started.append(('train', iters)) or 1)
    monkeypatch.setattr(cv, 'start_exam', lambda folder=None: started.append(('exam',)) or 1)
    return lab, started, tmp_path


def test_routes_train_then_exam_and_refuse_while_busy(lab, monkeypatch):
    lab, started, folder = lab
    req = SimpleNamespace(headers={}, client=None)
    with pytest.raises(Exception) as e:
        asyncio.run(lab.comp2_exam(req))
    assert '400' in str(getattr(e.value, 'status_code', '')) or 'Train COMP v2 first' in str(e.value.detail)
    st = asyncio.run(lab.comp2_train(req, lab.Comp2Train(iters=5000)))
    assert started == [('train', 1000)] and st['dataset']['test'] > 0                # iters capped, dataset rebuilt from the proofs
    (folder / 'train.json').write_text(json.dumps({'pid': 1, 'iters': 150}))
    monkeypatch.setattr(cv, 'alive', lambda pid: True)                                 # the run is still going
    with pytest.raises(Exception) as e:
        asyncio.run(lab.comp2_train(req, lab.Comp2Train()))
    assert e.value.status_code == 409
    monkeypatch.setattr(cv, 'alive', lambda pid: False)
    asyncio.run(lab.comp2_exam(req))
    assert started[-1] == ('exam',)


class _R:
    def __init__(self, j, code=200):
        self._j, self.status_code = j, code

    def json(self):
        return self._j


def _pair(addr, mint, price, liq=20000):
    return {'pairAddress': addr, 'baseToken': {'address': mint, 'symbol': mint.upper()}, 'dexId': 'pumpswap', 'priceUsd': str(price),
            'liquidity': {'usd': liq}, 'fdv': 90000, 'pairCreatedAt': 0, 'priceChange': {'m5': 3, 'h1': 9}, 'txns': {'h1': {'buys': 40, 'sells': 20}},
            'volume': {'h1': 5000}}


def test_the_internet_learner_snapshots_then_settles_won_lost_flat_and_rugs(tmp_path):
    import comp_market as cm
    prices = {'a': 1.0, 'b': 1.0, 'c': 1.0, 'd': 1.0}

    class H:
        async def get(self, url):
            if 'token-profiles' in url:
                return _R([{'chainId': 'solana', 'tokenAddress': m} for m in 'abcd'] + [{'chainId': 'base', 'tokenAddress': 'x'}])
            if 'token-boosts' in url:
                return _R([{'chainId': 'solana', 'tokenAddress': 'a'}])
            if '/tokens/v1/' in url:
                return _R([_pair('p' + m, m, prices[m]) for m in url.rsplit('/', 1)[1].split(',')] + [_pair('pa2', 'a', 1.0, liq=5)])
            if '/latest/dex/pairs/' in url:   # an hour later: a +50%, b −40%, c +5%, d's pool is gone
                return _R({'pairs': [_pair('pa', 'a', 1.5), _pair('pb', 'b', 0.6), _pair('pc', 'c', 1.05)]})
            raise AssertionError(url)

    st = asyncio.run(cm.collect(H(), tmp_path, now=1000))
    assert st['open'] == 4 and st['rows'] == 0                                       # base-chain coin skipped, deepest pool per coin
    assert {s['pair'] for s in json.loads((tmp_path / 'market_open.json').read_text())} == {'pa', 'pb', 'pc', 'pd'}
    st = asyncio.run(cm.collect(H(), tmp_path, now=1000 + cm.HOLD_SEC))
    assert (st['won'], st['lost'], st['flat']) == (1, 2, 1) and st['rows'] == 3
    rows = cm.rows(tmp_path, 10)
    assert {(r['title'], r['outcome']) for r in rows} == {('Hold $A for 1 hour', 'won'), ('Hold $B for 1 hour', 'lost'), ('Hold $D for 1 hour', 'lost')}
    assert 'liquidity $20K' in rows[0]['plan'] and cm.rows(tmp_path, 1) == rows[:1]
    # the rows join training only, capped at the owner's own train count; the exam stays his proofs
    c = cv.write_dataset(_rows(), tmp_path)
    test = json.loads((tmp_path / 'test_rows.json').read_text())
    assert c['net'] == 3 and all(r['kind'] != 'PoMkt' for r in test)


def test_memory_recalls_the_most_alike_past_proofs():
    train = [{'kind': 'PoW', 'title': 'pump coin rocket', 'outcome': 'won'}, {'kind': 'PoB', 'title': 'pump coin rocket', 'outcome': 'lost'},
             {'kind': 'PoW', 'title': 'quiet slow chart', 'outcome': 'lost'}]
    row = {'kind': 'PoW', 'title': 'rocket pump again'}
    assert cv.neighbours(row, train, 2)[0]['title'] == 'pump coin rocket' and cv.neighbours(row, train, 2)[0]['kind'] == 'PoW'
    p = cv.memory_prompt(row, train, 2)
    assert '→ won' in p and p.endswith('Won or lost?')


def test_the_cut_off_is_tuned_on_valid_and_reads_confidence_not_the_top_word():
    import comp_v2_exam as ex
    rows = [{'kind': 'PoW', 'outcome': o} for o in ('won', 'won', 'lost', 'lost')]
    margins = [3.0, 2.5, 1.0, 0.5]                     # always "won" by the top word, but the gap separates them
    assert cv.score(rows, ['won' if m > 0 else 'lost' for m in margins])['acc'] == 0.5
    t, acc = ex.threshold(margins, rows)
    assert acc == 1.0 and 1.0 < t < 2.5 and ex.judged(rows, margins, t)['right'] == 4
    assert ex.threshold([0.1, -0.1], [{'outcome': 'won'}, {'outcome': 'lost'}]) == (0.0, 1.0)   # nothing beats its own word → 0
    five = [{'outcome': o} for o in ('won', 'won', 'lost', 'won', 'lost')]
    assert ex.threshold([2, 1, 0.5, -0.5, -1], five) == (0.0, 0.6)   # a cut that wins just one more proof is noise: keep its own word
