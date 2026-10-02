import meme_terms as mt

D = 86400


def test_tokenize_drops_noise_and_joins_phrases():
    assert mt.tokenize('$GIGA Chad to the moon 1000x paper hands') == ['chad', 'giga', 'moon', 'paperhands']
    assert 'the' not in mt.tokenize('the coin') and mt.tokenize('') == []


def test_a_new_ticker_wave_is_learned_and_known_slang_explained():
    s = {}
    for i in range(6):                                          # quiet past week: "chad" shows up every day
        mt.learn(s, [('chad energy', 'chat', f'm{i}a'), ('chad', 'chat', f'm{i}b'), ('chad', 'chat', f'm{i}c')], i * D)
    now = 7 * D
    mt.learn(s, [(f'Skibidi {k}', 'coin', f'MINT{k}') for k in range(4)] + [('wen cto', 'chat', f'c{k}') for k in range(3)] + [('chad', 'chat', 'x1')] * 3, now)
    mt.learn(s, [('Skibidi 0', 'coin', 'MINT0')], now)          # same coin twice = counted once
    t = {x['term']: x for x in mt.trending(s, now)}
    assert t['skibidi']['kind'] == 'wave' and t['skibidi']['new'] and t['skibidi']['today'] == 4 and 'MINT0' in t['skibidi']['coins']
    assert t['cto']['known'] and 'community takeover' in t['cto']['meaning']
    assert 'chad' not in t                                      # used every day = not new, no spike
    assert mt.wave_of('Skibidi Cat', 'SKIB', list(t.values()))['term'] == 'skibidi' and mt.wave_of('Dog', 'DOG', list(t.values())) is None
    assert mt.explain(s, '$JEET')['known'] and mt.explain(s, 'skibidi')['kind'] == 'wave'


def test_old_days_are_forgotten():
    s = mt.learn({}, [('alpha', 'chat', 'a')], 0)
    mt.learn(s, [('beta', 'chat', 'b')], 20 * D)
    assert list(s['days']) == ['20']
