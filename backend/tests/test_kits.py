"""🧰 The kit library. No network."""
import asyncio
import pytest
import collective_kits as ck


class R:
    status_code = 200; headers = {'content-type': 'text/plain'}; text = '# guide'
class H:
    def __init__(self): self.asked = []
    async def get(self, url, **kw):
        self.asked.append(url); return R()


def test_only_a_catalog_kit_downloads_and_it_reaches_the_repo(tmp_path):
    h = H(); asyncio.run(ck.add(h, tmp_path, 'shadcn'))
    assert h.asked == [ck.CATALOG['shadcn']['url']] and b'# guide' in ck.tree(tmp_path)['kits/shadcn.md']
    with pytest.raises(ValueError):
        asyncio.run(ck.add(h, tmp_path, 'https://evil.test/x'))


def test_a_secret_is_never_saved(tmp_path):
    ck.save(tmp_path, {'id': 'a', 'name': 'A', 'kinds': ['pos'], 'text': 'x'})
    with pytest.raises(ValueError):
        ck.edit(tmp_path, 'a', text='ghp_' + 'a' * 30)
    assert ck.load(tmp_path, 'a')['text'] == 'x'


def test_picks_come_first_the_rest_fill_and_the_prompt_stays_small(tmp_path):
    for k in ('a', 'b', 'c'):
        ck.save(tmp_path, {'id': k, 'name': k.upper(), 'kinds': ['pos'], 'text': k * 90000})
    t = ck.line(tmp_path, 'pos', ['c'])
    assert t.index('[C]') < t.index('[A]') and 'Use C first' in t and len(t) < ck.PROMPT_CHARS + 400
    assert ck.line(tmp_path, 'pow') == ''
