import fuse_best as fb


def card(style, fit, legs):
    return {'style': style, 'fitness': fit, 'legs': [{'symbol': s, 'weight': w} for s, w in legs]}


def test_best_settings_rank_styles_and_compare_the_top_quarter():
    arena = [card('steady', 90 + i % 3, [('SOL', 60), ('WETH', 40)]) for i in range(10)] + [card('gen-1', 60 + i % 5, [('PEPE', 90), ('X', 5), ('Y', 5)]) for i in range(10)]
    b = fb.best(arena)
    assert b['n'] == 20 and b['styles'][0]['style'] == 'steady' and b['styles'][0]['medFit'] == 91
    assert b['top']['legs'] == 2 and b['top']['majorW'] == 100 and b['rest']['maxW'] > b['top']['maxW']
    assert len(b['cards']) == 3 and b['cards'][0]['style'] == 'steady'
    assert fb.best([]) == {'n': 0, 'styles': [], 'top': None, 'rest': None, 'cards': []}
    assert fb.best([card('lonely', 50, [('A', 1)])])['styles'] == []          # a style needs ≥ 8 cards to rank
