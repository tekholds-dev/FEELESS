"""💬 Slice 34 streaming replies: the answer shows in the chat as the model writes it (network faked)."""
import asyncio
import json

import httpx
import cat_agent as ca


def test_partial_answer_reads_the_answer_string_as_far_as_it_got():
    assert ca.partial_answer('{"fast": "Hel') == 'Hel'
    assert ca.partial_answer('{"fast": "line\\none \\"q\\" \\u00e9') == 'line\none "q" é'
    assert ca.partial_answer('{"fast": "done", "a": "x"}') == 'done'
    assert ca.partial_answer('{"a": "half", "b": "') == ''                     # a plan with no answer yet shows nothing
    assert ca.partial_answer('{"answer": "merged so') == 'merged so'
    assert ca.partial_answer('Plain words being written') == 'Plain words being written'
    assert ca.partial_answer('Plain plan text', plain=False) == ''             # the plan call's plain text is its plan, never the answer
    assert ca.partial_answer('{"fast": "ab\\') == 'ab'                         # a cut escape waits for the next chunk


def test_or_stream_hands_every_chunk_over_and_keeps_the_bill(monkeypatch):
    import fc_core
    chunks = [{'id': 'gen-1', 'model': 'm/a', 'choices': [{'delta': {'content': '{"fast": "Hi'}}]},
              {'choices': [{'delta': {'content': ' there"}'}, 'finish_reason': 'stop'}]},
              {'choices': [{'delta': {}}], 'usage': {'total_tokens': 42, 'cost': 0.0012}}]
    body = ': OPENROUTER PROCESSING\n\n' + ''.join(f'data: {json.dumps(c)}\n\n' for c in chunks) + 'data: [DONE]\n\n'
    sent = {}

    def handler(req):
        sent.update(json.loads(req.content))
        return httpx.Response(200, text=body, headers={'content-type': 'text/event-stream'})
    seen = []

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as h:
            return await fc_core._or_stream(h, {}, {'model': 'm/a', 'messages': []}, seen.append)
    r = asyncio.run(go())
    assert sent['stream'] is True and sent['usage'] == {'include': True}
    assert seen == ['{"fast": "Hi', '{"fast": "Hi there"}']
    d = r.json()
    assert r.status_code == 200 and d['choices'][0]['message']['content'] == '{"fast": "Hi there"}' and d['choices'][0]['finish_reason'] == 'stop'
    assert d['usage']['cost'] == 0.0012 and d['id'] == 'gen-1'                # the provider's own cost: billing + receipts unchanged


def test_a_refused_stream_bills_nothing():
    import fc_core

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(402, text='{"error":"credit"}'))) as h:
            return await fc_core._or_stream(h, {}, {'model': 'm/a', 'messages': []}, lambda s: None)
    r = asyncio.run(go())
    assert r.status_code == 402 and r.json() == {}


def test_the_plan_streams_its_fast_answer_into_the_task_and_the_view_shows_it_only_while_live():
    t = ca.new_task('s1', 'what is 2+2', ['m/a'], 1.0)
    shown = []

    async def ask(model, messages):
        on = ca.STREAM.get()
        assert on is not None                                                  # the plan call streams
        on('{"fast": "Fo'); shown.append(t.get('partial'))
        on('{"fast": "Four.", "a": "", "b": ""}'); shown.append(t.get('partial'))
        return '{"fast": "Four.", "a": "", "b": ""}', 0.001
    asyncio.run(ca.run(t, ask, [None], None, ['A']))
    assert shown == ['Fo', 'Four.'] and t['answer'] == 'Four.' and t['status'] == 'done'
    assert ca.STREAM.get() is None                                             # reset after the call
