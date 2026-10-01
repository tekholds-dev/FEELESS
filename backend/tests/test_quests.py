"""Quest engine: every badge is earned only by the activity behind it; admin edits and grants apply; quests tick by day."""
import time

import quests as q

NOW = 1_800_000_000.0
FEE = 'FeeMint1111111111111111111111111111111111111'


def raw(**kw):
    base = {'trades': [], 'chat': [], 'call_ts': [], 'signin_days': [], 'fee_mints': [FEE], 'fee_usd': 0, 'first_seen': NOW - 40 * q.DAY}
    return {**base, **kw}


def badge(s, bid):
    return next(b for b in s['badges'] if b['id'] == bid)


def test_forty_badges_two_sets_with_art_and_tasks():
    assert len(q.DEFAULTS) == 45   # 20 FEELESS + 20 FRSV + 5 Fuse (one season)
    assert {d['set'] for d in q.DEFAULTS} == {'feeless', 'frsv'}
    assert all(d['tasks'] and q.is_valid_def(d) for d in q.DEFAULTS)
    assert badge({'badges': q.DEFAULTS}, 'frsv-diamond_hands')['art'] == '/assets/badges/frsv/diamond_hands'
    # every FRSV badge needs $FEE held (or is the timed Founder that also needs it)
    assert all(any(t['metric'] == 'fee_usd' for t in d['tasks']) for d in q.DEFAULTS if d['set'] == 'frsv')


def test_recruit_and_trader_earned_from_real_activity():
    trades = [{'side': 'buy', 'usd': 20, 'token': f'C{i % 4}', 'ts': NOW - 3600} for i in range(10)]
    s = q.summary(q.DEFAULTS, raw(trades=trades, chat=[{'room': 'r1', 'chain': 'solana', 'ts': NOW - 60}], signin_days=['2027-01-15']), now=NOW)
    assert badge(s, 'q-recruit')['earned'] and badge(s, 'q-trader')['earned']
    assert not badge(s, 'q-pro')['earned'] and badge(s, 'q-pro')['tasks'][0]['have'] == 10
    assert s['quests']['daily']['tasks'][1] == {'id': 'trade', 'label': 'Make a trade', 'have': 10, 'target': 1, 'xp': 15, 'done': True}
    assert s['level']['xp'] > 0


def test_diamond_hands_counts_days_since_last_fee_sell():
    trades = [{'side': 'buy', 'usd': 50, 'token': FEE, 'ts': NOW - 60 * q.DAY}, {'side': 'sell', 'usd': 10, 'token': FEE, 'ts': NOW - 40 * q.DAY},
              {'side': 'buy', 'usd': 50, 'token': FEE, 'ts': NOW - 35 * q.DAY}]
    m = q.metrics(raw(trades=trades, fee_usd=30), NOW)
    assert m['diamond_days'] == 35 and m['fee_buys'] == 2
    assert q.metrics(raw(trades=trades, fee_usd=0), NOW)['diamond_days'] == 0   # sold it all: no streak


def test_admin_edit_grant_and_revoke():
    defs = q.merge(q.DEFAULTS, {'badges': {'q-trader': {'tasks': [{'metric': 'trades', 'target': 2, 'label': '2 trades'}]},
                                           'q-custom': {'name': 'Night Owl', 'tier': 'epic', 'tasks': [{'metric': 'streak', 'target': 3, 'label': '3-day streak'}]}}})
    s = q.summary(defs, raw(trades=[{'side': 'buy', 'usd': 1, 'token': 'X', 'ts': NOW}] * 2, streak=3), manual={'grant': ['q-vip'], 'revoke': ['q-recruit']}, now=NOW)
    assert badge(s, 'q-trader')['earned'] and badge(s, 'q-custom')['earned'] and badge(s, 'q-custom')['name'] == 'Night Owl'
    assert badge(s, 'q-vip')['earned'] and badge(s, 'q-vip')['granted']
    assert not badge(s, 'q-recruit')['earned']


def test_weekly_window_resets_monday_utc():
    s = q.quests(raw(signin_days=[time.strftime('%Y-%m-%d', time.gmtime(NOW - k * q.DAY)) for k in range(10)]), now=NOW)
    assert s['weekly']['tasks'][0]['have'] == time.gmtime(NOW).tm_wday + 1
    assert s['daily']['resetsAt'] == NOW // q.DAY * q.DAY + q.DAY
