"""Bot shield engines: each farming pattern caught with cited evidence; humans + FEELESS wallets stay clean."""
import bot_shield as bs

DAY = 86400


def test_human_is_clean():
    f = {'signin_days': list(range(10)), 'trades': [{'ts': 1000 + i * 3777 + (i * i * 97), 'side': 'buy', 'usd': 20 + i, 'token': f'T{i}'} for i in range(6)],
         'chat': [{'ts': 500 + i * 900 + i * i * 33, 'text': f'gm {i}'} for i in range(6)], 'checkin_at': [d * DAY + 3600 * (d % 7) for d in range(8)]}
    assert bs.scan(f)['verdict'] == 'clean'


def test_reward_farmer_and_clockwork_and_batch():
    f = {'signin_days': list(range(15)), 'trades': [], 'chat': [], 'checkin_at': [d * DAY + 30_000 + d for d in range(10)], 'batch_days': 4}
    r = bs.scan(f)
    assert r['verdict'] == 'bot' and {h['engine'] for h in r['hits']} == {'reward_farmer', 'clockwork', 'batch_cluster'}
    assert all(h['evidence'][0]['source'] for h in r['hits'])


def test_wash_dust_spam_referral_selfdeal():
    wash = [x for i in range(4) for x in ({'ts': i * 1000, 'side': 'buy', 'usd': 50, 'token': 'A'}, {'ts': i * 1000 + 60, 'side': 'sell', 'usd': 49.5, 'token': 'A'})]
    assert bs.wash_trader({'trades': wash})['score'] >= 65
    assert bs.dust_farmer({'trades': [{'usd': 0.2}] * 12})
    assert bs.chat_spam({'chat': [{'ts': i, 'text': 'FREE AIRDROP'} for i in range(25)]})['score'] >= 70
    assert bs.referral_farm({'invitees': [{'active': False}] * 9 + [{'active': True}]})
    assert bs.fuse_self_deal({'own_fuse_buys': 3})['score'] == 80


def test_manual_and_protected_win_and_batch_days():
    f = {'signin_days': list(range(15)), 'trades': [], 'chat': []}
    assert bs.scan(f, manual='cleared')['verdict'] == 'clean' and bs.scan({}, manual='bot')['verdict'] == 'bot'
    assert bs.scan(f, protected=True)['verdict'] == 'clean'
    ck = {w: [d * DAY + 100 + i for d in range(4)] for i, w in enumerate('ABCD')}
    assert bs.batch_days(ck, 'A') == 4 and bs.batch_days({'A': [5], 'B': [500]}, 'A') == 0
    assert bs.rep_penalty({'verdict': 'bot'}) == -40


def test_service_gates_rewards_case_and_fuse_cut(monkeypatch):
    import asyncio
    import pytest
    rs = pytest.importorskip('reputation_service')
    farm = 'Farm111111111111111111111111111111111111111'
    rs._json_save(rs.QUEST_STATE_PATH, {farm: {'days': [f'2026-09-{d:02d}' for d in range(1, 20)], 'checkinAt': [], 'first': 1}})
    monkeypatch.setattr(rs, '_session_or_401', lambda a, s: rs.primary_of(a))
    rs._shield_cache.clear()
    assert asyncio.run(rs._shield_of(farm))['verdict'] == 'bot'                       # 19 check-ins, never traded
    r = asyncio.run(rs.quest_checkin(rs.QuestCheckin(address=farm, session='s')))
    assert r['shield'] == 'bot' and r['fresh'] is False                                 # no reward
    t = asyncio.run(rs.trust_score(farm)) if hasattr(rs, 'trust_score') else None
    if t and t.get('parts'):
        assert any('Bot shield' in p['label'] for p in t['parts'])
    rs._json_save(rs.SHIELD_PATH, {'manual': {rs.primary_of(farm): 'cleared'}}); rs._shield_cache.clear()
    assert asyncio.run(rs._shield_of(farm))['verdict'] == 'clean'                       # HQ decision wins
