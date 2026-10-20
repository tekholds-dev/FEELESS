"""Number coercion shared by the pure modules (each used to carry its own copy of `_f`).

nan_safe — float(v); NaN / not a number → d (inf passes)
finite   — float(v); NaN, ±inf / not a number → d
plain    — float(v); not a number → d (NaN and inf pass)
zero     — float(v or 0); not a number → 0.0
"""
import math


def nan_safe(v, d=0.0):
    try:
        x = float(v)
        return x if x == x else d
    except (TypeError, ValueError):
        return d


def finite(v, d=0.0):
    try:
        x = float(v)
        return x if math.isfinite(x) else d
    except (TypeError, ValueError):
        return d


def plain(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def zero(v):
    return plain(v or 0)
