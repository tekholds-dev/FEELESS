"""🔌 Owner 2026-10-23: "G4 keeps unloading … I hate walking to 2 other PCs". Every LM Studio call asks for a 7-day idle TTL, and an EMPTY
server gets its model loaded by the heartbeat at most once per 10 min — a loaded model is never reloaded."""
import ai_router as ar


def test_every_lm_call_keeps_the_model_loaded():
    assert ar.EXTRA_BODY['lan']['ttl'] >= 86400 and ar.EXTRA_BODY['local']['ttl'] >= 86400


def test_empty_server_auto_load_is_rate_limited():
    assert ar.auto_load_due({}, 'lan', 1000.0) is True
    assert ar.auto_load_due({'load:lan': 1000.0}, 'lan', 1000.0 + ar.AUTO_LOAD_SEC - 1) is False
    assert ar.auto_load_due({'load:lan': 1000.0}, 'lan', 1000.0 + ar.AUTO_LOAD_SEC) is True
    assert ar.auto_load_due({'load:lan': 1000.0}, 'local', 1001.0) is True   # each box on its own clock
