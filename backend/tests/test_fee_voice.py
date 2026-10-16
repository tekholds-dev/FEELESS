import fee_voice as fv


def test_two_prominent_sources_one_per_domain_no_junk():
    rows = [{'url': 'https://randomblog.xyz/a'}, {'url': 'https://www.pinterest.com/x'}, {'url': 'https://www.reuters.com/a'},
            {'url': 'https://www.reuters.com/b'}, {'url': 'https://coindesk.com/c'}, {'url': 'https://other.net/d'}]
    assert [r['url'] for r in fv.pick_sources(rows)] == ['https://www.reuters.com/a', 'https://coindesk.com/c']
    assert [r['url'] for r in fv.pick_sources([{'url': 'https://a.net/1'}, {'url': 'https://b.net/2'}])] == ['https://a.net/1', 'https://b.net/2']


def test_living_block_carries_the_owners_record_and_memory_and_is_empty_without_it():
    t = fv.living({'owner': [{'text': 'hold picks 30 min'}], 'lessons': ['fake candles = skip']}, {'findings': ['🎯 pick: 231 graded · 18% good']}, ['avoid phase:LATE FOMO'], now=0)
    assert 'owner\'s record: 🎯 pick' in t and 'owner says: hold picks' in t and 'lesson: fake candles' in t and 'desk rule: avoid' in t
    assert fv.living({}, {}, [], now=0) == ''
    assert 'FEELESS' in fv.PERSONA and '2 most solid sources' in fv.PERSONA
