import json

import provider_ready as pr


def test_names_and_booleans_only_and_an_any_or_all_rule():
    env = {'HELIUS_API_KEY': 'SECRETVALUE123', 'DROPBOX_APP_KEY': 'SECRETVALUE456'}
    out = pr.status(env); by = {r['name']: r for r in out['rows']}
    assert by['Helius RPC']['ready'] and by['Helius RPC']['missing'] == []             # either key will do
    assert not by['Dropbox']['ready'] and by['Dropbox']['missing'] == ['DROPBOX_APP_SECRET']   # half a pair is not ready
    assert out['rows'][0]['ready'] is False and out['total'] == len(pr.PROVIDERS) and out['ready'] == 1
    assert 'SECRETVALUE' not in json.dumps(out)
