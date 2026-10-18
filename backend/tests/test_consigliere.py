import consigliere as cg


def test_the_consigliere_picks_the_plan_that_has_been_working_per_coin_type():
    pos = [{'mint': f'G{i}', 'closedAt': i, 'realPct': 2.0, 'path': [1.0, 3.0], 'thesis': {'germDist': 5.0, 'stopPct': 15}} for i in range(25)]
    after = {f'G{i}|{i}': [10.0, 25.0, 31.0] for i in range(25)}                     # germ coins kept running after Reaper sold
    pos += [{'mint': f'O{i}', 'closedAt': 100 + i, 'realPct': 2.0, 'path': [1.0, 3.0], 'thesis': {'germDist': 40.0, 'stopPct': 15}} for i in range(25)]
    after.update({f'O{i}|{100 + i}': [-5.0, -20.0] for i in range(25)})                # other coins fell after the sale
    pl = cg.plans(pos, after, lambda p: f"{p['mint']}|{int(p['closedAt'])}")
    assert pl['germ']['plan'] == 'patient' and pl['germ']['spike'] == 50.0   # the move ran to +31: the widest spike kept the most
    assert pl['other']['plan'] == 'reaper'
    assert cg.plans(pos[:5], after, lambda p: f"{p['mint']}|{int(p['closedAt'])}")['germ']['plan'] == 'reaper'   # too few to prove
