"""Owner 2026-11-14: "all my agents i own should follow the same openrouter key" — owner agents borrow it; a user's agent never does."""
import cat_keys as ck


def test_owner_agents_share_one_key_users_never(monkeypatch):
    seen = []
    monkeypatch.setattr(ck, 'unseal', lambda tok, cid, env=None, data_dir=None: seen.append(cid) or f'key-of-{cid}')
    monkeypatch.setitem(ck.OWNER_DONOR, 'fn', lambda p: ({'sealed': 'x', 'at': 1}, 'happy', 'Happy') if p == 'openrouter' else None)
    fee = {'id': 'fee', 'ownerStaff': True}
    assert ck.key_for(fee, 'openrouter') == 'key-of-happy' and seen[-1] == 'happy'      # unsealed with the donor's own id
    assert ck.key_for({'id': 'u1'}, 'openrouter') is None                                 # a user's agent never borrows
    assert ck.key_for(fee, 'kalshi') is None                                              # only OpenRouter is shared
    own = {'id': 'g4', 'ownerStaff': True, 'apiKeys': {'openrouter': {'sealed': 'y'}}}
    assert ck.key_for(own, 'openrouter') == 'key-of-g4'                                   # its own key wins
    row = next(r for r in ck.public(fee) if r['provider'] == 'openrouter')
    assert row['sharedFrom'] == 'Happy' and not row['saved'] and 'sealed' not in str(row)
    assert next(r for r in ck.public({'id': 'happy', 'ownerStaff': True, 'apiKeys': {'openrouter': {'sealed': 'x', 'last4': 'abcd'}}}) if r['provider'] == 'openrouter')['sharedFrom'] is None
