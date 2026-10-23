import { hotRow, hotRows, readHot, _setHotFetch, GUARD } from './hotPools';
import { withSlip } from './lpBuilder';

const SOL = 'So11111111111111111111111111111111111111112'; const NOW = 1_800_000_000_000;
const row = (o = {}) => ({ address: 'P1', is_blacklisted: false, created_at: NOW - 40 * 3.6e6, tvl: 115000,
  token_x: { address: 'C1', symbol: 'PANGEA', holders: 1962, freeze_authority_disabled: true, market_cap: 1.5e6 }, token_y: { address: SOL, symbol: 'SOL' },
  volume: { '24h': 1.1e6 }, fees: { '24h': 9100, '1h': 120 }, protocol_fees: { '24h': 2230 }, ...o });

test('🔥 a hot pool: what LPs KEPT of 24h fees ÷ depth (protocol cut out), ranked best first', () => {
  const r = hotRow(row(), NOW); expect(r).toMatchObject({ id: 'P1', sym: 'PANGEA-SOL', coin: 'C1', coinSym: 'PANGEA' }); expect(r.feeDay).toBeCloseTo(6870 / 115000, 6);
  expect(r.apy).toBeCloseTo((6870 / 115000) * 36500, 3); expect(10 * r.feeDay).toBeGreaterThan(0.5);   // $10 there ≈ $0.60 a day
  const rows = hotRows({ data: [row(), row({ address: 'P2', fees: { '24h': 30000 }, protocol_fees: { '24h': 6000 } })] }, NOW); expect(rows.map(x => x.id)).toEqual(['P2', 'P1']);
});

test('🛡 the guards on a new buy door: blacklisted · not SOL · thin · quiet · too young · freezable · few holders → never shown', () => {
  expect(hotRow(row({ is_blacklisted: true }), NOW)).toBeNull();
  expect(hotRow(row({ token_y: { address: 'USDC1', symbol: 'USDC' } }), NOW)).toBeNull();
  expect(hotRow(row({ tvl: GUARD.tvl - 1 }), NOW)).toBeNull(); expect(hotRow(row({ volume: { '24h': GUARD.vol - 1 } }), NOW)).toBeNull();
  expect(hotRow(row({ created_at: NOW - 2 * 3.6e6 }), NOW)).toBeNull();
  expect(hotRow(row({ token_x: { ...row().token_x, freeze_authority_disabled: false } }), NOW)).toBeNull();
  expect(hotRow(row({ token_x: { ...row().token_x, holders: 120 } }), NOW)).toBeNull();
  expect(hotRow(row({ fees: { '24h': 100 }, protocol_fees: { '24h': 100 } }), NOW)).toBeNull();   // no fees kept → nothing to hunt
});

test('📡 one shared read a minute; tests never hit the network; a failed read clears for the next try', async () => {
  const f = jest.fn(() => Promise.resolve({ data: [row({ created_at: Date.now() - 40 * 3.6e6 })] })); _setHotFetch(f);
  const a = await readHot(); const b = await readHot(); expect(f).toHaveBeenCalledTimes(1); expect(a).toBe(b); expect(a[0].id).toBe('P1');
  _setHotFetch(() => Promise.reject(new Error('down'))); expect(await readHot()).toEqual([]);
});

test('🔌 the join keeps 1 % head-room on the coin side, in exact base units', () => {
  expect(withSlip('955815822275')).toBe(965373980497n); expect(withSlip(10000, 50)).toBe(10050n);
});
