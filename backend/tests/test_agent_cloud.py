"""☁ An agent's cloud starts with its first real deposit (owner 2026-10-30): 1 GB in the first free pool FEELESS holds keys for (R2 → B2 →
Filebase, one S3 API), else the FEELESS server. Faked S3 — no network, no real bucket."""
import base64

import pytest

PNG = 'data:image/png;base64,' + base64.b64encode(b'\x89PNG\r\n\x1a\n' + b'0' * 64).decode()
MP4 = 'data:video/mp4;base64,' + base64.b64encode(b'\x00\x00\x00\x18ftypmp42' + b'0' * 64).decode()
KEYS = {f'R2_S3_{k}': 'x' for k in ('ENDPOINT', 'KEY_ID', 'SECRET', 'BUCKET')}


def test_no_cloud_before_a_deposit_and_the_server_pool_without_keys(tmp_path):
    af = pytest.importorskip('agent_files')
    cat = {'id': 'a1'}
    with pytest.raises(ValueError, match='first real deposit'):
        af.save(tmp_path, cat, PNG, 'logo.png', env={})
    row = af.start_cloud(cat, [cat], env={}, now=100)
    assert row == {'pool': 'feeless', 'label': 'FEELESS server', 'quota': af.QUOTA, 'startedAt': 100, 'seen': False}
    assert af.start_cloud(cat, [cat], env={}) is None                      # once per agent
    f = af.save(tmp_path, cat, PNG, 'logo.png', env={})
    assert af.read(tmp_path, cat, f['id'], env={}).startswith(b'\x89PNG') and af.public(cat)['cloud']['label'] == 'FEELESS server'
    clip = af.save(tmp_path, cat, MP4, 'clip.mp4', env={})
    assert clip['mime'] == 'video/mp4'
    with pytest.raises(ValueError):
        af.save(tmp_path, cat, 'data:video/mp4;base64,' + base64.b64encode(b'not a video at all').decode(), env={})


def test_keys_pick_the_first_free_pool_until_it_is_full(monkeypatch):
    af = pytest.importorskip('agent_files')
    full = [{'cloud': {'pool': 'R2'}} for _ in range(10)]                  # R2's 10 GB = 10 agents
    a, b = {'id': 'a'}, {'id': 'b'}
    assert af.start_cloud(a, [a], env=KEYS)['label'] == 'Cloudflare R2'
    both = {**KEYS, **{f'B2_S3_{k}': 'y' for k in ('ENDPOINT', 'KEY_ID', 'SECRET', 'BUCKET')}}
    assert af.start_cloud(b, full + [b], env=both)['pool'] == 'B2'
    assert af.pools({'R2_S3_ENDPOINT': 'x'}) == []                        # half a key set is no pool


def test_a_remote_pool_puts_reads_and_deletes_in_its_own_folder(tmp_path, monkeypatch):
    af = pytest.importorskip('agent_files')
    bucket = {}

    class S3:
        def put_object(self, Bucket, Key, Body, ContentType):
            bucket[Key] = Body

        def get_object(self, Bucket, Key):
            return {'Body': type('B', (), {'read': lambda self: bucket[Key]})()}

        def delete_object(self, Bucket, Key):
            bucket.pop(Key)
    monkeypatch.setattr(af, '_s3', lambda pool, env=None: (S3(), 'feeless-agents'))
    cat = {'id': 'a7'}
    af.start_cloud(cat, [cat], env=KEYS)
    f = af.save(tmp_path, cat, PNG, 'coin.png', env=KEYS)
    assert list(bucket) == [f"agents/a7/{f['id']}.png"] and not (tmp_path / 'agent_files' / 'a7').exists()
    assert af.read(tmp_path, cat, f['id']).startswith(b'\x89PNG')
    assert af.local_copy(tmp_path, cat, f['id']).read_bytes().startswith(b'\x89PNG')   # its browser can still upload it
    assert af.delete(tmp_path, cat, f['id']) and bucket == {}
