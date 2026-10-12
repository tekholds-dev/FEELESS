"""📏 Kernel timings: decision → order, order → fill (from the keeper's ledger), wake → decision, age at entry; ORDER_PENDING in the lifecycle."""
from pathlib import Path

import trench_kernel.kernel as tk
import trench_kernel.metrics as km

from kernel_helpers import row

SRC = (Path(__file__).resolve().parent.parent / 'reputation_service.py').read_text()


def test_timings_are_bounded_rings_with_percentiles():
    t = km.Timings()
    for i in range(km.KEEP + 50):
        t.note('readyToSeatSec', float(i))
    t.note('ageAtEntryMin', None)                                           # an unknown is not a 0
    v = t.view()
    assert v['readyToSeatSec']['n'] == km.KEEP and v['readyToSeatSec']['last'] == km.KEEP + 49 and v['readyToSeatSec']['p50'] > 50 and 'ageAtEntryMin' not in v


def test_execution_latency_comes_from_the_keepers_confirmed_rows_only():
    ev = [{'kind': 'agent', 'move': 'fill', 'mint': 'A', 'at': 1000.0}, {'kind': 'agent', 'move': 'fill', 'mint': 'B', 'at': 1010.0},
          {'kind': 'agent', 'move': 'fill', 'mint': 'C', 'at': 1020.0}, {'kind': 'agent', 'move': 'pull', 'mint': 'A', 'at': 1500.0}]
    ledger = [{'card': 'c', 'side': 'buy', 'status': 'filled', 'sig': 'S1', 'mint': 'A', 'at': 1009.0, 'sentAt': 1003.0, 'confirmedAt': 1009.0, 'landSec': 6.0},
              {'card': 'c', 'side': 'buy', 'status': 'failed', 'sig': 'S2', 'mint': 'B', 'at': 1015.0},                      # never confirmed: not a fill
              {'card': 'c', 'side': 'buy', 'status': 'filled', 'mint': 'C', 'at': 1030.0, 'landSec': 4.0},                    # no signature: not a fill either
              {'card': 'other', 'side': 'buy', 'status': 'filled', 'sig': 'S3', 'mint': 'B', 'at': 1016.0, 'landSec': 2.0}]   # another card's buy
    x = km.execution(ledger, ev, 'c', 2000.0)
    assert x['fills'] == 1 and x['unmatched'] == 2
    assert x['decisionToSubmitSec']['p50'] == 3.0 and x['submitToConfirmSec']['p50'] == 6.0 and x['decisionToConfirmSec']['p50'] == 9.0
    assert km.execution([], ev, 'c', 2000.0)['decisionToConfirmSec'] == {'n': 0, 'p50': None, 'p95': None, 'last': None, 'max': None}   # nothing measured = nothing claimed


def test_a_seat_being_bought_is_order_pending_and_never_a_candidate_again():
    k = tk.Kernel()
    k.run([row('A'), row('B')], 100.0, {})
    assert {m for m, _d in k.ready()} == {'A', 'B'}
    k.run([row('A'), row('B')], 110.0, {'pending': {'A'}})
    assert k.dec['A']['status'] == 'ORDER_PENDING' and [m for m, _d in k.ready()] == ['B']
    k.run([row('A'), row('B')], 120.0, {'held': {'A': {'entry': 1.0, 'peak': 0, 'stopNow': 30}}})        # the ledger confirmed it: HELD
    assert k.dec['A']['status'] == 'HELD' and k.lanes[0] == {'lane': 1, 'state': 'HELD', 'mint': 'A'}
    k2 = tk.Kernel(); k2.run([row('A')], 100.0, {'pending': {'A'}}); k2.run([row('A')], 110.0, {})        # the buy was called off: it is judged again
    assert k2.dec['A']['status'] == 'READY'
    assert k.metrics(120.0)['byStatus']['HELD'] == 1 and 'timings' in k.metrics(120.0)


def test_the_service_notes_each_timing_where_it_happens():
    for s in ("K_.timings.note('readyToSeatSec'", "K_.timings.note('discoveryToEntrySec'", "K_.timings.note('ageAtEntryMin'", "_tk.KERNEL.timings.note('wakeToDecisionSec'",
              "row['sentAt'], row['confirmedAt'] =", "v['metrics']['execution'] = _tkm.execution(_office_ledger(), ev_, tid_, now)", "rpcStats=_chain.rpc_metrics(now)", "**_ENRICH.metrics(now)"):
        assert s in SRC, s
