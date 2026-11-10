"""COL-25 (found 2026-11-10): filed real PoWs lost their order ids and chain proof, so none was checked against the chain. Each one with its own
buy and sell in the agent's transactions is now read back once; P&L becomes the net of the two real fills. Reads only."""
import asyncio

import pow as pw


def test_match_sigs_takes_the_folders_own_buy_then_sell():
    f = {'mint': 'M', 'at': 1000, 'soldAt': 2000}
    tx = [{'mint': 'M', 'side': 'sell', 'status': 'success', 'sig': 'old', 'at': 500},          # before the folder: not its
          {'mint': 'M', 'side': 'buy', 'status': 'failed', 'sig': 'f', 'at': 1001},
          {'mint': 'M', 'side': 'buy', 'status': 'success', 'sig': 'B', 'at': 1010, 'pid': 'pb'},
          {'mint': 'X', 'side': 'sell', 'status': 'success', 'sig': 'x', 'at': 1500},
          {'mint': 'M', 'side': 'sell', 'status': 'success', 'sig': 'S', 'at': 1990, 'pid': 'ps'}]
    b, s = pw.match_sigs(f, tx)
    assert (b['sig'], s['sig']) == ('B', 'S')
    assert pw.match_sigs({**f, 'mint': 'Z'}, tx) is None and pw.match_sigs(f, tx[:3]) is None   # no sell: nothing linked
    assert 'pid' in pw.folder_public({'pid': 'p', 'buySig': 'B', 'settlementVerified': True, 'id': 'x'})   # filing keeps the proof now


def test_relink_reads_the_chain_once_and_sets_true_pnl(monkeypatch):
    import feecat_service as fs
    f = {'id': 'pow1', 'real': True, 'mint': 'M', 'at': 1000, 'soldAt': 2000, 'pnlSol': 0.001, 'pnlPct': 5.0}
    cat = {'agentWallet': {'address': 'W'}, 'powFolders': [f, {'id': 'paper', 'mint': 'M', 'at': 1000}],
           'agentTx': [{'mint': 'M', 'side': 'buy', 'status': 'success', 'sig': 'B', 'at': 1010, 'pid': 'pb'}, {'mint': 'M', 'side': 'sell', 'status': 'success', 'sig': 'S', 'at': 1990, 'pid': 'ps'}]}
    reads = []
    async def rpc(http, method, params, scan=False):
        reads.append(params[0]); return {'sig': params[0]}
    monkeypatch.setattr(fs._crpc, '_rpc', rpc)
    monkeypatch.setattr(fs._fills, 'raw_fill', lambda tx, w, m: {'side': 'buy', 'cashSol': 0.01} if tx['sig'] == 'B' else {'side': 'sell', 'cashSol': 0.008})
    fs._RELINKED.clear()
    assert asyncio.run(fs._pow2_relink({'cats': {'c': cat}})) == 1
    assert (f['settlementVerified'], f['buySig'], f['sellSig'], f['pid'], f['sellPid']) == (True, 'B', 'S', 'pb', 'ps')
    assert f['pnlSol'] == -0.002 and f['pnlPct'] == -20.0 and reads == ['B', 'S']   # the server's own +5% was wrong: the fills say -20%
    assert asyncio.run(fs._pow2_relink({'cats': {'c': cat}})) == 0 and reads == ['B', 'S']   # once only
