"""Owner 2026-11-14: one agent runs at most 3 proofs at once (PoC beside a PoB is fine; a 4th is refused)."""
import feecat_service as fs


def test_three_proofs_max_and_a_poc_beside_a_pob():
    cid = 'cap-test-cat'
    cat = {'name': 'Happy', 'pobRun': {'id': 'b1'}}
    assert fs._active_proofs(cat, cid) == ['PoB']
    assert fs._proof_room(cat, cid, 'PoC') is None          # PoC while the PoB waits on its game
    fs._POC_BUSY.add(cid)
    try:
        cat['popRun'] = {'id': 'p1'}
        assert fs._active_proofs(cat, cid) == ['PoP', 'PoB', 'PoC']
        why = fs._proof_room(cat, cid, 'PoW')
        assert why and '3 proofs' in why and 'PoB' in why and 'Happy' in why
        assert fs._proof_room(cat, cid, 'PoB') is None      # same kind → its own guard answers, not the cap
        ok, say = fs._site_proof_start(cat, cid, 'pump', 'pow')
        assert ok is False and '3 proofs' in say
    finally:
        fs._POC_BUSY.discard(cid)
    assert fs._proof_room(cat, cid, 'PoW') is None


def test_a_pob_ask_a_restart_orphaned_still_starts_and_frees_its_slot(monkeypatch):
    import asyncio
    cat = {'id': 'orph', 'name': 'Happy', 'pobAsk': 'NBA tonight', 'chat': []}
    fs._POB_WANT.pop('orph', None)                                    # the restart lost the start signal
    assert fs._active_proofs(cat, 'orph') == ['PoB']
    monkeypatch.setattr(fs, '_topic_shared', lambda t, n: None)
    monkeypatch.setattr(fs, '_read_start', lambda *a, **k: 'no model credit')   # it can't browse → it files and frees the slot, never hangs
    asyncio.run(fs._pob_tick(None, cat, 1.0))
    assert 'pobAsk' not in cat and fs._active_proofs(cat, 'orph') == [] and 'not filed' in cat['chat'][-1]['text']
