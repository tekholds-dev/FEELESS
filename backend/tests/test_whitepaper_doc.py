"""📄 The whitepaper says what is true today (2026-11-14): agents start no model work by themselves, COMP has its chapter, the roadmap names them."""
import whitepaper


def test_the_whitepaper_is_current():
    d = whitepaper.document(); by = {c['title']: c['text'] for c in d['chapters']}
    assert d['version'] == '1.3' and len(d['chapters']) == 35
    assert 'never starts model work by itself' in by['Agents and Two Minds']
    assert 'COMP does not trade, sign or move funds' in by["COMP, FEELESS's Own Model"]
    assert 'COMP' in by['Roadmap'] and 'The Collective' in by['Roadmap'] and 'Q2 2027' in by['Roadmap']
