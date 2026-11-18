"""🧾 COMP and its teacher read what a proof DID (owner audit 2026-11-18: they were reading a title and a topic only). Pure; no network."""
import json

import model_lab as ml


def test_a_bid_proof_carries_its_calls_bid_game_and_review():
    d = {'topic': 'Jazz vs Clippers', 'calls': [{'name': 'mind-a', 'picks': [], 'pass': 'Clippers at 0.68 is over ESPN 62%'},
                                               {'name': 'mind-b', 'picks': [{'pick': 'Clippers -4.5', 'confidence': 62, 'why': 'LAC -5.5 on ESPN'}]}],
         'kalshi': {'title': 'Parlay', 'side': 'yes', 'price': 0.39, 'count': 1, 'status': 'filled', 'legs': [{'title': 'LA Clippers', 'side': 'yes', 'price': 0.68}]},
         'games': [{'label': 'Jazz at Clippers', 'status': 'Final', 'score': '101 - 112', 'won': True}],
         'review': {'by': {'ossy': {'score': 20, 'verdict': 'fail', 'checks': ['✗ no sources']}}},
         'browsed': {'0': {'note': 'a long page dump that must stay out'}}}
    ev = ml.evidence(d)
    assert ev[0] == 'call mind-a: PASS · Clippers at 0.68 is over ESPN 62%'
    assert ev[1] == 'call mind-b: Clippers -4.5 · 62% · LAC -5.5 on ESPN'
    assert 'bid: Parlay · yes @ 0.39 × 1 · filled' in ev and 'leg: LA Clippers · yes @ 0.68' in ev
    assert 'game: Jazz at Clippers · Final · score 101 - 112 · side won' in ev
    assert ev[-1].startswith('review ossy: 20 · fail') and not any('page dump' in x for x in ev)


def test_evidence_is_scrubbed_capped_and_safe_on_junk():
    wallet = '7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU'
    ev = ml.evidence({'calls': [{'name': 'a', 'side': 'long', 'market': 'SOL', 'lev': 2, 'why': f'send to {wallet}'}] * 4, 'whys': ['x' * 900] * 2}, cap=400)
    assert wallet not in ' '.join(ev) and sum(len(x) + 1 for x in ev) <= 400
    assert ml.evidence({'calls': 'junk', 'kalshi': 'junk', 'games': [None], 'review': {'by': {'x': 'junk'}}}) == []


def test_text_of_appends_the_evidence_under_the_words():
    raw = json.dumps({'topic': 'Hornets vs Lakers', 'games': [{'label': 'Hornets at Lakers', 'status': 'pre', 'score': '0 - 0', 'won': None}]}).encode()
    t = ml.text_of({'category': next(iter(ml.KINDS)), 'title': 'Hornets vs Lakers', 'outcome': 'open'}, raw)
    assert 'topic: Hornets vs Lakers' in t and 'game: Hornets at Lakers · pre · score 0 - 0 · not settled' in t
