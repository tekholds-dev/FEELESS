import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { ProofMonitorBody, codeLines } from './ProofMonitor';

const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); await act(async () => { root.render(node); }); return { el, root }; };

test('🖥 PoStatic on a monitor = its real code beside its real page (read once through ws_open)', async () => {
  const work = jest.fn(async () => ({ doc: { code: '<html><head><title>x</title></head><body><script type="module">\nconst a = 1;\nnew THREE.Scene();\n</script></body></html>', preview: '<p>GLINT</p>' } }));
  const { el, root } = await mount(<ProofMonitorBody p={{ k: 'ps', f: { ws: 'w1', topic: 'GLINT' } }} catId="c" work={work} />);
  await act(async () => { await Promise.resolve(); });
  expect(work).toHaveBeenCalledWith('c', { op: 'ws_open', text: 'w1' });
  expect(el.querySelector('.pmn-code').textContent).toContain('new THREE.Scene();');
  expect(el.querySelector('iframe').getAttribute('srcdoc')).toBe('<p>GLINT</p>');
  expect(el.querySelector('iframe').getAttribute('sandbox')).toBe('allow-scripts');
  act(() => root.unmount());
});

test('🖥 each kind shows its own folder numbers; a missing number says so, never a made-up one', async () => {
  const { el, root } = await mount(<><ProofMonitorBody p={{ k: 'pow', f: { sym: 'LEEROY', pnlPct: -11.31, minds: 2, phase: 'done' } }} />
    <ProofMonitorBody p={{ k: 'pob', f: { topic: 'best nba picks tonight', sites: ['espn.com', 'nba.com'], calls: [], noTrade: true } }} />
    <ProofMonitorBody p={{ k: 'poe', f: { topic: 'Example books', months: [{ month: '2026-09', income: 6200, costs: 4320 }], net: 1880, margin: 30.3 } }} />
    <ProofMonitorBody p={{ k: 'pow', f: { sym: 'NEW' } }} /></>);
  expect(el.textContent).toContain('$LEEROY'); expect(el.querySelector('.pmn-pnl.is-dn')).toBeTruthy();
  expect(el.textContent).toContain('No call: nothing was read');
  expect(el.textContent).toContain('Example books'); expect(el.textContent).toContain('margin 30.3%');
  expect(el.textContent).toContain('no trade yet');
  act(() => root.unmount());
});

test('codeLines skips the page head and blank lines', () => {
  expect(codeLines('<head>\n<title>t</title>\n</head>\n<script>\n\nlet x = 1;\n</script>')).toEqual(['<script>', 'let x = 1;', '</script>']);
});

test('🖥 a newest PoStatic takes both monitors: code on one, page on the other', () => {
  const { monitorProof } = require('./CatWorkbench');
  const ps = { k: 'ps', id: 's1' }; const pow = { k: 'pow', id: 'w1' };
  expect(monitorProof([ps, pow], 0, 2).view).toBe('code'); expect(monitorProof([ps, pow], 1, 2).view).toBe('page');
  expect(monitorProof([ps, pow], 2, 4)).toBe(pow);
  expect(monitorProof([pow, ps], 0, 2).view).toBe('code'); expect(monitorProof([pow, ps], 1, 2).view).toBe('page');   // owner 2026-11-13: an older PoStatic still splits, never squeezed into one
  expect(monitorProof([pow, ps], 2, 3)).toBe(pow);
  expect(monitorProof([pow, ps], 1, 2, [false, true])).toBe(ps); expect(monitorProof([pow, ps], 1, 2, [false, true]).view).toBe(undefined);   // separate jobs: one each, no split
});

test('🖥 a PoC shows its own made media first (owner 2026-11-12, Bishop), then its idea text — never a bare nothing', async () => {
  // made image leads
  let { el, root } = await mount(<ProofMonitorBody p={{ k: 'poc', f: { topic: 'BishopRealistic', media: [{ id: 'm1', kind: 'image', url: '/api/cats/media/c/m1.png', label: 'Flash Image', prompt: 'Bishop' }], calls: [{ post: 'Create Bishop' }] } }} catId="c" />);
  expect(el.querySelector('[data-testid="pmn-poc-media"]').getAttribute('src')).toContain('/api/cats/media/c/m1.png');
  expect(el.textContent).toContain('Flash Image'); act(() => root.unmount());
  // a made video plays silently
  ({ el, root } = await mount(<ProofMonitorBody p={{ k: 'poc', f: { topic: 'B', media: [{ id: 'm2', kind: 'video', url: '/api/cats/media/c/m2.mp4', label: 'Seedance 2.0 fast' }] } }} catId="c" />));
  const v = el.querySelector('[data-testid="pmn-poc-video"]'); expect(v.getAttribute('src')).toContain('m2.mp4'); expect(v.muted).toBe(true); act(() => root.unmount());
  // no media, no shot: the idea itself is drawn
  ({ el, root } = await mount(<ProofMonitorBody p={{ k: 'poc', f: { topic: 'BishopRealistic', calls: [{ post: 'Create a Black dude named Bishop in the latest gear' }] } }} catId="c" />));
  expect(el.querySelector('[data-testid="pmn-poc-idea"]').textContent).toContain('named Bishop');
  act(() => root.unmount());
});

test('🎲 a PoB monitor is its game live: the score, every slip on that game (fees never in P&L), each mind, the sites it really read', async () => {
  const f0 = global.fetch; global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: async () => ({ state: 'in', status: '3:10 - 2nd', teams: [{ abbr: 'UTAH', score: 48 }, { abbr: 'LAC', score: 55 }] }) }));
  const g = [{ id: '401910006', sport: 'nba', label: 'Jazz at Clippers' }];
  const f = { id: 'p21', topic: 'Jazz vs Clippers team to win', games: g, browsed: { 0: { sites: ['kalshi.com', 'espn.com'] }, 1: { sites: ['polymarket.com'] } }, sites: ['kalshi.com', 'covers.com'],
    calls: [{ mind: 0, name: 'gpt-6.1-sol', picks: [{ pick: 'Clippers to win', confidence: 68 }] }, { mind: 1, name: 'glm-5.3', picks: [] }],
    kalshi: { title: 'Los Angeles C wins', side: 'yes', orderId: 'o', status: 'filled', count: 2, filled: 2, price: 0.68, usd: 1.36, livePx: 0.8 } };
  const slip = { id: 'p22', games: g, kalshi: { kind: 'parlay', status: 'waiting', legs: [{ title: 'LAC' }, { title: 'Harden 20+' }] } };
  const { el, root } = await mount(<ProofMonitorBody p={{ k: 'pob', f, also: [slip] }} />); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(global.fetch.mock.calls[0][0]).toContain('/api/cats/tools/game/nba/401910006');
  expect(el.querySelector('[data-testid="pmn-score"]').textContent).toContain('UTAH 48 – 55 LAC');
  const rows = el.querySelectorAll('[data-testid="pmn-slips"] li');
  expect(rows).toHaveLength(2); expect(rows[0].textContent).toContain('$1.36 in · $1.60 now · +$0.24'); expect(rows[1].textContent).toContain('2-leg parlay'); expect(rows[1].textContent).toContain('waiting for your tap');
  expect(el.textContent).toContain('Clippers to win'); expect(el.textContent).toContain('passed');
  expect([...el.querySelectorAll('.pmn-sites li.is-read')].map(x => x.textContent)).toEqual(['kalshi.com', 'espn.com', 'polymarket.com']);
  act(() => root.unmount()); global.fetch = f0;
});

test('🎯 the proof opened on the desk leads the monitors even when it is older than the 4 newest, with its game\'s other slips', () => {
  const { deskProofs } = require('./CatWorkbench');
  const g = [{ id: 'G1', sport: 'nba' }];
  const pobFolders = [{ id: 'old', at: 1, topic: 'Jazz vs Clippers', games: g, kalshi: { ticker: 'T' } }, ...[2, 3, 4, 5, 6].map(n => ({ id: `p${n}`, at: n, topic: `t${n}` })), { id: 'slip', at: 7, games: g, kalshi: { kind: 'parlay' } }];
  const out = deskProofs({ pobFolders, deskProof: { id: 'old' } });
  expect(out[0].id).toBe('old'); expect(out[0].also.map(x => x.id)).toEqual(['slip']); expect(out).toHaveLength(4);
  expect(deskProofs({ pobFolders }).map(x => x.id)).toEqual(['slip', 'p6', 'p5', 'p4']);
});
