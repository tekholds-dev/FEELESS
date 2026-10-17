"""🗂 runners.json's 1.8 MB of price paths live in their own store: the main file is written without them, every load still sees them."""
import json


def test_paths_are_saved_apart_and_loaded_back():
    import reputation_service as rs
    d = {'rounds': [{'id': 1}], 'paths': {'M': [[1, 2.0]]}}
    rs._json_save(rs.RUNNERS_PATH, d)
    assert 'paths' not in json.loads(rs.RUNNERS_PATH.read_text())
    rs._parse_cache.clear()
    back = rs._json_load(rs.RUNNERS_PATH, {})
    assert back['paths'] == {'M': [[1, 2.0]]} and back['rounds'] == [{'id': 1}]
    rs._paths_mem.flush()
    assert json.loads(rs.RUNNER_PATHS_PATH.read_text()) == {'M': [[1, 2.0]]}
