"""Uploads: animated GIFs up to 6 MB keep their frames; images capped per IP; profile URLs length-checked."""
import asyncio
import base64

import pytest

rs = pytest.importorskip('reputation_service')


class Req:
    headers = {}
    class client: host = '9.9.9.9'


def _call(mime, raw):
    return asyncio.run(rs.upload_image(rs.UploadPayload(dataUrl=f'data:{mime};base64,' + base64.b64encode(raw).decode()), Req()))


def test_gif_cap_rate_limit_and_safe_url(monkeypatch, tmp_path):
    monkeypatch.setattr(rs, 'UPLOAD_DIR', tmp_path)
    monkeypatch.setattr(rs, '_require_admin', lambda r: (_ for _ in ()).throw(rs.HTTPException(403, 'no')))
    rs._upload_ip.clear()
    gif = b'GIF89a' + b'\0' * (3_000_000)
    assert _call('image/gif', gif)['url'].endswith('.gif')          # 3 MB animated cover is fine
    with pytest.raises(rs.HTTPException):
        _call('image/png', b'\x89PNG' + b'\0' * 2_100_000)            # stills stay at 2 MB
    for _ in range(18):
        _call('image/png', b'\x89PNG' + b'\0' * 10)
    with pytest.raises(rs.HTTPException) as e:
        _call('image/png', b'\x89PNG' + b'\0' * 10)
    assert e.value.status_code == 429
    assert rs._safe_url('https://x.io/' + 'a' * 500) == ''           # length limit now applies to https links too
    assert rs._safe_url('/api/reputation/uploads/abc.gif') == '/api/reputation/uploads/abc.gif'
