"""Helpers for tests that need the kernel in a known state (the service reads `trench_kernel.kernel.KERNEL`)."""
import trench_kernel.kernel as tk


def row(m='M', age=0.05, mc=40_000, d5=6.0, buy=62, liq=20_000, v5=8_000, pace=2.0, px=1.0, **k):
    """A sensed row (trench_kernel.senses.sense shape). The defaults read HOT EARLY MOVE → READY."""
    return {'mint': m, 'symbol': m, 'pair': 'P' + m, 'px': px, 'nums': {'v5': v5, 'pace': pace, 'liq': liq, 'd5': d5, 'buy': buy},
            'vitals': {'mcap': mc, 'liq': liq, 'ageH': age, 'vol1h': 20_000, 'txns1h': 300}, **k}


def seed(monkeypatch, rows, now=100.0, ctx=None):
    """A fresh kernel judged on `rows`, installed as the process's KERNEL for this test. → the kernel"""
    k = tk.Kernel()
    k.run(rows, now, ctx or {})
    monkeypatch.setattr(tk, 'KERNEL', k)
    return k
