import glob
import re


def test_every_transaction_reader_accepts_version_1_transactions():
    # 2026-10-15: Solana version-1 transactions made every getTransaction with maxSupportedTransactionVersion 0 fail (-32015) — the trade
    # tape read "provider unavailable" on every coin (blinding the flow vital, the rug radar and the pool-drain exit). 1 also reads v0 / legacy.
    bad = []
    for f in glob.glob('*.py') + glob.glob('../scripts/*.py'):
        if re.search(r"maxSupportedTransactionVersion['\"]?\s*:\s*0\b", open(f).read()):
            bad.append(f)
    assert bad == []
