"""👤 owner study + 🗄 AI memory + 🌐 search before answering (owner, 2026-10-15)."""
import ai_memory as aim
import ai_chat as aic
import owner_study as ost


def test_the_study_reports_numbers_and_suggests_only_with_evidence():
    moves = {'pick': {'label': '🎯 pick', 'n': 10, 'good': 7, 'bad': 3, 'medPct': 12}, 'cut': {'label': '✂ cut', 'n': 8, 'good': 2, 'bad': 6, 'medPct': 9},
             'skim': {'label': '💰 profit take', 'n': 2, 'good': 2, 'bad': 0, 'medPct': -5}}
    seats = {'n': 7, 'cmp': {'n': 7, 'you': 14.0, 'agents': 4.0, 'youBetter': 5}}
    r = ost.report(moves, seats, {'yours': {'n': 6, 'med': 3.0}, 'agents': {'n': 40, 'med': -2.0}}, ['age 1–6h'])
    assert r['score'] == 55 and any('🎯 pick: 10 graded · 70% good' in f for f in r['findings'])
    assert not any('profit take' in f for f in r['findings'])                                   # 2 moves = not enough to say anything
    keys = [s['agent'] for s in r['suggestions']]
    assert keys == ['sherlock', 'devil', 'reaper', 'reaper']                                     # good picks · weak cuts · seats beat Reaper · lines beat theirs
    assert all(aic.check(s)[0] for s in r['suggestions'])                                       # every suggestion is a valid Brain proposal (owner ✅ / ✕)
    assert ost.report({}, {}, {}, [])['suggestions'] == []


def test_memory_is_filed_capped_and_recalled_by_fit():
    m = {}
    for i in range(150):
        m = aim.file(m, 'coins', f'c{i}', f'$C{i} READY rank {i}', 1000 + i)
    assert len(m['coins']) == 120                                                               # capped: oldest out
    m = aim.file(m, 'lessons', 'n1', 'copycat narratives are in and out within minutes', 2000)
    m = aim.file(m, 'lessons', 'n1', 'copycat narratives: in and out within minutes', 2001)    # same key replaces itself
    m = aim.file(m, 'owner', 's0', 'your picks are 70% good', 2001)
    assert len(m['lessons']) == 1
    got = aim.recall(aim.seed_site(m, 2002), 'should I chase this copycat narrative?', 5)
    assert got[0].startswith('[you]') and any('copycat' in g for g in got)
    assert aim.prune(m, 2001 + 86400 * 2)['coins'] == []                                         # coins keep a day only
    assert aim.size(m)['site'] == 0 and aim.size(aim.seed_site(m, 1))['site'] == len(aim.SITE)


def test_the_brain_searches_before_any_real_question():
    assert aic.should_search('what is pump.fun doing with creator fees now')
    assert not aic.should_search('yo') and not aic.should_search('gm fam') and not aic.should_search('hi')
