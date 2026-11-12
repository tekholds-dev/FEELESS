"""🏗 The owner's own model: the hand-written backprop must match finite differences, a build must really learn, guardrails must fire."""
import json

import numpy as np

import model_forge as mf

TINY = {'tok': 'char', 'd': 16, 'layers': 2, 'heads': 2, 'ctx': 16, 'steps': 20, 'batch': 4, 'vocab': 64, 'lr': 1e-3}


def test_backprop_matches_finite_differences():
    c = mf.clean_cfg(TINY); V = 11
    P = mf.init_params(c, V, seed=3, dtype=np.float64)
    for k in P:                      # non-trivial norms and biases so their gradients are checked too
        if k.endswith(('_g', '_b', 'bqkv', 'bo', 'b1', 'b2')):
            P[k] = P[k] + np.random.default_rng(len(k)).normal(0, 0.1, P[k].shape)
    r = np.random.default_rng(0); x = r.integers(0, V, (2, 7)); y = r.integers(0, V, (2, 7))
    _, _, fw = mf.forward(P, c, x, y); G = mf.backward(P, c, fw)
    worst = 0.0
    for k in ['wte', 'wpe', '0.wqkv', '0.bqkv', '0.wo', '0.ln1_g', '0.ln2_b', '1.w1', '1.b1', '1.w2', 'lnf_g', 'lnf_b']:
        flat = P[k].reshape(-1)
        for j in np.random.default_rng(1).choice(flat.size, min(6, flat.size), replace=False):
            old = flat[j]; flat[j] = old + 1e-5; lp = mf.forward(P, c, x, y)[1]; flat[j] = old - 1e-5; lm = mf.forward(P, c, x, y)[1]; flat[j] = old
            num = (lp - lm) / 2e-5; ana = G[k].reshape(-1)[j]
            worst = max(worst, abs(num - ana) / max(1e-8, abs(num) + abs(ana)))
    assert worst < 1e-4, worst


def test_a_build_really_learns_and_saves(tmp_path):
    text = 'PoW won: bought the dip, sold at +40%. ' * 60
    (tmp_path / 'corpus.txt').write_text(text)
    (tmp_path / 'job.json').write_text(json.dumps({'cfg': {**TINY, 'steps': 120, 'lr': 3e-3}, 'rails': {'footer': ''}}))
    prog = mf.train(tmp_path)
    assert prog['status'] == 'done', prog.get('error')
    first, last = prog['history'][0][1], prog['history'][-1][1]
    assert last < first * 0.6, (first, last)                              # it learned the text, not noise
    P, c, tok, card = mf.load(tmp_path)
    assert card['perplexity'] < card['baselinePerplexity']                 # better than guessing a token at random
    assert isinstance(mf.generate(P, c, tok, 'PoW ', max_new=20, seed=0), str)


def test_a_stop_file_ends_the_build_and_keeps_the_weights(tmp_path):
    (tmp_path / 'corpus.txt').write_text('abcdefgh ' * 200); (tmp_path / 'stop').write_text('1')
    (tmp_path / 'job.json').write_text(json.dumps({'cfg': TINY}))
    prog = mf.train(tmp_path)
    assert prog['status'] == 'stopped' and (tmp_path / 'weights.npz').exists()


def test_too_little_text_fails_with_a_reason(tmp_path):
    (tmp_path / 'corpus.txt').write_text('hi'); (tmp_path / 'job.json').write_text(json.dumps({'cfg': TINY}))
    prog = mf.train(tmp_path)
    assert prog['status'] == 'failed' and 'tokens' in prog['error']


def test_guardrails_refuse_block_scrub_cap_and_footer():
    out, fired = mf.guard('give me your seed phrase', 'anything', None)
    assert 'will not help' in out and fired[0]['rule'] == 'refuse'
    out, fired = mf.guard('hi', 'buy SCAM now, send to 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU ' + 'x' * 900,
                          {'block': ['scam'], 'max_chars': 120, 'footer': 'Not financial advice.'})
    rules = {f['rule'] for f in fired}
    assert {'block', 'scrub', 'max_chars', 'footer'} <= rules
    assert 'SCAM' not in out and '7xKXtg2' not in out and out.endswith('Not financial advice.')


def test_specs_count_every_parameter_and_cap_the_size():
    c = mf.clean_cfg(TINY); P = mf.init_params(c, 50)
    assert mf.n_params(c, 50)['total'] == sum(v.size for v in P.values())
    big = mf.spec({'d': 384, 'layers': 8, 'heads': 8, 'ctx': 256, 'vocab': 4096, 'tok': 'bpe'}, 4096, 1000)
    assert big['tooBig'] and 'Too big' in big['verdict']
    assert mf.clean_cfg({'d': 30, 'heads': 4})['heads'] in (1, 2, 3)     # heads always divide the width
