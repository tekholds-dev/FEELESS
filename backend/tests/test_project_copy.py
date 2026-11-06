"""Copying from the git folder to his own repo: only files in the folder, a build takes its page, never a secret."""
import json

import feecat_service as fs


def test_a_build_proof_takes_its_page_and_a_missing_file_goes_nowhere(monkeypatch):
    monkeypatch.setattr(fs, '_load', lambda: {'cats': {'a': {'id': 'a', 'psFolders': [{'ws': 'w1'}]}}})
    monkeypatch.setattr(fs, '_git_page', lambda c, w: ('<html>page</html>', 'x'))
    files = {'proofs/Code/open/x.json': json.dumps({'ws': 'w1', 'topic': 'test'}).encode(), 'proofs/PoW/won/y.json': b'{}'}
    out = fs._copy_files({}, files, ['proofs/Code/open/x.json', 'nope.json'])
    assert sorted(out) == ['feeless/proofs/Code/open/x.html', 'feeless/proofs/Code/open/x.json'] and out['feeless/proofs/Code/open/x.html'] == b'<html>page</html>'
    assert fs._copy_files({}, files, ['nope.json']) == {}
    assert list(fs._copy_files({}, files, ['proofs/PoW/won/y.json'])) == ['feeless/proofs/PoW/won/y.json']


def test_a_file_holding_a_key_never_leaves(monkeypatch):
    bad = {'proofs/a.json': b'{"note":"ghp_' + b'a' * 36 + b'"}'}
    assert fs._copy_files({}, bad, ['proofs/a.json']) == {}
