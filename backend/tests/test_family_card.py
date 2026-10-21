import pytest
import crews as cr

A, B = 'A' * 40, 'B' * 40


def test_only_the_don_styles_the_card_and_only_listed_values_stick():
    st = {}
    c = cr.create(st, A, 'Sicario', 'SIC', 0)
    cr.invite(st, A, B, 1); cr.accept(st, B, c['id'], 2)
    with pytest.raises(ValueError):
        cr.set_card(st, B, {'style': 'gold'}, 3)
    cr.set_card(st, A, {'style': 'blood', 'fx': 'lightning', 'line': 'Famiglia \x07prima di tutto — and the trenches after that one'}, 4)
    v = cr.card_view(st['crews'][c['id']])
    assert v['style'] == 'blood' and v['fx'] == 'lightning' and len(v['line']) <= cr.CARD_LINE_MAX and '\x07' not in v['line']
    cr.set_card(st, A, {'style': 'hacker', 'fx': 'nukes'}, 5)
    assert cr.card_view(st['crews'][c['id']])['style'] == 'noir' and cr.card_view(st['crews'][c['id']])['fx'] == 'none'
    row = cr.board(st, {}, 10)[0]
    assert row['card']['style'] == 'noir'
