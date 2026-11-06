"""🖍 A box means the brain read it. No network: a fake page."""
import asyncio, io
import evidence_marks as em
from PIL import Image


def jpg(busy=True):
    im = Image.new('RGB', (200, 120), (255, 255, 255))
    if busy:
        for x in range(0, 200, 7):
            for y in range(0, 120, 5):
                im.putpixel((x, y), (x % 255, y * 2 % 255, 30))
        im = im.resize((200, 120)).point(lambda v: v)
        for x in range(200):
            for y in range(60):
                im.putpixel((x, y), (10, 10, 10))
    o = io.BytesIO(); im.save(o, 'JPEG'); return o.getvalue()


class Page:
    url = 'https://x.test/'
    def __init__(self, marks=None, pic=None):
        self.marks = marks or {}; self.pic = pic; self.asked = []
    async def find_private(self, js):
        self.asked.append(js); return self.marks
    async def shot(self):
        return self.pic if self.pic is not None else jpg()


def run(c):
    return asyncio.run(c)


def test_a_page_it_only_opened_gets_no_boxes_at_all():
    p = Page({'rects': [[1, 1, 9, 9]], 'found': {'$5': 1}, 'w': 200, 'h': 120})
    r = run(em.marked_shot(p, []))
    assert r['found'] == {} and not p.asked and not r['read']


def test_only_what_it_read_is_boxed_and_what_was_not_there_says_so():
    p = Page({'rects': [[1, 1, 9, 9]], 'found': {'12,345': 1}, 'w': 200, 'h': 120})
    r = run(em.marked_shot(p, ['12,345', '999'], read=True))
    assert list(r['found']) == ['12,345'] and r['missing'] == ['999'] and r['read'] is True


def test_it_scrolls_to_a_value_off_screen_then_boxes_it():
    class P(Page):
        n = 0
        async def find_private(self, js):
            self.n += 1
            return {'moved': True, 'rects': []} if self.n == 1 else {'rects': [[1, 1, 9, 9]], 'found': {'777': 1}, 'w': 200, 'h': 120}
    p = P(); r = run(em.marked_shot(p, ['777']))
    assert p.n == 2 and list(r['found']) == ['777']


def test_a_blank_page_is_never_evidence():
    assert em.is_dead(jpg(False)) and not em.is_dead(jpg(True))
    assert run(em.marked_shot(Page(pic=jpg(False)), ['x'])) is None


def test_a_value_is_looked_for_the_ways_a_page_writes_it():
    w = em.value_words(['$12,345', '45%', 7, '1.2M', ''])
    assert {'$12,345', '12,345', '12345', '45%', '1.2m'} <= set(w) and '7' not in w
