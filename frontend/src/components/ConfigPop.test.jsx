import { seatHealth } from './ArenaPrime';

test('seat health names the filter that empties the last seat and offers the looser value', () => {
  const c = { legs: [{ symbol: 'A' }, { symbol: 'B' }, { symbol: 'C' }], pipeline: { steps: [['safe', 77], ['alive', 4], ['your vital filter (grade · organic · crew)', 0], ['not on the card', 0]] } };
  const h = seatHealth(c, { coins: 4, vitalMin: 65, organicMin: 30 });
  expect(h.short).toContain('1 empty seat'); expect(h.short).toContain('your vital filter'); expect(h.short).toContain('last 4 coins');
  expect(h.why).toContain('B+'); expect(h.why).toContain('30%'); expect(h.fix.patch).toEqual({ vitalMin: 50, organicMin: 10 });
  expect(seatHealth({ ...c, legs: [...c.legs, { symbol: 'D' }] }, { coins: 4 })).toBeNull();   // full card: nothing to say
  expect(seatHealth({ legs: [], pipeline: { steps: [['safe', 3], ['not on the card', 0]] } }, { coins: 2 }).fix).toBeNull();   // not the owner's filter: no button
});

test('Edit Fuse is a pop-out: launcher with live chips, rail of sections, seat banner with one-tap fix, Esc closes', async () => {
  const React = require('react'); const { act } = React; const { createRoot } = require('react-dom/client');
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({}) }));
  const { CardEditor } = require('./ArenaPrime');
  const call = jest.fn(async () => ({}));
  const c = { tpl: 'degen', label: '🔥 Prime Blaze', real: true, legs: [{ symbol: 'A' }, { symbol: 'B' }, { symbol: 'C' }], pipeline: { steps: [['safe', 77], ['alive', 4], ['your vital filter (grade · organic · crew)', 0]] } };
  const cfg = { rotateHours: 0.08, coins: 4, sl: 15, rideAt: 30, vitalMin: 65, organicMin: 30, cycles: {} };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CardEditor c={c} cfg={cfg} real call={call} keeper={{}} />); });
  const q = id => document.querySelector(`[data-testid="${id}"]`);
  expect(q('ce-pop')).toBeNull(); expect(q('ce-open').textContent).toContain('5m rounds'); expect(q('ce-open').textContent).toContain('stop −15%'); expect(q('ce-seat-warn')).not.toBeNull();
  await act(async () => { q('ce-open').click(); });
  expect(q('ce-pop')).not.toBeNull(); expect(q('ce-pane-main')).not.toBeNull(); expect(q('ce-tab-wallet')).not.toBeNull();
  await act(async () => { q('ce-tab-exits').click(); }); expect(q('ce-pane-exits')).not.toBeNull();
  await act(async () => { q('ce-seat-fix').click(); });
  expect(call).toHaveBeenCalledWith('/admin/arena/prime', expect.objectContaining({ body: JSON.stringify({ realCfg: { vitalMin: 50, organicMin: 10 } }) }));
  await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); }); expect(q('ce-pop')).toBeNull();
  await act(async () => { root.unmount(); });
});
