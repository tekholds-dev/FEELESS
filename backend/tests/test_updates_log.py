import updates_log as ul


def _log(*commits):
    return ''.join(f"{ul.SEP_C}{sha}{ul.SEP_F}{at}{ul.SEP_F}{subj}\n\n" + '\n'.join(files) + '\n' for sha, at, subj, files in commits)


def test_rows_split_by_part_and_type_and_drop_private_bits():
    text = _log(('abc12345ff', '2026-10-27', 'feat(perps): 🧭 swipe provider rail · Crypto.com full market list · the HQ key table', ['frontend/src/components/PerpsDash.jsx', 'backend/brokers.py']),
                ('def67890aa', '2026-10-26', 'fix(duo): 📱 trench chart fits phones', ['frontend/src/styles/duo.css']),
                ('0000aaaa11', '2026-10-26', 'docs: handoff', ['docs/HANDOFF.md']),
                ('1111bbbb22', '2026-10-25', 'feat: set the API key in .env', ['backend/x.py']),
                ('2222cccc33', '2026-10-25', 'fix(api): pays 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU', ['backend/x.py']))
    rows = ul.parse(text)
    assert [r['sha'] for r in rows] == ['abc12345', 'def67890']                       # docs skipped; all-private subjects dropped whole
    assert rows[0]['type'] == 'new' and rows[0]['parts'] == ['site', 'backend'] and rows[0]['area'] == 'perps'
    assert rows[0]['items'] == ['🧭 swipe provider rail', 'Crypto.com full market list']   # "the HQ key table" never leaves the server
    assert rows[1]['type'] == 'fix' and rows[1]['parts'] == ['site', 'mobile']
    assert ul.counts(rows) == {'site': 2, 'backend': 1, 'mobile': 1, 'new': 1, 'fix': 1}
    assert ul.parse('') == [] and ul.parse('garbage') == []
    assert ul._items('tank levels (NEW · GERM · DESK) · whitepaper cards') == ['tank levels (NEW · GERM · DESK)', 'whitepaper cards']   # brackets stay whole
