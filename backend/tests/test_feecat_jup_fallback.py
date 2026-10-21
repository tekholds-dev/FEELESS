import asyncio
import feecat_service as fs


class R:
    def __init__(self, j):
        self._j = j

    def json(self):
        return self._j


class Http:
    def __init__(self, audit):
        self.audit = audit

    async def get(self, url, params=None, timeout=None):
        if '/intel/' in url:
            return R({'top10Pct': None})
        if 'jup.ag' in url:
            return R([{'id': 'M1', 'audit': self.audit}])
        return R({})


def test_fee_falls_back_to_jupiters_holder_audit_at_a_smaller_size():
    fs._intel_cache.clear()
    ok, why, conv = asyncio.run(fs._safety(Http({'topHoldersPercentage': 18, 'devBalancePercentage': 1, 'mintAuthorityDisabled': True, 'freezeAuthorityDisabled': True}), {'baseToken': {'address': 'M1'}}))
    assert ok and conv <= 0.6 and 'top10 18%' in why
    fs._intel_cache.clear()
    ok, why, _ = asyncio.run(fs._safety(Http({'topHoldersPercentage': 18, 'mintAuthorityDisabled': False}), {'baseToken': {'address': 'M1'}}))
    assert not ok and 'authority' in why
