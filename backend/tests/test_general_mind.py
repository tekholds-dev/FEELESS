"""The general mind rides pages, content and plans with the real record, and never touches a trading mindset."""
import asyncio

import prompt_studio as ps


CAT = {'psFolders': [{'graded': 'right'}, {'graded': 'wrong'}, {'graded': 'wrong'}, {}], 'popFolders': [{'roePct': 4}, {'roePct': -2}], 'pobFolders': [{'won': True}]}


def test_the_record_comes_from_the_real_folders():
    r = {x['kind']: x for x in ps.general_record(CAT)}
    assert (r['PoS']['filed'], r['PoS']['right'], r['PoS']['wrong']) == (4, 1, 2) and (r['PoP']['right'], r['PoP']['wrong']) == (1, 1) and r['PoB']['right'] == 1 and r['PoW']['filed'] == 0


def test_the_line_names_the_weakest_only_once_enough_is_judged():
    assert 'weakest work is PoS' in ps.general_line(ps.general_record(CAT))
    assert 'weakest' not in ps.general_line(ps.general_record({'psFolders': [{'graded': 'wrong'}]}))
    assert ps.general_line(ps.general_record({})) == ''


def test_the_block_says_never_invent_and_an_owner_edit_wins():
    b = ps.general_block(None, []); assert 'never invent' in b and b.endswith('\n\n')
    assert ps.general_block('Read twice.', ps.general_record(CAT)).startswith('Read twice. Your real record')
    assert len(ps.general_block('x' * 5000, [])) <= ps.MAX_CHARS['fee'] + 2


def test_it_reaches_a_page_call_and_saving_it_leaves_the_trading_mindset_alone(monkeypatch):
    import feecat_service as fs
    seen = {}

    async def fake(cat, model, msgs, own, tools, tokens):
        seen['sys'] = msgs[0]['content']; return 'ok', 0.0, 'x'
    monkeypatch.setattr(fs, '_think', fake); monkeypatch.setattr(fs._ck, 'key_for', lambda *a, **k: None)
    asyncio.run(fs._ws_ask({}, 'local/x', 'BUILD IT', 'hi', 10))
    assert 'never invent' in seen['sys'] and seen['sys'].endswith('BUILD IT')
    cat = {'studio': {'set': 'elite', 'text': 'trade well', 'at': 1, 'by': 'o'}}
    out = fs.studio_set(cat, {'general': 'Read twice.'}, 'o', 10.0)
    assert cat['studio']['text'] == 'trade well' and cat['studio']['general'] == 'Read twice.' and out['general']['edited'] is True
    fs.studio_set(cat, {'general': ''}, 'o', 11.0); assert cat['studio']['general'] is None and cat['studio']['text'] == 'trade well'
    cat['studio']['general'] = 'Keep me'; fs.studio_set(cat, {'revert': True}, 'o', 12.0); assert cat['studio']['general'] == 'Keep me' and not cat['studio'].get('text')
