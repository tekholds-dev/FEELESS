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
