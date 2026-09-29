"""FEELESS ecosystem coins. Mints are configuration (env overrides, else the launch defaults),
so resolving them never needs a network call."""
import os

DEFAULT_MINTS = {
    'FEE': '49MmWE8sgNjuw342Eu7tB9thsVFtvTfKigUw9KSppump',
    'FEECAT': 'AsX2abSJ2HqPqRxUbeYXE5R5ksrmUDz6BMGpg9mDpump',
    'RFEE': '2vZjg2w58k4urtdNWPnNHizuSxesLCozQ5Pq9xxqNray',
}


def ecosystem_mints() -> dict:
    """{'fee': mint, 'rfee': mint, 'feecat': mint} — same ids as /api/market/assets."""
    return {name.lower(): os.getenv(f'{name}_MINT', mint) for name, mint in DEFAULT_MINTS.items()}
