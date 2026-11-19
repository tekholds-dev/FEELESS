import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FeaturesFolder } from './FeaturesFolder';
import { addPick, pinRows } from './PsInspect';

// 🔍 Slice 9 · PoStatic: inspect, not mark. Click → saved/sent with the exact element → the next version shows it before and after.
jest.mock('../terminal/TrenchChart', () => ({ TrenchChart: () => <i data-testid="trench" /> }));
jest.mock('../perps/PerpsChart', () => ({ PerpsChart: () => <i data-testid="perps" /> }));
jest.mock('../terminal/TradeTape', () => ({ TradeTape: () => <i data-testid="tape" /> }));
jest.mock('./FeeCatShell', () => ({ goTo: jest.fn() }));
const DATA = { workspaces: [{ id: 'w1', kind: 'build', name: 'Site' }], memory: { notes: 0, mindNotes: 0, recent: [], personal: '' }, print: { level: 1, proofs: 0, traits: [] }, edge: [], edgeCats: {}, indicators: [], pocFolders: [] };
const RUN = { at: 5, ask: 'say Top 10 pools', from: 1, to: 2, asked: 1, changed: 1, rows: [{ sel: '#pools > h2', tag: 'h2', note: 'say Top 10 pools', changed: true, gone: false, before: { found: true, code: '<h2>Top pools today</h2>', text: 'Top pools today', shot: '/api/cats/media/c/m000000000001.jpg' }, after: { found: true, code: '<h2>Top 10 pools</h2>', text: 'Top 10 pools', shot: '/api/cats/media/c/m000000000002.jpg' } }] };
const DOC = { id: 'w1', kind: 'build', name: 'Site', messages: [], versions: 2, by: 'Mind A', code: '<h1>hi</h1>', preview: '<h1>hi</h1>', busy: null, inspect: [RUN], comments: [{ id: 'k1', sel: 'body > header > h1', tag: 'h1', text: 'Solana', note: 'too green', at: 4 }] };
const type = async (n, v) => { await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(n, v); n.dispatchEvent(new Event('input', { bubbles: true })); }); };

async function open(doc) {
  const work = jest.fn(async (_, b) => (b.op === 'ws_open' ? { doc } : b.op === 'ws_build' ? { doc: { ...doc, busy: { at: 1 } } } : b.op === 'ws_comment' ? { doc: { ...doc, comments: [...doc.comments, { id: 'k2', sel: b.tools.target?.sel, tag: 'p', note: b.text, at: 6 }] } } : DATA));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FeaturesFolder cat={{ id: 'c' }} d={{ setup: { use: 'code' } }} work={work} onCommand={() => {}} />); });
  await act(async () => { await Promise.resolve(); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { q('fea-tab-work').click(); }); await act(async () => { q('ws-w1').click(); }); await act(async () => { await Promise.resolve(); });
  return { el, q, work };
}
const pick = async (w, d) => act(async () => { window.dispatchEvent(new MessageEvent('message', { data: { t: 'feeless-inspected', ...d }, source: w })); });

test('the mark tool is gone from a built page: Inspect turns hover-highlight on inside the page and its pins go in', async () => {
  const { q } = await open(DOC);
  expect(q('ws-mark')).toBeNull(); const btn = q('ws-inspect'); expect(btn.dataset.tip).toMatch(/hover the page/);
  const w = q('ws-frame').contentWindow; const spy = jest.spyOn(w, 'postMessage');
  await act(async () => { btn.click(); });
  expect(spy).toHaveBeenCalledWith({ t: 'feeless-inspect', on: true }, '*'); expect(btn.getAttribute('aria-pressed')).toBe('true');
  expect(spy).toHaveBeenCalledWith({ t: 'feeless-inspect-pins', rows: [{ sel: 'body > header > h1', n: 'C1', kind: 'comment' }] }, '*');
  await act(async () => { window.dispatchEvent(new MessageEvent('message', { data: { t: 'feeless-inspect-off' }, source: w })); });
  expect(btn.getAttribute('aria-pressed')).toBe('false');
});

test('a click on an element opens Fix this aimed at it: the request carries its selector, text and code', async () => {
  const { q, work } = await open(DOC); const w = q('ws-frame').contentWindow;
  await pick(w, { sel: '#pools > h2', tag: 'h2', text: 'Top pools today', html: '<h2>Top pools today</h2>', rect: { x: 0.1, y: 0.3, w: 0.5, h: 0.05 }, css: { fontSize: '24px', color: 'rgb(25, 230, 140)' } });
  expect(q('ws-insp-card-0').textContent).toContain('#pools > h2'); expect(q('ws-insp-card-0').textContent).toContain('Top pools today');
  await type(q('ws-insp-note-0'), 'say Top 10 pools');
  await act(async () => { q('ws-insp-fix-0').click(); });
  const call = work.mock.calls.find(([, b]) => b.op === 'ws_build')[1];
  expect(call).toMatchObject({ job: 'w1', text: 'say Top 10 pools', to: 'both' });
  expect(call.tools.region[0]).toMatchObject({ kind: 'el', mode: 'fix', sel: '#pools > h2', text: 'Top pools today', html: '<h2>Top pools today</h2>', note: 'say Top 10 pools' });
  expect(q('ws-insp-card-0')).toBeNull();
});

test('Comment keeps a free note on that element, and the before and after of the last inspect shows', async () => {
  const { el, q, work } = await open(DOC); const w = q('ws-frame').contentWindow;
  await pick(w, { sel: 'body > main > p', tag: 'p', text: 'Volume', html: '<p>Volume</p>' });
  expect(q('ws-insp-comment-0').disabled).toBe(true); await type(q('ws-insp-note-0'), 'explain this better');
  await act(async () => { q('ws-insp-comment-0').click(); });
  expect(work).toHaveBeenCalledWith('c', expect.objectContaining({ op: 'ws_comment', job: 'w1', text: 'explain this better', tools: { target: expect.objectContaining({ sel: 'body > main > p' }) } }));
  expect(q('ws-insp-comments').textContent).toContain('explain this better');
  const row = q('ws-insp-row-0'); expect(row.textContent).toContain('CHANGED'); expect(row.textContent).toContain('Top 10 pools');
  expect([...row.querySelectorAll('img')].map(i => i.getAttribute('src'))).toEqual([RUN.rows[0].before.shot, RUN.rows[0].after.shot]);
  expect(q('ws-insp-diff').textContent).toContain('Page 1 → page 2'); expect(el.textContent).toContain('1/1');
});

test('an old saved mark still opens on the page and goes with Finish it', async () => {
  const old = { ...DOC, inspect: [], comments: [], unfinished: { ask: 'fix the header', why: 'It stopped.', at: 9, region: [{ x: 0.1, y: 0.2, w: 0.3, h: 0.1, sy: 0, note: 'old saved mark' }] } };
  const { q } = await open(old);
  expect(q('ws-box-0')).toBeTruthy(); expect(q('ws-mark-note-0').value).toBe('old saved mark'); expect(q('ws-finish')).toBeTruthy();
});

test('picks: newest wins on one selector, at most six; pins number fixes and comments apart', () => {
  let ps = [];
  for (let i = 0; i < 8; i += 1) ps = addPick(ps, { sel: `body > p:nth-of-type(${i + 1})`, tag: 'p' });
  ps = addPick(ps, { sel: 'body > p:nth-of-type(8)', tag: 'p', text: 'again' });
  expect(ps).toHaveLength(6); expect(ps[5].text).toBe('again'); expect(addPick(ps, {})).toBe(ps);
  expect(pinRows(ps.slice(0, 1), [{ sel: 'x' }])).toEqual([{ sel: ps[0].sel, n: 1, kind: 'fix' }, { sel: 'x', n: 'C1', kind: 'comment' }]);
});
