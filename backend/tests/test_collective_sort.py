import collective_sort as cs


def test_both_minds_must_agree_and_trash_waits_for_the_owner():
    i = cs.vote({}, 'ossy', 'good', 'ok', 1); assert 'status' not in i
    assert cs.vote(i, 'g4', 'good', 'ok', 2)['status'] == 'good'
    assert cs.vote(i, 'g4', 'bad', 'no', 2)['status'] == 'disputed'
    t = cs.vote(cs.vote({}, 'ossy', 'trash', '', 1), 'g4', 'trash', '', 2); assert t['status'] == 'trash_ask'
    assert cs.rule_trash(t, True)['status'] == 'trash' and 'status' not in cs.rule_trash(t, False) and cs.rule_trash(t, False)['by'] == 'owner'


def test_the_owner_always_outranks_the_minds():
    i = cs.owner_set({}, {'status': 'good', 'note': 'keep this'}, 1)
    assert cs.vote(cs.vote(i, 'ossy', 'trash', '', 2), 'g4', 'trash', '', 3)['status'] == 'good'
    assert cs.next_path(['snapshots/a.webp'], {'snapshots/a.webp': i}) is None


def test_owner_input_is_cleaned():
    i = cs.owner_set({}, {'note': 'x' * 5000, 'use': ['pow', 'nope'], 'marks': [{'x': 2, 'y': -1, 'w': .5, 'h': .5, 'label': 'l'}, {'x': 'bad'}], 'status': 'hack'}, 1)
    assert len(i['note']) == cs.MAX_NOTE and i['use'] == ['pow'] and i['marks'] == [{'x': 1.0, 'y': 0.0, 'w': .5, 'h': .5, 'label': 'l'}] and 'status' not in i


def test_only_idle_and_only_evidence():
    assert cs.idle(1, False, 0, 1000) and not cs.idle(1, True, 0, 1000) and not cs.idle(9, False, 0, 1000) and not cs.idle(1, False, 950, 1000)
    paths = ['README.md', 'kits/a.md', 'proofs/x.json', 'snapshots/b.webp', 'snapshots/c.webp']
    assert cs.next_path(paths, {}) == 'snapshots/b.webp'
    assert cs.next_path(paths, {'snapshots/c.webp': {'note': 'look'}}) == 'snapshots/c.webp'
    done = {p: {'votes': {'ossy': {'marks': []}, 'g4': {'marks': []}}} for p in paths}
    assert cs.next_path(paths, done) is None


def test_a_vague_reply_is_no_vote():
    assert cs.parse_vote('sure') is None and cs.parse_vote('{"verdict":"delete it"}') is None
    assert cs.parse_vote('ok {"verdict":"Good","why":"real chart"}') == ('good', 'real chart')


def test_saved_state_survives_and_counts(tmp_path):
    d = cs.load(tmp_path); assert d['on'] is True
    d['items']['a'] = {'status': 'good'}; d['items']['b'] = {'status': 'trash_ask'}; cs.save(tmp_path, d)
    x = cs.load(tmp_path); c = cs.counts(x['items'], 5); assert c['good'] == 1 and c['trash_ask'] == 1 and c['unsorted'] == 3


def test_a_webp_snapshot_becomes_a_jpeg_the_local_models_accept():
    import io
    from PIL import Image
    b = io.BytesIO(); Image.new('RGB', (2000, 1000), 'red').save(b, 'WEBP')
    out = cs.to_jpeg(b.getvalue()); im = Image.open(io.BytesIO(out)); assert im.format == 'JPEG' and im.width == 1024


def test_a_mark_can_be_words_or_a_note_as_well_as_a_box():
    it = cs.owner_set({}, {'marks': [{'text': 'holders 412', 'kind': 'item'}, {'x': .1, 'y': .1, 'w': .2, 'h': .2}, {'text': 'it missed the dev wallet', 'kind': 'missed'}, 'junk']})
    assert [m.get('kind') for m in it['marks']] == ['item', None, 'missed']
    assert 'it missed the dev wallet' in cs.prompt('a/b.json', it, {})


def test_a_folder_rules_its_files_for_the_minds():
    items = {'snapshots/x/': {'status': 'trash', 'note': 'all 404s', 'by': 'owner'}}
    assert cs.folder_of('snapshots/x/a.webp', items)['note'] == 'all 404s' and cs.next_path(['snapshots/x/a.webp'], items) is None
    assert 'all 404s' in cs.prompt('snapshots/x/a.webp', {}, items)
    assert cs.counts(items, 3)['trash'] == 0


def test_his_word_on_many_at_once():
    items = {'a': {'status': 'bad', 'by': 'minds'}}
    assert cs.bulk(items, ['a', 'b'], 'trash') == 2 and items['a']['status'] == 'trash' and items['a']['by'] == 'owner'
    assert cs.bulk(items, ['a'], 'nope') == 0


def test_marks_from_a_mind_are_cleaned_and_joined():
    t = '{"verdict":"good","why":"x","marks":[{"x":0.1,"y":0.1,"w":0.2,"h":0.2,"label":"Cap","why":"read it","grade":80},{"x":2,"y":0,"w":-1,"h":0},{"text":"holders 412","label":"Holders","grade":"60"},"junk"]}'
    m = cs.parse_marks(t); assert [x.get('label') for x in m] == ['Cap', 'Holders'] and m[1]['grade'] == 60
    assert cs.parse_marks('no json') == [] and cs.parse_marks('{"marks":"nope"}') == []
    a = cs.vote({}, 'ossy', 'good', '', marks=[{'x': .1, 'y': .1, 'w': .2, 'h': .2, 'label': 'Cap', 'why': 'a', 'grade': 80}]); b = cs.vote(a, 'g4', 'good', '', marks=[{'x': .11, 'y': .1, 'w': .2, 'h': .2, 'label': 'Cap', 'why': 'b', 'grade': 60}, {'text': 'holders', 'label': 'H', 'grade': 50}])
    rows = cs.proposed(b); assert len(rows) == 2 and rows[0]['by'] == ['ossy', 'g4'] and rows[0]['grade'] == 70


def test_approving_keeps_only_what_he_ticked_and_the_original_is_safe(tmp_path):
    import io
    from PIL import Image
    buf = io.BytesIO(); Image.new('RGB', (200, 100), (5, 5, 5)).save(buf, 'PNG'); raw = buf.getvalue()
    b = cs.vote(cs.vote({}, 'ossy', 'bad', '', marks=[{'x': .1, 'y': .1, 'w': .3, 'h': .3, 'label': 'A', 'grade': 90}]), 'g4', 'bad', '', marks=[{'x': .6, 'y': .6, 'w': .3, 'h': .3, 'label': 'B', 'grade': 10}])
    done = cs.approve(b, {1}); assert [m['label'] for m in done['marks']] == ['B'] and done['status'] == 'good' and done['by'] == 'owner'
    burned = cs.burn(raw, cs.approve(b, None)['marks']); assert burned != raw and Image.open(io.BytesIO(burned)).size == (200, 100)
    assert Image.open(io.BytesIO(burned)).convert('RGB').getpixel((20, 10)) != (5, 5, 5)
    cs.save_marked(tmp_path, 'snapshots/a.png', burned); files = {'snapshots/a.png': raw, 'b.json': b'{}'}; out = cs.with_marked(tmp_path, files)
    assert out['snapshots/a.png'] == burned and files['snapshots/a.png'] == raw and out['b.json'] == b'{}'


def test_grades_and_many_at_once():
    items = {}; assert cs.bulk(items, ['a', 'b'], patch={'grade': 150, 'use': ['pow']}) == 2 and items['a']['grade'] == 100 and items['b']['use'] == ['pow']
    assert 'grade 100' in cs.lessons({'a': {**items['a'], 'status': 'good', 'by': 'owner'}})
    assert cs.bulk(items, ['a']) == 0


def test_a_file_voted_before_marks_gets_read_again_for_its_marks():
    assert cs.next_path(['snapshots/a.webp'], {'snapshots/a.webp': {'votes': {'ossy': {'verdict': 'bad'}, 'g4': {'verdict': 'bad'}}}}) == 'snapshots/a.webp'
    assert cs.next_path(['snapshots/a.webp'], {'snapshots/a.webp': {'votes': {'ossy': {'verdict': 'bad', 'marks': []}, 'g4': {'verdict': 'bad', 'marks': []}}}}) is None


def test_a_mark_snaps_to_its_real_words_and_a_made_up_one_is_dropped():
    boxes = [{'text': 'Price USD $0.008194', 'x': 0.8, 'y': 0.2, 'w': 0.19, 'h': 0.02}, {'text': 'LIQUIDITY', 'x': 0.8, 'y': 0.3, 'w': 0.05, 'h': 0.02}]
    out = cs.snap([{'text': '$0.008194', 'label': 'Price', 'why': 'read', 'grade': 90}, {'read': 'liquidity', 'label': 'Liq', 'x': 0.1, 'y': 0.1, 'w': 0.5, 'h': 0.5}, {'text': 'RSI 62.59', 'label': 'RSI'}, {'text': 'x', 'label': 'too short'}], boxes)
    assert [m['label'] for m in out] == ['Price', 'Liq'] and out[0]['read'] == '$0.008194' and 'text' not in out[0]
    assert 0.85 < out[0]['x'] < 0.92 and abs(out[1]['x'] - 0.796) < 0.01 and out[1]['w'] < 0.07   # the mind's own box is ignored
    assert cs.ocr_lines(boxes) == 'Price USD $0.008194 | LIQUIDITY' and cs.snap(None, boxes) == []


def test_no_text_reader_means_no_boxes_never_a_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(cs, 'OCR_SRC', tmp_path / 'missing.swift')
    assert cs.ocr_boxes(b'x', tmp_path / 'bin') == []


def test_a_vote_with_marks_inside_it_still_counts():
    t = '{"verdict":"good","why":"Complete","marks":[{"text":"$1","label":"Price","why":"clear","grade":95},{"text":"$2","label":"Cap","grade":90}]}'
    assert cs.parse_vote(t) == ('good', 'Complete') and len(cs.parse_marks(t)) == 2
    assert cs.parse_vote('```json\n' + t + '\n```') == ('good', 'Complete')
    assert cs.parse_vote('{"marks":[{"text":"a"}]}') is None
