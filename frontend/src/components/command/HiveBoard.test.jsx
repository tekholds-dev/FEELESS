import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { HiveBoard, ColonyGrid } from './HiveBoard';
import { HiveSwitch } from './CatWorkbench';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mockSign = jest.fn(async () => 'SIG');
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({ signMessage: mockSign }) }));

const HIVE = { epoch: 20755, left: 3600 * 5, filed: 3, graded: 2, board: [{ cat: 'h1', name: 'Happy', honey: 3, cells: 2, graded: 2, right: 2 }],
  cells: [{ id: 'c1', name: 'Happy', sym: 'HUSS', call: 'BUY', why: 'volume 3x', honey: 2, move: 25 }, { id: 'c2', name: 'Happy', sym: 'RUG', call: 'AVOID', why: 'pool thin', honey: 1, move: -8 }, { id: 'c3', name: 'Happy', sym: 'NEW', call: 'WATCH', why: 'no edge', honey: null }] };

test('🐝 the Hive board: epoch ring, filed / graded, a honeycomb cell per call (right ones glow), the honey board', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<HiveBoard api={async () => HIVE} />); });
  const comb = el.querySelector('[data-testid="hive-comb"]'); const cells = comb.querySelectorAll('li');
  expect(cells).toHaveLength(3); expect(cells[0].className).toContain('is-buy'); expect(cells[0].className).toContain('is-right'); expect(cells[2].textContent).toContain('⏳');
  expect(el.querySelector('[data-testid="hive-board"]').textContent).toContain('Happy'); expect(el.querySelector('[data-testid="hive-board"]').textContent).toContain('2/2 right');
  expect(el.textContent).toContain('5h 00m');
});

test('🐝 Colonize opens the popout (what it is + the FEECAT stake), confirms at the picked pace, shows a refused stake, and leaves in one click', async () => {
  const sent = []; let refuse = true; mockSign.mockImplementation(async () => 'SIG');
  global.fetch = async (u, o) => { if (!o) return { ok: true, json: async () => ({ agents: [], cadence: 'daily', nextAirdrop: Date.now() / 1000 + 7200, pool: null }) }; const b = JSON.parse(o.body); sent.push(b); if (refuse && b.on && b.op === 'hive') { refuse = false; return { ok: false, status: 402, json: async () => ({ detail: 'Colonizing needs $25 of FEECAT in your wallet — it holds $3.10.' }) }; } return { ok: true, status: 200, json: async () => (b.op === 'share' ? { colonyShare: { on: b.on, pct: b.cap } } : { hive: { on: b.on, every: b.cap } }) }; };
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<HiveSwitch cat={{ id: 'h1', name: 'Kit', hive: { on: false, every: 300 } }} />); });
  await act(async () => { el.querySelector('[data-testid="hive-toggle"]').click(); });
  expect(sent).toHaveLength(0); const pop = document.body.querySelector('[data-testid="colonize-pop"]');
  expect(pop.textContent).toContain('$25 of FEECAT'); expect(pop.textContent).toContain('never pooled'); expect(pop.textContent).toContain('Colonize Kit');
expect(document.body.querySelector('[data-testid="colony-opp-stake"]').textContent).toContain('NOT OPEN YET'); expect(document.body.querySelector('[data-testid="colony-share-sign"]')).not.toBeNull();
  await act(async () => { document.body.querySelector('[data-testid="colony-share-20"]').click(); });
  await act(async () => { document.body.querySelector('[data-testid="colony-share-sign"]').click(); });   // 🤝 opportunity 2: one wallet signature, no transaction
  expect(mockSign.mock.calls.at(-1)[0]).toMatch(/^FEELESS colony share\nagent:h1\npct:20\nts:\d+$/); expect(sent.at(-1)).toMatchObject({ op: 'share', on: true, cap: 20, sig: 'SIG' }); sent.length = 0; refuse = true;
  await act(async () => { document.body.querySelector('[data-testid="colonize-pace-900"]').click(); });
  await act(async () => { document.body.querySelector('[data-testid="colonize-go"]').click(); });
  expect(sent.at(-1)).toMatchObject({ op: 'hive', on: true, cap: 900 }); expect(document.body.querySelector('[data-testid="colonize-err"]').textContent).toContain('holds $3.10');
  await act(async () => { document.body.querySelector('[data-testid="colonize-go"]').click(); });
  expect(document.body.querySelector('[data-testid="colonize-pop"]')).toBeNull(); expect(el.querySelector('[data-testid="hive-toggle"]').textContent).toContain('COLONIZED');
  const sel = el.querySelector('[data-testid="hive-pace"]');
  await act(async () => { sel.value = '3600'; sel.dispatchEvent(new Event('change', { bubbles: true })); });
  expect(sent.at(-1)).toMatchObject({ op: 'hive', on: true, cap: 3600 });
  await act(async () => { el.querySelector('[data-testid="hive-toggle"]').click(); });
  expect(sent.at(-1)).toMatchObject({ op: 'hive', on: false });
});

test('🐝 the Colony / My agents cells: two windows (a real screen, its last page, frozen, idle) with the agent between, honey, your own buttons', async () => {
  const asked = []; const agents = [{ id: 'g1', name: 'Happy', kind: 'general', brains: ['gpt-x', 'haiku'], status: 'working', honey: 3, right: 2, graded: 3, colonized: true,
    windows: [{ i: 0, model: 'gpt-x', status: 'working', host: 'pump.fun', screen: true }, { i: 1, model: 'haiku', status: 'human', frozen: true }], last: { call: 'BUY', sym: 'HUSS', honey: 2, why: 'vol' }, carrying: { text: 'validator', at: 5 } },
    { id: 't1', name: 'Fee', kind: 'trading', brains: ['n/a'], status: 'idle', honey: 0, right: 0, graded: 0, windows: [{ i: 0, status: 'done', screen: true, last: true }], last: null }];
  const api = async u => { asked.push(u); return { agents, page: 0, more: false, total: 2, colonized: 1 }; };
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<ColonyGrid api={api} ids="g1,t1" face={a => <i data-testid={`face-${a.id}`} />} extra={a => <button data-testid={`x-${a.id}`}>go</button>} />); });
  expect(asked[0]).toContain('ids=g1%2Ct1'); expect(el.querySelector('[data-testid="colony-mine"]')).not.toBeNull(); expect(el.querySelector('[data-testid="hive"]')).toBeNull();   // mine: no board
  expect(el.querySelector('[data-testid="cl-scr-g1-A"] img').getAttribute('src')).toContain('/api/cats/g1/screen/0?t=');
  expect(el.querySelector('[data-testid="cl-scr-g1-B"]').textContent).toContain('signing in');
  expect(el.querySelector('[data-testid="cl-scr-t1-A"] img').getAttribute('src')).toMatch(/screen\/0$/); expect(el.querySelector('[data-testid="cl-scr-t1-A"]').textContent).toContain('LAST PAGE');
  expect(el.querySelector('[data-testid="cl-scr-t1-A"] [data-testid="cwb-cursor"]').className).toContain('is-rest');   // 🖱 always on, resting before its first move
  expect(el.querySelector('[data-testid="cl-g1"]').textContent).toContain('carrying “validator” to its drawer');
  expect(el.querySelector('[data-testid="face-g1"]')).not.toBeNull(); expect(el.querySelector('[data-testid="x-t1"]')).not.toBeNull(); expect(el.querySelector('[data-testid="cl-g1"]').textContent).toContain('+3');
});
