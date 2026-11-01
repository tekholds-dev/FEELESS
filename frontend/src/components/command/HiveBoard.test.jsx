import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ColonyFlow, ColonyGrid, ColonyManual, PowEngine } from './HiveBoard';
import { HiveSwitch } from './CatWorkbench';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mockSign = jest.fn(async () => 'SIG');
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({ signMessage: mockSign }) }));

const HIVE = { epoch: 20755, left: 3600 * 5, filed: 3, graded: 2, board: [{ cat: 'h1', name: 'Happy', honey: 3, cells: 2, graded: 2, right: 2 }],
  cells: [{ id: 'c1', name: 'Happy', sym: 'HUSS', call: 'BUY', why: 'volume 3x', honey: 2, move: 25 }, { id: 'c2', name: 'Happy', sym: 'RUG', call: 'AVOID', why: 'pool thin', honey: 1, move: -8 }, { id: 'c3', name: 'Happy', sym: 'NEW', call: 'WATCH', why: 'no edge', honey: null }] };

test('💸 colony --flow: real money boxes (PoW in → P/L → shares → pot → airdrop), packets only where money moved, and the live ledger with every tx', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  const FLOW = { pow: { folders: 8, trades: 3, inSol: 0.018, won: 1 }, pnlSol: -0.0021, shares: { owedSol: 0, count: 0, sharing: 0 }, pot: { address: '7poJPeupTfM1vd8fKWU694WaQ6sie52mbPTByJCRGpaQ', sol: 0.05 },
    epoch: { n: 1, left: 3600, honey: 3, agents: 2 }, airdrop: { next: Date.now() / 1000 + 7200, cadence: 'daily', paidSol: 0 }, agents: 5, colonized: 2,
    ledger: [{ at: 1793521620, kind: 'sell', agent: 'Happy', sym: 'SIS', sol: 0.0051, sig: '5DMYabcd', memo: 'PoW sell' }, { at: 1793521000, kind: 'buy', agent: 'Happy', sym: 'SIS', sol: 0.006, sig: '3xYzefgh', memo: 'PoW buy' }] };
  await act(async () => { createRoot(el).render(<ColonyFlow api={async u => (u.includes('/flow') ? FLOW : HIVE)} meta={{ colonized: 2, total: 5 }} />); });
  const t = el.querySelector('[data-testid="colony-flow"]').textContent;
  expect(t).toContain('colony --flow'); expect(t).toContain('0.0180 SOL'); expect(t).toContain('−0.0021 SOL'); expect(t).toContain('0.0500 SOL'); expect(t).toContain('+3 honey');
  expect(el.querySelector('.cmf-box.is-pnl b').className).toContain('is-dn'); expect(el.querySelectorAll('.cmf-pipe.is-on').length).toBeGreaterThan(0);
  expect(el.querySelector('.cmf-box.is-share').className).not.toContain('is-hot');   // nothing shared → no packets into the pot
  const rows = el.querySelectorAll('.cmf-tr:not(.is-head)'); expect(rows).toHaveLength(2); expect(rows[0].textContent).toContain('PoW sell'); expect(rows[1].textContent).toContain('−0.0060');
  expect(rows[0].querySelector('a').getAttribute('href')).toBe('https://solscan.io/tx/5DMYabcd'); expect(el.querySelector('.cmf-box.is-pot a').getAttribute('href')).toContain('solscan.io/account/7poJ');
});


test('🐝 Colonize opens the popout (what it is + the FEECAT stake), confirms at the picked pace, shows a refused stake, and leaves in one click', async () => {
  const sent = []; let refuse = true; mockSign.mockImplementation(async () => 'SIG');
  global.fetch = async (u, o) => { if (!o) return { ok: true, json: async () => ({ agents: [], cadence: 'daily', nextAirdrop: Date.now() / 1000 + 7200, pool: null }) }; const b = JSON.parse(o.body); sent.push(b); if (refuse && b.on && b.op === 'hive') { refuse = false; return { ok: false, status: 402, json: async () => ({ detail: 'The agent service did not answer.' }) }; } return { ok: true, status: 200, json: async () => (b.op === 'share' ? { colonyShare: { on: b.on, pct: b.cap } } : { hive: { on: b.on, every: b.cap } }) }; };
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<HiveSwitch cat={{ id: 'h1', name: 'Kit', hive: { on: false, every: 300 } }} />); });
  await act(async () => { el.querySelector('[data-testid="hive-toggle"]').click(); });
  expect(sent).toHaveLength(0); const pop = document.body.querySelector('[data-testid="colonize-pop"]');
  expect(pop.textContent).not.toContain('FEECAT in'); expect(pop.textContent).toContain('never pooled'); expect(pop.textContent).toContain('Colonize Kit');
expect(document.body.querySelector('[data-testid="colony-opp-stake"]').textContent).toContain('NOT OPEN YET'); expect(document.body.querySelector('[data-testid="colony-share-sign"]')).not.toBeNull();
  await act(async () => { document.body.querySelector('[data-testid="colony-share-20"]').click(); });
  await act(async () => { document.body.querySelector('[data-testid="colony-share-sign"]').click(); });   // 🤝 opportunity 2: one wallet signature, no transaction
  expect(mockSign.mock.calls.at(-1)[0]).toMatch(/^FEELESS colony share\nagent:h1\npct:20\nts:\d+$/); expect(sent.at(-1)).toMatchObject({ op: 'share', on: true, cap: 20, sig: 'SIG' }); sent.length = 0; refuse = true;
  await act(async () => { document.body.querySelector('[data-testid="colonize-pace-900"]').click(); });
  await act(async () => { document.body.querySelector('[data-testid="colonize-go"]').click(); });
  expect(sent.at(-1)).toMatchObject({ op: 'hive', on: true, cap: 900 }); expect(document.body.querySelector('[data-testid="colonize-err"]').textContent).toContain('did not answer');
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
  await act(async () => { createRoot(el).render(<ColonyGrid api={api} ids="g1,t1" extra={a => <button data-testid={`x-${a.id}`}>go</button>} />); });
  expect(asked[0]).toContain('ids=g1%2Ct1'); expect(el.querySelector('[data-testid="colony-mine"]')).not.toBeNull(); expect(el.querySelector('[data-testid="hive"]')).toBeNull();   // mine: no board
  expect(el.querySelector('[data-testid="cl-scr-g1-A"] img').getAttribute('src')).toContain('/api/cats/g1/screen/0?t=');
  expect(el.querySelector('[data-testid="cl-scr-g1-B"]').textContent).toContain('signing in');
  expect(el.querySelector('[data-testid="cl-scr-t1-A"] img').getAttribute("src")).toMatch(/last\/0$/); expect(el.querySelector('[data-testid="cl-scr-t1-A"]').textContent).toContain('LAST PAGE');
  expect(el.querySelector('[data-testid="cl-scr-t1-A"] [data-testid="cwb-cursor"]').className).toContain('is-rest');   // 🖱 always on, resting before its first move
  expect(el.querySelector('[data-testid="cl-g1"]').textContent).toContain('carrying “validator” to its drawer');
  expect(el.querySelector('[data-testid="x-t1"]')).not.toBeNull(); expect(el.querySelector('[data-testid="cl-g1"]').textContent).toContain('+3');
});

test('⛏ the PoW engine: the hard rules as a pipeline, live numbers, and each proof with its vitals per site, call and honey', async () => {
  const POW = { rules: { sites: 4, steps: 5, pulls: 3, everyMin: 30 }, rows: [
    { id: 'p1', name: 'Happy', sym: 'CAT', call: 'AVOID', strength: 52, sites: 2, steps: 7, honey: 2, graded: true, at: Date.now() / 1000 - 120, pulls: [{ site: 'rugcheck.xyz', label: 'mint authority', value: 'revoked' }, { site: 'solscan.io', label: 'top 10 holders', value: '61%' }] },
    { id: 'p2', name: 'Kit', sym: 'DOG', call: 'BUY', strength: 20, sites: 1, steps: 3, honey: null, graded: false, at: Date.now() / 1000 - 30, pulls: [] }] };
  global.fetch = async u => { expect(String(u)).toContain('/api/cats/pow'); return { ok: true, json: async () => POW }; };
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<PowEngine />); });
  expect(el.querySelectorAll('.hv-pow-flow li')).toHaveLength(6); expect(el.textContent).toContain('≤ 4 sites · ≤ 5 moves each');
  const cards = el.querySelectorAll('[data-testid="ck-pow"]'); expect(cards).toHaveLength(2);
  expect(cards[0].className).toContain('is-dn'); expect(cards[0].textContent).toContain('revoked'); expect(cards[0].textContent).toContain('🍯 +2');
  expect(cards[1].textContent).toContain('⏳ grading');
  expect(el.querySelector('.hv-pow-stats').textContent).toContain('100%');   // 1 graded, 1 right
  global.fetch = async () => ({ ok: true, json: async () => ({ ...POW, folders: [{ cat: 'h1', name: 'Happy', live: true, folder: { id: 'pow1', name: 'PoW #1 · Nov 01', phase: 'watch', status: 'open', coins: [{ mint: 'M1', sym: 'SIS', src: 'dex', liq: 64000 }], pick: { mint: 'M1' }, shots: [{ mint: 'M1', site: 'rugcheck.xyz', n: 1, file: 'r0_rugcheck.xyz_1.jpg' }] } }] }) });
  const el2 = document.createElement('div'); document.body.appendChild(el2);
  await act(async () => { createRoot(el2).render(<PowEngine />); });
  expect(el2.querySelector('[data-testid="pow-db"]').textContent).toContain('● LIVE');   // 🗄 every agent's folders, live + filed
  expect(el2.querySelector('[data-testid="dsk-fold-live"]').textContent).toContain('$SIS');
});

test('📖 the PoW manual: 5 steps (plan · research · choose · hold · file) and the commands — details open on a tap', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<ColonyManual />); });
  expect(el.querySelectorAll('.cfm-steps li')).toHaveLength(5); expect(el.textContent).toContain('file a PoW'); expect(el.textContent).not.toContain('+15 s');
  await act(async () => { el.querySelector('.cfm-h').click(); });
  expect(el.textContent).toContain('+15 s'); expect(el.textContent).toContain('2 snapshots a site');
});
