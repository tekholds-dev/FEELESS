"""Owner 2026-11-09 ("loading bar not true"): a PoC run says which mind is answering and how many have answered, from when the job began,
and Mind A's answer shows while Mind B is still working. It never says it is writing a page."""
import asyncio

from test_play_studio import _server


def test_a_poc_bar_moves_on_real_answers(monkeypatch, tmp_path):
    fs, c, store = _server(monkeypatch, tmp_path)
    cat = store['cats']['g']; cat['brainsCfg']['brains'] = ['m/x', 'm/y']
    row = fs._feat.new_folder(cat, 'content', 'NewTrench coin', 1.0)
    doc = fs._feat.new_doc(row); doc['busy'] = {'at': 1000, 'to': 'both', 'stage': 'answer'}; fs._ws_save('g', doc)
    seen = []
    async def fake(cat_, model, sys_, user_, tokens):
        d = fs._ws_load('g', row['id']); seen.append((d['busy'], [m['by'] for m in d.get('messages') or []]))
        return f'an answer from {model} that is long enough to read as a real answer', 0.002, False
    monkeypatch.setattr(fs, '_ws_ask', fake)
    asyncio.run(fs._ws_run('g', row['id'], 'both', 'Create a full trench coin with a name', None))
    (b0, said0), (b1, said1) = seen
    assert (b0['stage'], b0['by'], b0['step'], b0['steps'], b0['at']) == ('answer', 'Mind A', 0, 2, 1000)
    assert (b1['by'], b1['step'], b1['at']) == ('Mind B', 1, 1000) and 'Mind A' in said1 and 'Mind A' not in said0   # A's answer is saved before B starts
    done = fs._ws_load('g', row['id'])
    assert done['busy'] is None and [m['by'] for m in done['messages']][-2:] == ['Mind A', 'Mind B'] and done['lastCost'] == 0.004


def test_poc_answers_are_short_by_rule_and_kept_whole():
    import agent_features as af
    assert 'under 120 words' in af.CONTENT_SYS and 'picks one to build' in af.CONTENT_SYS
    doc = {}; af.add_msg(doc, 'Mind A', 'x' * 5000, 1)
    assert len(doc['messages'][0]['text']) == 5000   # was cut at 3,500 mid-word; the chat folds it behind Read more instead
