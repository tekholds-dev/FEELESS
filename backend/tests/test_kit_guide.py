"""🌊 A source with no text guide of its own (Scrolltide) is saved from our own written notes: no download, links only, its license kept."""
import asyncio

import collective_kits as k


def test_a_written_guide_saves_without_a_download(tmp_path):
    class NoNet:
        async def get(self, *a, **kw): raise AssertionError('must not download')
    asyncio.run(k.add(NoNet(), tmp_path, 'scrolltide'))
    kit = k.load(tmp_path, 'scrolltide')
    assert 'https://www.scrolltide.co/templates/selene' in kit['text'] and 'never resell or share the prompts' in kit['license']
    assert kit['text'].count('https://www.scrolltide.co/templates/') == 7
