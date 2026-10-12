"""🧬 ONE lifecycle record for all ten roles. The four desks (agents.py state) and the office desks (office state) used to keep their own
generation books; this is the single representation every caller reads (built on generations.lifecycle)."""
import generations as _gen

STATUSES = ('ACTIVE', 'PROBATION', 'SHADOW', 'RETIRED', 'BENCHED')


def generations(four, office, now, desk_stats=None, shadows=None):
    """→ [AgentGeneration] — role · generation · bornAt · status · decisions · winsAttributed · lossesAttributed · netImpact · lessons ·
    lineage · lastEvaluation — exactly one ACTIVE (or BENCHED) per role."""
    lc = _gen.lifecycle(four, office, now, shadows)
    ds = desk_stats or {}
    lessons = dict((four or {}).get('lessons') or {})
    out = []
    for role, v in lc.items():
        a = v['active']
        d = ds.get(role) or {}
        out.append({'role': role, 'generation': a['gen'], 'bornAt': a.get('since'), 'status': a['status'],
                    'decisions': d.get('decisions'), 'winsAttributed': d.get('winResp'), 'lossesAttributed': d.get('lossResp'), 'netImpact': d.get('medNet'),
                    'lessons': (lessons.get(role) or {}).get('words') or [p.get('changed') for p in v['past'][:1] if p.get('changed')],
                    'lineage': v['past'], 'lastEvaluation': now})
    return out
