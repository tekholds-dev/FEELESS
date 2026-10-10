import asyncio
import json

import edge_audit as ea


def _coins(n, f, end, at0=0, gone=False):
    return [{'at': at0 + i, 'f': list(f), 'end': end, 'gone': gone} for i in range(n)]


def test_a_rule_passes_only_when_it_is_positive_after_costs_on_coins_it_was_not_picked_from():
    assert ea.gate({}) == 'wait' and ea.gate(ea.audit(_coins(60, ['age:12h+'], 5.0))) == 'wait'          # too little data: never judged
    # 600 coins that lose, old or new: nothing passes → HOLD
    lose = _coins(300, ['age:<15m', 'safe:yes'], -60.0) + _coins(300, ['age:12h+', 'safe:yes'], 1.0, 300)   # +1% before a 3% cost = a loss
    a = ea.audit(lose, now=9)
    assert a['n'] == 600 and a['held'] == 0 and a['trainPos'] == 0 and a['tested'] >= 2 and ea.gate(a) == 'hold' and a['base']['up'] == 0
    assert '0 of' in ea.words(a) and 'not buying' in ea.words(a) and a['old']['med'] == -2.0
    # a rule that only worked in the OLD data does not pass (learned +, unseen −)
    drift = _coins(360, ['age:12h+'], 9.0) + _coins(240, ['age:12h+'], -9.0, 400)
    b = ea.audit(drift)
    assert b['trainPos'] >= 1 and b['held'] == 0 and ea.gate(b) == 'hold'
    # a rule positive in BOTH halves passes → TRADE; a vanished coin counts −100; one freak cannot carry a bucket (capped at +100)
    good = _coins(600, ['age:12h+', 'cap:1M+'], 8.0)
    c = ea.audit(good)
    assert c['held'] >= 1 and ea.gate(c) == 'trade' and c['rules'][0]['med'] == 5.0 and 'pass on unseen' in ea.words(c)
    freak = _coins(599, ['x:a'], -10.0) + [{'at': 1, 'f': ['x:a'], 'end': 900000.0}]
    assert ea.audit(freak)['held'] == 0 and ea.audit(_coins(600, ['x:a'], 50.0, gone=True))['base']['med'] == -100.0
    ag = ea.audit(lose, [{'kind': 'enter', 'p5': 1.0}, {'kind': 'wait', 'p5': 5.0}])['agents']
    assert ag['enter5']['med'] == -2.0 and ag['wait5']['up'] == 100


def test_the_proof_gate_holds_the_real_card_while_nothing_passes_releases_when_a_rule_does_and_never_touches_the_owners_own_hold(monkeypatch):
    import reputation_service as rs
    lose = _coins(600, ['age:<15m'], -60.0)
    good = _coins(600, ['age:12h+'], 8.0)
    sent = []
    monkeypatch.setattr(rs, 'notify', lambda *a, **k: sent.append(a[2]))
    monkeypatch.setattr(rs, '_owner_wallets', lambda: ['OWNER'])
    save = lambda cards, gate=True: rs._json_save(rs.FUSE_HQ_PATH, {'prime': {'realCfg': rs._prime.clean_cfg({'proofGate': gate}), 'cards': cards}})
    card = lambda: json.loads(json.dumps(rs._json_load(rs.FUSE_HQ_PATH, {})))['prime']['cards']
    rs._json_save(rs.BRAIN_PATH, {'done': lose}); rs._json_save(rs.AGENTS_PATH, {'done': []})
    save({'degen': {'real': True, 'events': []}, 'safe': {'events': []}}, gate=False)
    asyncio.run(rs._proof_gate_tick(1000))
    assert not card()['degen'].get('holdAll') and rs._json_load(rs.EDGE_AUDIT_PATH, {})['gate'] == 'hold'      # gate off: audited, never held
    save({'degen': {'real': True, 'events': []}, 'safe': {'events': []}})
    asyncio.run(rs._proof_gate_tick(1000))
    c = card()
    assert c['degen']['holdAll'] is True and c['degen']['holdBy'] == 'proof' and 'not buying' in c['degen']['events'][-1]['why']
    assert not c['safe'].get('holdAll') and len(sent) == 1                                                       # paper cards are never held
    rs._json_save(rs.BRAIN_PATH, {'done': good})
    asyncio.run(rs._proof_gate_tick(5000))
    c = card()
    assert c['degen']['holdAll'] is False and 'holdBy' not in c['degen'] and 'trades again' in c['degen']['events'][-1]['why'] and len(sent) == 2
    save({'degen': {'real': True, 'holdAll': True, 'events': []}})                                               # the owner's OWN hold
    asyncio.run(rs._proof_gate_tick(9000))
    assert card()['degen']['holdAll'] is True and 'holdBy' not in card()['degen']                                # a passing rule never lifts it
    assert rs._prime.clean_cfg({})['proofGate'] is False


def test_a_proof_hold_buys_nothing_not_even_idle_cash_into_held_coins():
    import fuse_wallet as fw
    card = {'legs': [{'mint': 'A', 'pairAddress': 'PA', 'symbol': 'A', 'units': 10, 'entry': 1.0}], 'holdAll': True, 'holdBy': 'proof'}
    assert fw.idle_sweep('degen', card, {'sol': 1.0}, {}, 1.0, 100.0, {}, 1000) is None
    import inspect, arena_prime as ap
    assert "c.get('holdBy') != 'proof'" in inspect.getsource(ap.tick)          # the engine's own idle-cash compound is gated too
