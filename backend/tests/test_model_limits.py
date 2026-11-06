"""Owner 2026-11-06: test the LM Studio models' limits with all proofs, for free. Code grades them; a model never does."""
import asyncio

import model_limits as ml
import prompt_studio as ps


def _exam(k):
    return next(e for e in ml.EXAMS if e['k'] == k)


def test_right_answers_pass_and_wrong_ones_fail_with_a_reason():
    assert _exam('pow')['grade']('{"pick":"MIRA","why":"cap 22K, buyers 58"}')[0]
    assert not _exam('pow')['grade']('{"pick":"ZEN","why":"cheap"}')[0] and not _exam('pow')['grade']('{"pick":"MIRA","why":"looks good"}')[0]
    assert _exam('pop')['grade']('{"call":"pass"}')[0] and not _exam('pop')['grade']('{"call":"long"}')[0]
    assert _exam('pob')['grade']('{"side":"no","edge":14}')[0] and _exam('pob')['grade']('{"side":"No","edge":"-14%"}')[0] and not _exam('pob')['grade']('{"side":"yes","edge":14}')[0] and not _exam('pob')['grade']('{"side":"no","edge":10}')[0]
    assert _exam('poc')['grade']('{"narrative":"Robots"}')[0] and not _exam('poc')['grade']('{"narrative":"Cats"}')[0]
    page = '<!doctype html><html><head><style>body{background:#000}</style></head><body><button>Go</button><span id=count>0</span><script>let count=0</script></body></html>'
    assert _exam('pos')['grade'](page)[0] and not _exam('pos')['grade']('<div>half a pa')[0] and not _exam('pos')['grade'](page.replace('<script>', '<script src="https://x.y/z.js">'))[0]
    assert not _exam('pow')['grade']('no json here')[0]


def test_a_think_block_is_not_the_answer_and_every_exam_but_the_page_has_a_trap():
    assert _exam('poc')['grade']('<think>{"narrative":"Cats"}</think>{"narrative":"Robots"}')[0]
    assert all(ml.TRAP in e['q'] for e in ml.EXAMS if e['k'] != 'pos') and {e['k'] for e in ml.EXAMS} == {'pow', 'pop', 'pob', 'poc', 'pos'}


class Fake:
    def __init__(self, replies):
        self.replies = list(replies); self.bodies = []

    async def post(self, url, headers=None, json=None, timeout=None):
        self.bodies.append(json); x = self.replies.pop(0)
        if isinstance(x, Exception):
            raise x

        class R:
            status_code = 200

            @staticmethod
            def json():
                return {'choices': [{'message': {'content': x}}], 'usage': {'completion_tokens': 10}}
        return R()


def test_a_run_scores_and_a_dead_model_fails_instead_of_raising():
    f = Fake(['{"pick":"MIRA","why":"58"}', '{"call":"pass"}', '{"side":"no","edge":14}', '{"narrative":"Robots"}', OSError('gone')])
    got = asyncio.run(ml.run_one(f, 'http://x/v1/', 'k', 'm', 'BE SHARP'))
    assert got['score'] == 80 and [r['ok'] for r in got['rows']] == [True, True, True, True, False] and 'No answer' in got['rows'][-1]['why']
    assert f.bodies[0]['messages'][0] == {'role': 'system', 'content': 'BE SHARP'} and f.bodies[0]['reasoning_effort'] == 'none'


def test_supreme_is_offered_and_fits():
    rows = ps.sets('lan', ps.stats([]), [], None)
    top = next(r for r in rows if r['set'] == 'supreme')
    assert len(top['text']) <= ps.MAX_CHARS['lan'] and 'ATTACK' in top['text']
