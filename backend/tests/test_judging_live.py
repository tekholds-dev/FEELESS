"""⚖ AGX-9: The Collective's verdicts land on the live record one judge at a time; the desk sees it (names hidden for users) and it fades after 10 min."""
import asyncio

import proof_review as rv


def test_live_record_fills_judge_by_judge_and_fades():
    f = {'id': 'f1', 'n': 7, 'topic': 'SOL breakout'}
    j = rv.live_start('pob', f, recused_=('zed',), now=100)
    assert j['judges'] == {'ossy': {'state': 'wait'}, 'g4': {'state': 'wait'}, 'zed': {'state': 'out'}} and j['title'] == 'SOL breakout'
    rv.live_judge(j, 'ossy', state='think', now=101)
    assert j['judges']['ossy'] == {'state': 'think', 'since': 101}
    rv.live_judge(j, 'ossy', {'score': 80, 'verdict': 'pass', 'why': 'sources check out', 'checks': ['✓ a']}, now=130)
    rv.live_judge(j, 'g4', None, now=140)
    assert j['judges']['ossy']['score'] == 80 and j['judges']['ossy']['why'] == 'sources check out' and j['judges']['g4']['state'] == 'down'
    assert rv.live_view(j, now=500) is j                      # in flight
    assert rv.live_view(j, now=100 + 4 * 240 + 61) is None    # cut off by a restart: never shown forever
    j['done'] = 150
    assert rv.live_view(j, now=150 + 599) is j and rv.live_view(j, now=150 + 601) is None
    assert rv.live_view(None) is None


def test_review_one_publishes_each_verdict_as_it_lands(monkeypatch):
    import feecat_service as fs
    store = {'cats': {'c1': {'id': 'c1', 'handle': 'sicarios', 'pobFolders': [{'id': 'b1', 'n': 3, 'topic': 'JUP bid', 'status': 'closed', 'at': 1}]}}}
    seen = []

    async def think(_cat, model, _msgs, max_tokens=0):
        seen.append({k: dict(v) for k, v in fs._JUDGING['c1']['judges'].items()})   # what the desk would see mid-judging
        return ('{"score": 90, "why": "fine"}' if 'ossy' in model else 'no json'), 0, 'local'

    async def rows():
        return []
    monkeypatch.setattr(fs, '_think', think); monkeypatch.setattr(fs, '_review_rows', rows)
    monkeypatch.setattr(fs._review, 'next_due', lambda *_a, **_k: ('c1', 'pob', store['cats']['c1']['pobFolders'][0]))
    monkeypatch.setattr(fs, '_REVIEWED', set()); monkeypatch.setattr(fs, '_REVIEW_DONE', []); monkeypatch.setattr(fs, '_JUDGING', {})
    asyncio.run(fs._review_one(store))
    assert seen[0]['ossy']['state'] == 'think' and seen[0]['g4']['state'] == 'wait'
    assert seen[1]['ossy']['state'] == 'done' and seen[1]['ossy']['score'] == 90 and seen[1]['g4']['state'] == 'think'
    j = fs._JUDGING['c1']
    assert j['done'] and j['judges']['g4']['state'] == 'down' and j['score'] == 90
    # a user's agent sees The Collective, never the judges' names
    out = fs._collective_names({'judges': j['judges']})
    assert list(out['judges'])[:2] == ['collective', 'collective-2']
