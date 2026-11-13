"""COL-10: Claude-made commits file themselves into the stash, tagged by model only. Fake git log text; a temp stash."""
import claude_builds as cb
import collective_stash as cs

S = 'a' * 40
T = 'b' * 40


def log(*recs):
    return ''.join(cb.SEP + cb.FIELD.join(r) for r in recs)


def test_only_claude_commits_file_tagged_by_model_and_never_twice(tmp_path):
    text = log((S, '1794500000', 'feat: COL-11 Evolution Lab', 'held-out gate\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>', 'Claude Opus 5.5 <noreply@anthropic.com>'),
               (T, '1794500100', 'fix: chart', 'tight', 'Claude Sonnet 5.5 <noreply@anthropic.com>'),
               ('c' * 40, '1794500200', 'hand edit', '', ''))
    recs = cb.parse_log(text, {S: ['backend/evolution_lab.py']})
    assert [(r['model'], r['kind']) for r in recs] == [('claude-opus-5.5', 'feat'), ('claude-sonnet-5.5', 'fix')]
    assert recs[0]['method'] == 'held-out gate' and recs[0]['files'] == ['backend/evolution_lab.py']   # the trailer is not the method
    assert [cs.put(tmp_path, **cb.stash_args(r)) for r in recs] == [True, True]
    assert [cs.put(tmp_path, **cb.stash_args(r)) for r in recs] == [False, False]
    st = cs.stats(tmp_path); assert st['categories'] == {'Builds': 2} and st['agents'] == 2


def test_who_reads_the_model_and_nothing_else():
    assert cb.who('Claude Fable 5.2 <noreply@anthropic.com>') == 'claude-fable-5.2'
    assert cb.who('Someone <x@y.z>') == '' and cb.who('') == ''
