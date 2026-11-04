"""🔒 What a stranger can't get from an owner's agent. No network, no money."""
import asyncio

import pytest
from fastapi import HTTPException

import agent_setup as st
import cat_keys as ck
import cat_policy as cp
import feecat_service as fs


def test_plain_http_is_never_opened():
    with pytest.raises(ValueError):
        cp.check_url('http://example.com/')
    assert cp.check_url('https://example.com/a') == 'example.com'
    assert cp.secure_url('http://example.com/a') == 'https://example.com/a'
    assert cp.secure_url('HTTP://example.com') == 'https://example.com'
    assert cp.secure_url('https://a.co') == 'https://a.co'
    for bad in ('https://localhost/', 'https://10.0.0.1/', 'https://169.254.169.254/latest', 'https://user:pw@a.co/', 'ftp://a.co', 'file:///etc/passwd', 'https://a.co:8443/'):
        with pytest.raises(ValueError):
            cp.check_url(bad)


def test_only_a_content_agent_may_post():
    for word in ('Post', 'Tweet', 'Reply', 'post now', 'Publish', '  Repost', 'Comment'):
        assert cp.is_post(word), word
    for word in ('Buy', 'Sign in', 'Next', 'Postal code', 'Sell', 'Commentary', None):
        assert not cp.is_post(word), word
    assert 'post' in cp.toolkit('content', None) and cp.toolkit('content', None)['post']
    for job in ('agent', 'code', 'detective', 'researcher', 'trading'):
        assert not cp.toolkit(job, None).get('post'), job


def test_a_snapshot_opens_only_with_its_own_agents_key():
    sealed = ck.seal_bytes(b'jpeg-bytes', 'cat-a', {'BROKER_SECRET_KEY': 'master'})
    assert b'jpeg-bytes' not in sealed
    assert ck.unseal_bytes(sealed, 'cat-a', {'BROKER_SECRET_KEY': 'master'}) == b'jpeg-bytes'
    with pytest.raises(Exception):
        ck.unseal_bytes(sealed, 'cat-b', {'BROKER_SECRET_KEY': 'master'})
    with pytest.raises(Exception):
        ck.unseal_bytes(sealed, 'cat-a', {'BROKER_SECRET_KEY': 'other'})
    assert ck.unseal_bytes(b'old-open-jpeg', 'cat-a', {'BROKER_SECRET_KEY': 'master'}) == b'old-open-jpeg'


def test_a_signed_in_page_is_private():
    cat = {'siteSessions': {'pump.fun': {}, 'polymarket.com': {}}}
    assert fs._signed_host(cat, 'https://pump.fun/profile') and fs._signed_host(cat, 'https://www.polymarket.com/x')
    assert not fs._signed_host(cat, 'https://dexscreener.com/solana')
    assert fs._shot_private(cat, 'pob123', 'm0_0.jpg')
    assert fs._shot_private(cat, 'powf1', 'g8lf8u_r0_pump.fun_1.jpg')
    assert not fs._shot_private(cat, 'powf1', 'g8lf8u_r0_jup.ag_1.jpg')
    assert fs._shot_private({**cat, 'incognito': True}, 'powf1', 'g8lf8u_r0_jup.ag_1.jpg')


def test_a_stranger_gets_nothing_private(monkeypatch, tmp_path):
    cat = {'id': 'g', 'ownerWallet': 'OWNER', 'siteSessions': {'pump.fun': {}}}
    monkeypatch.setattr(fs, '_load', lambda: {'cats': {'g': cat}})
    monkeypatch.setattr(fs, 'POWSHOTS_DIR', tmp_path)
    (tmp_path / 'pob1').mkdir(); (tmp_path / 'pob1' / 'm0_0.jpg').write_bytes(ck.seal_bytes(b'private-page', 'g'))
    (tmp_path / 'powf').mkdir(); (tmp_path / 'powf' / 'a_r0_jup.ag_1.jpg').write_bytes(b'public-page')
    monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s: {'owner': 'OWNER', 'thief': 'THIEF'}.get(s))
    assert asyncio.run(fs.pow_snapshot('g', 'powf', 'a_r0_jup.ag_1.jpg')).body == b'public-page'
    for sess, code in (('', 401), ('thief', 403)):
        with pytest.raises(HTTPException) as e:
            asyncio.run(fs.pow_snapshot('g', 'pob1', 'm0_0.jpg', session=sess))
        assert e.value.status_code == code
    assert asyncio.run(fs.pow_snapshot('g', 'pob1', 'm0_0.jpg', session='owner')).body == b'private-page'


def test_private_fields_never_leave_on_a_public_card():
    secret = {'setup': {'use': 'trade'}, 'siteWallets': {'pump.fun': 'W'}, 'siteTrades': [{}], 'siteSessions': {'pump.fun': {'ctx': 'v2:SEAL', 'at': 1, 'n': 2}}, 'mailbox': {'address': 'a@b'}, 'logins': [{'sealed': 'x', 'site': 'a.co', 'user': 'u'}], 'topups': [{}], 'name': 'ok'}
    out = fs._no_keys(secret)
    for k in ('setup', 'siteWallets', 'siteTrades', 'siteSessions', 'mailbox', 'topups'):
        assert k not in out, k
    assert 'SEAL' not in str(out) and 'sealed' not in str(out) and out['name'] == 'ok'


def test_setup_counts_real_things_and_follows_its_use():
    cat = {}
    v = st.view(cat)
    assert v['left'] == v['total'] == len(st.STEPS) and v['sites'] == []
    v = st.apply(cat, 'use', 'bids', 1)
    assert v['use'] == 'bids' and v['sites'][0][0] == 'polymarket.com' and 'post' not in [r['k'] for r in v['steps']]
    assert 'post' in [r['k'] for r in st.apply(cat, 'use', 'content', 1)['steps']] and 'trades' not in [r['k'] for r in st.view(cat)['steps']]
    done = lambda k: next(r for r in st.view(cat)['steps'] if r['k'] == k)['done']
    assert not done('email'); cat['mailbox'] = {'address': 'a@b'}; assert done('email')
    assert not done('colony'); cat['colonyShare'] = {'on': True}; assert done('colony')
    assert not done('sites'); cat['siteSessions'] = {'pump.fun': {}}; assert done('sites')
    assert not done('terms'); st.apply(cat, 'terms', '', 5); assert done('terms') and st.view(cat)['termsAt'] == 5
    st.apply(cat, 'done', 'fund', 1); assert done('fund'); st.apply(cat, 'undo', 'fund', 1); assert not done('fund')
    for bad in (('use', 'nope'), ('done', 'terms'), ('done', 'nope'), ('hack', 'x')):
        with pytest.raises(ValueError):
            st.apply(cat, *bad, 1)


def test_the_old_30_share_pays_the_new_25_cap():
    import colony
    assert colony.SHARE_PCTS[-1] == 25 and colony.share_pct(30) == 25 and colony.share_pct(26) == 0
    assert colony.share_cut(1.0, 30) == 0.25


def test_a_stranger_reads_no_private_drawer_on_the_leader(monkeypatch):
    cat = {'id': 'fee', 'isLeader': True, 'name': 'Fee', 'wins': 3, 'ownerWallet': 'OWNER', 'chat': [{'text': 'private'}], 'logins': [{'sealed': 'x', 'site': 'a.co', 'user': 'me@a.co', 'at': 1}], 'vaultLog': [{'what': 'signed in'}], 'siteSessions': {'a.co': {'ctx': 'v2:x', 'at': 1, 'n': 1}}, 'orders': [{}]}
    monkeypatch.setattr(fs, '_load', lambda: {'cats': {'fee': cat}})
    monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s: {'owner': 'OWNER'}.get(s))
    seen = asyncio.run(fs.get_cat('fee'))['cat']
    assert seen['name'] == 'Fee' and seen['wins'] == 3 and seen['mine'] is False
    for k in fs.LEADER_PRIVATE:
        assert k not in seen, k
    assert 'me@a.co' not in str(seen)
    assert asyncio.run(fs.get_cat('fee', session='owner'))['cat']['chat']


def test_the_leader_route_is_as_clean_as_the_card(monkeypatch):
    cat = {'id': 'leader', 'isLeader': True, 'name': 'Fee', 'positions': [{'symbol': 'A'}], 'chat': [{'text': 'private'}], 'logins': [{'sealed': 'x', 'site': 'a.co', 'user': 'me@a.co', 'at': 1}], 'vaultLog': [{'what': 'signed in'}], 'siteSessions': {'a.co': {'ctx': 'v2:x', 'at': 1, 'n': 1}}}
    monkeypatch.setattr(fs, '_load', lambda: {'cats': {'leader': cat}})
    monkeypatch.setattr(fs, '_migrate', lambda store: None)
    seen = asyncio.run(fs.leader())['cat']
    assert seen['positions'] and seen['name'] == 'Fee'
    for k in fs.LEADER_PRIVATE:
        assert k not in seen, k
    assert 'me@a.co' not in str(seen) and 'sealed' not in str(seen)
