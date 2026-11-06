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


def test_vitals_come_from_the_guide_itself():
    v = ck.vitals('# Docs\n## Buttons\n- [Button](u): x\n- [Card](u)\n- [Button](u)\n')
    assert v['items'] == 3 and v['sections'] == ['Docs', 'Buttons'] and v['sample'] == ['Button', 'Card']
    assert ck.vitals('')['items'] == 0 and ck.MAX_PICKS == 3


def test_agent_chooses_kits_for_the_request_and_may_look_outside(tmp_path):
    ck.save(tmp_path, {'id': 'a', 'name': 'Alpha', 'what': 'Animated landing pages', 'kinds': ['poc'], 'text': '- [Hero](x)'})
    ck.save(tmp_path, {'id': 'b', 'name': 'Beta', 'what': 'Data tables', 'kinds': ['pos'], 'text': '- [Grid](x)'})
    assert ck.auto_picks(tmp_path, 'pos', 'an animated landing page')[0] == 'a'
    assert ck.auto_picks(tmp_path, 'pow', 'nothing matches') == []
    assert 'free, open-source' in ck.line(tmp_path, 'pos', ['b'], open_kits=True)
    assert 'free, open-source' in ck.line(tmp_path, 'pow', [], open_kits=True)
    assert 'free, open-source' not in ck.line(tmp_path, 'pos', ['b'])
    assert 'Alpha' in ck.line(tmp_path, 'pos', ['a'])   # a pick is read even outside its usual kind


def test_catalog_view_marks_what_is_not_downloaded_yet(tmp_path):
    ck.save(tmp_path, {'id': 'heroui', 'name': 'HeroUI', 'what': 'x', 'kinds': ['pos'], 'text': '- [Button](x)'})
    rows_ = {r['id']: r for r in ck.catalog_view(tmp_path)}
    assert rows_['heroui']['added'] and rows_['heroui']['vitals']['items'] == 1 and rows_['shadcn']['added'] is False and len(rows_) == len(ck.CATALOG)
