import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FeaturesFolder, FEATURES, ProofDesk, STARTERS, briefOf } from './FeaturesFolder';
import { nextMove } from './CollectiveTop';

jest.mock('../terminal/TrenchChart', () => ({ TrenchChart: () => <i data-testid="trench" /> }));
jest.mock('../perps/PerpsChart', () => ({ PerpsChart: ({ asset }) => <i data-testid="perps">{asset}</i> }));
jest.mock('../terminal/TradeTape', () => ({ TradeTape: () => <i data-testid="tape" /> }));
jest.mock('./FeeCatShell', () => ({ goTo: jest.fn() }));
const DATA = { workspaces: [], memory: { notes: 3, mindNotes: 1, recent: ['a note'], personal: '' }, print: { level: 40, proofs: 6, traits: [{ t: 'source pump', score: 2, n: 3, won: 3 }] }, edge: [{ id: 'x', cat: 'safety', t: 'Mint on', read: 'r', means: 'm', do: 'd', stop: 's' }], edgeCats: { safety: 'Rugs' }, indicators: [{ id: 'rsi', t: 'RSI' }], pocFolders: [] };
async function mount(work, d = { setup: { use: 'code' } }) { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(<FeaturesFolder cat={{ id: 'c' }} d={d} work={work} onCommand={() => {}} />); }); await act(async () => { await Promise.resolve(); }); await act(async () => { }); return { el, q: id => el.querySelector(`[data-testid="${id}"]`) }; }
const type = async (n, v) => { await act(async () => { const set = Object.getOwnPropertyDescriptor(n.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype, 'value').set; set.call(n, v); n.dispatchEvent(new Event('input', { bubbles: true })); }); };

test('every proof type in the Showcase ends in a start', async () => {
  const { el, q } = await mount(jest.fn(async () => DATA));
  expect(q('fea-tab-features')).toBeNull();   // the start lives under every Showcase preview now
  for (const k of ['pos', 'pow', 'pop', 'pob', 'poc', 'poe']) { await act(async () => { q(`pdr-${k}`).click(); }); expect(q('sst-go')).toBeTruthy(); }
});
test('create makes a real folder and opens it: blank screen, a mind picker, send goes to the owner door', async () => {
  const doc = { id: 'w1', kind: 'build', name: 'Site', messages: [], versions: 0, code: '', preview: '', busy: null };
  const work = jest.fn(async (_, b) => (b.op === 'feature_create' ? { folder: { id: 'w1', kind: 'build', name: 'Site' }, workspaces: [{ id: 'w1', kind: 'build', name: 'Site' }] } : b.op === 'ws_open' ? { doc } : b.op === 'ws_build' ? { doc: { ...doc, messages: [{ by: 'you', text: b.text }], busy: null } } : DATA));
  const { el, q } = await mount(work);
  await act(async () => { q('sst-go').click(); }); await act(async () => { await Promise.resolve(); });
  expect(el.textContent).toContain('A blank screen'); expect(q('ws-mark').disabled).toBe(true);
  await act(async () => { q('ws-to-a').click(); }); await type(q('ws-input'), 'make a timer');
  await act(async () => { q('ws-send').click(); });
  expect(work).toHaveBeenCalledWith('c', expect.objectContaining({ op: 'ws_build', job: 'w1', text: 'make a timer', to: 'a' }));
});
test('a built page runs only in a sandbox with no same-origin, and code and static switch', async () => {
  const doc = { id: 'w1', kind: 'build', name: 'Site', messages: [], versions: 1, by: 'Mind A', code: '<b>hi</b>', preview: '<b>hi</b>', busy: null };
  const work = jest.fn(async (_, b) => (b.op === 'ws_open' ? { doc } : { ...DATA, workspaces: [{ id: 'w1', kind: 'build', name: 'Site' }] }));
  const { q } = await mount(work);
  await act(async () => { q('fea-tab-work').click(); }); await act(async () => { q('ws-w1').click(); }); await act(async () => { await Promise.resolve(); });
  expect(q('ws-frame').getAttribute('sandbox')).toBe('allow-scripts');
  await act(async () => { q('ws-view-code').click(); }); expect(q('ws-code').textContent).toContain('<b>hi</b>'); expect(q('ws-frame')).toBeNull();
});
test('its mind: start fresh asks first, clean and about you go through the owner door', async () => {
  const work = jest.fn(async (_, b) => (b.op === 'memory' ? { memory: { ...DATA.memory, notes: b.job === 'fresh' ? 0 : 3 } } : DATA));
  const { el, q } = await mount(work);
  await act(async () => { q('fea-tab-mind').click(); });
  expect(q('fea-print').textContent).toContain('40');
  await act(async () => { q('fea-fresh').click(); }); expect(work).not.toHaveBeenCalledWith('c', expect.objectContaining({ op: 'memory' }));
  await act(async () => { q('fea-fresh-yes').click(); }); expect(work).toHaveBeenCalledWith('c', { op: 'memory', job: 'fresh', text: undefined }); expect(el.textContent).toContain('proofs and fingerprint stay');
  await type(q('fea-personal'), 'I like it short'); await act(async () => { q('fea-personal-save').click(); }); expect(work).toHaveBeenCalledWith('c', { op: 'memory', job: 'personal', text: 'I like it short' });
});
test('the next move follows what is off', () => {
  expect(nextMove({ auto: false })[0]).toContain('Auto-collect'); expect(nextMove({ auto: true, convo: false })[0]).toContain('convos'); expect(nextMove({ auto: true, convo: true, weight: 1.4 })[0]).toContain('boost'); expect(nextMove({ auto: true, convo: true, weight: 2 })[0]).toContain('full');
});

test('a filed PoC keeps its response verdict visible and updates its print when marked', async () => {
  const f = { id: 'pc1', n: 1, ws: 'w1', topic: 'Memecoin narratives', calls: [{ mind: 0, post: 'Three narratives to watch' }] };
  const work = jest.fn(async (_, b) => b.op === 'poc_mark' ? { pocFolders: [{ ...f, graded: b.text }] } : b.op === 'ws_open' ? { doc: { messages: [] } } : { workspaces: [{ id: 'w1', kind: 'content', name: 'Ideas' }], pocFolders: [f], psFolders: [] });
  const setD = jest.fn();
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<ProofDesk cat={{ id: 'c' }} kind="content" work={work} d={{}} setD={setD} />); });
  await act(async () => { el.querySelector('[data-testid="ws-w1"]').click(); });
  expect(el.querySelector('[data-testid="poc-mark-pc1"]').textContent).toContain('Did you like this response?');
  await act(async () => { el.querySelector('[data-testid="poc-right-pc1"]').click(); });
  expect(work).toHaveBeenCalledWith('c', expect.objectContaining({ op: 'poc_mark', job: 'pc1', text: 'right' }));
  expect(setD).toHaveBeenCalled();
  expect(setD.mock.calls.at(-1)[0]({}).pocFolders[0].graded).toBe('right');
  expect(el.querySelector('[data-testid="poc-right-pc1"]').getAttribute('aria-pressed')).toBe('true');
  expect(el.querySelector('[data-testid="poc-mark-pc1"] .prg path:last-child').getAttribute('stroke')).toBe('#4dea8f');
  await act(async () => root.unmount());
});

test('every filed PoC has its own opening folder and recorded cost', async () => {
  const filed = [1, 2].map(n => ({ id: `pc${n}`, n, topic: `Topic ${n}`, cost: 0.0123 * n, calls: [{ mind: 0, post: `Post ${n}` }] }));
  const work = jest.fn(async () => ({ workspaces: [{ id: 'w1', kind: 'content', name: 'Ideas' }], pocFolders: filed, psFolders: [] }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<ProofDesk cat={{ id: 'c' }} kind="content" work={work} d={{}} />); });
  expect(el.querySelectorAll('[data-testid^="poc-file-"]')).toHaveLength(2);
  await act(async () => { el.querySelector('[data-testid="poc-file-pc2"]').click(); });
  expect(el.querySelector('[data-testid="poc-folder-pc2"]').textContent).toContain('$0.0246');
  expect(el.querySelector('[data-testid="poc-folder-pc2"]').textContent).toContain('Post 2');
  await act(async () => root.unmount()); el.remove();
});

test('PoStatic approval grows its progress and can complete the proof', async () => {
  const row = { id: 'w1', kind: 'build', name: 'Site' }; const f = { id: 'ps1', n: 1, ws: 'w1' };
  const doc = { ...row, versions: 1, code: '<p>new</p>', previousCode: '<p>old</p>', preview: '<p>new</p>', messages: [], busy: null, cost: 0.0032 };
  const work = jest.fn(async (_, b) => b.op === 'features' ? { workspaces: [row], psFolders: [f] } : b.op === 'state' ? { psFolders: [f] } : b.op === 'ws_open' ? { doc } : b.op === 'ps_mark' ? { psFolders: [{ ...f, graded: b.text }] } : b.op === 'ws_complete' ? { doc: { ...doc, complete: true } } : {});
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<ProofDesk cat={{ id: 'c' }} kind="build" work={work} d={{}} />); });
  await act(async () => { el.querySelector('[data-testid="ws-w1"]').click(); });
  expect(el.querySelector('[data-testid="ws-cost"]').textContent).toContain('$0.0032');
  await act(async () => { el.querySelector('[data-testid="ws-view-code"]').click(); });
  expect(el.querySelector('[data-testid="ws-code"]').textContent).toContain('+1 added');
  await act(async () => { el.querySelector('[data-testid="ws-pos-yes"]').click(); });
  expect(el.querySelector('[role="progressbar"]').getAttribute('aria-valuenow')).toBe('1');
  await act(async () => { el.querySelector('[data-testid="ws-complete"]').click(); });
  expect(work).toHaveBeenCalledWith('c', expect.objectContaining({ op: 'ws_complete', job: 'w1' }));
  expect(el.querySelector('[data-testid="ws-complete"]').textContent).toContain('✓');
  await act(async () => root.unmount()); el.remove();
});

test('a PoStatic shows its steps, waits on its plan, and approval is what builds it', async () => {
  const { act } = require('react-dom/test-utils'); const { createRoot } = require('react-dom/client');
  const doc = { id: 'w1', kind: 'build', name: 'B', messages: [{ by: 'you', text: 'x' }], stage: 'approve', busy: null, versions: 0, cfg: { research: true, suggest: true, review: true, depth: 'quick' }, plan: { by: 'Mind A', approved: false, allRefs: [{ title: 'a/b', url: 'https://a', source: 'GitHub', score: 9, open: true }, { title: 'c', url: 'https://c', source: 'Hacker News', score: 1, open: false }], plan: { summary: 'A desk', steps: ['one'], borrow: 'layout', refs: [], risks: 'none' } } };
  const work = jest.fn(async (id, b) => (b.op === 'ws_open' ? { doc } : b.op === 'features' ? { workspaces: [{ id: 'w1', kind: 'build', name: 'B' }] } : b.op === 'ws_approve' ? { doc: { ...doc, busy: { stage: 'build' }, stage: 'build', plan: { ...doc.plan, approved: true } } } : b.op === 'ws_cfg' ? { doc: { ...doc, cfg: { ...doc.cfg, ...b.tools } } } : {}));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const { FeaturesFolder } = require('./FeaturesFolder');
  await act(async () => { root.render(<FeaturesFolder cat={{ id: 'c' }} d={{}} work={work} />); });
  await act(async () => { [...el.querySelectorAll('[role="tab"]')].find(b => b.textContent.includes('Your work')).click(); });
  await act(async () => { el.querySelector('[data-testid="ws-w1"]').click(); });
  expect(el.querySelector('[data-testid="ws-steps"] .is-now').textContent).toContain('You approve');
  expect(el.querySelector('[data-testid="ws-plan-stage"]').textContent).toContain('A desk'); expect(el.querySelector('[data-testid="ws-plan-stage"]').textContent).toContain('Blocked');   // a waiting plan takes the stage (owner 2026-11-09)
  await act(async () => { el.querySelector('[data-testid="ws-settings"]').click(); });
  await act(async () => { el.querySelector('[data-testid="ws-depth-deep"]').click(); }); expect(work).toHaveBeenCalledWith('c', expect.objectContaining({ op: 'ws_cfg', tools: expect.objectContaining({ depth: 'deep' }) }));
  await act(async () => { el.querySelector('[data-testid="ws-approve"]').click(); }); expect(work).toHaveBeenCalledWith('c', { op: 'ws_approve', job: 'w1', text: '' });
  expect(el.querySelector('[data-testid="ws-steps"] .is-now').textContent).toContain('It builds');
  await act(async () => root.unmount());
});

test('Discover keeps the kit on screen, caps picks at 3, and lets the agent choose', async () => {
  const { KitPick } = require('./FeaturesFolder');
  const kits = ['heroui', 'shadcn', 'magicui', 'motion'].map(id => ({ id, name: id, what: 'x', site: 'https://x.y', license: 'MIT', added: id === 'heroui', vitals: { items: 2 } }));
  const state = { kits, picks: [], mode: 'auto', max: 3 }; const calls = [];
  const fake = async (_, b) => { calls.push(b); if (b.op === 'kit_pick') { state.picks = b.text ? b.text.split(',') : []; state.mode = b.job; } return { ...state }; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<KitPick cat={{ id: 'c' }} work={fake} />); });
  expect(el.querySelector('[data-testid="kit-auto"]')).not.toBeNull();
  await act(async () => { el.querySelector('[data-testid="kit-discover"]').click(); });
  for (const id of ['heroui', 'shadcn', 'magicui']) { await act(async () => { document.querySelector(`[data-testid="kit-pick-${id}"]`).click(); }); }
  expect(calls.at(-1)).toMatchObject({ op: 'kit_pick', text: 'heroui,shadcn,magicui', job: 'mine' });
  expect(el.querySelector('[data-testid="kit-on-heroui"]')).not.toBeNull();
  expect(document.querySelector('[data-testid="kit-pick-motion"]').disabled).toBe(true);
  await act(async () => { document.querySelector('[data-testid="kit-pick-heroui"]').click(); });
  expect(el.querySelector('[data-testid="kit-pick"]')).not.toBeNull(); expect(el.querySelector('[data-testid="kit-on-heroui"]')).toBeNull();
  await act(async () => { document.querySelector('[data-testid="kit-mode-auto"]').click(); });
  expect(calls.at(-1)).toMatchObject({ job: 'auto' }); expect(el.querySelector('[data-testid="kit-auto"]')).not.toBeNull();
  await act(async () => { root.unmount(); }); el.remove();
});

test('a folder chat shows this chat and the folder, and the cost moves while it builds', async () => {
  const { ChatCost, LiveCode } = require('./FeaturesFolder');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<ChatCost doc={{ cost: 0.01, lastCost: 0.004 }} />); });
  expect(el.querySelector('[data-testid="ws-cost-chat"]').textContent).toBe('$0.0040'); expect(el.querySelector('[data-testid="ws-cost-folder"]').textContent).toBe('$0.0100');
  await act(async () => { root.render(<ChatCost doc={{ cost: 0.01, lastCost: 0.004, busy: { spent: 0.002 } }} />); });
  expect(el.querySelector('[data-testid="ws-cost-chat"]').textContent).toBe('$0.0020'); expect(el.querySelector('[data-testid="ws-cost-folder"]').textContent).toBe('$0.0120');
  document.body.classList.add('fx-lite');
  await act(async () => { root.render(<LiveCode draft={'<html>\n<body>'} by="Mind A" stage="build" />); });
  expect(el.querySelector('[data-testid="ws-live-code"]').textContent).toContain('Mind A is writing'); expect(el.querySelector('pre').textContent).toContain('<body>');
  document.body.classList.remove('fx-lite');
  await act(async () => { root.unmount(); }); el.remove();
});

test('Save keeps a page in its own folder and can take it out again', async () => {
  const { SaveToRepo } = require('./FeaturesFolder');
  const calls = []; let doc = { preview: '<html/>', savedToRepo: false };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const draw = () => root.render(<SaveToRepo cat={{ id: 'c' }} row={{ id: 'w1' }} doc={doc} work={async (_, b) => { calls.push(b); return { saved: b.on }; }} setDoc={f => { doc = f(doc); }} />);
  await act(async () => { draw(); });
  await act(async () => { el.querySelector('[data-testid="ws-save-repo"]').click(); });
  expect(calls[0]).toEqual({ op: 'ws_repo', text: 'w1', on: true }); expect(doc.savedToRepo).toBe(true);
  await act(async () => { draw(); }); expect(el.querySelector('[data-testid="ws-save-repo"]').textContent).toBe('Saved');
  await act(async () => { el.querySelector('[data-testid="ws-save-repo"]').click(); }); expect(calls[1].on).toBe(false);
  await act(async () => { root.unmount(); }); el.remove();
});

test('a folder opens with its own proof only, can file its answer, and any proof sends only on the second tap', async () => {
  const mine = { id: 'pa', n: 2, ws: 'w1', topic: 'Narrative Finder', calls: [{ mind: 0, post: 'A real thesis' }] }; const other = { id: 'pb', n: 1, topic: 'Memecoin trends', calls: [{ mind: 0, post: 'Some other proof' }] };
  const work = jest.fn(async (_, b) => (b.op === 'ws_open' ? { doc: { id: 'w1', messages: [{ by: 'Mind A', text: 'x'.repeat(50) }] } } : b.op === 'poc_answer' ? { pocFolders: [mine, other] } : b.op === 'pot_send' ? { sent: { sol: 0.05, sig: 'SIG' }, review: { seats: [{ k: 'tally', name: 'Tally', ok: true, why: 'ok' }] } } : { workspaces: [{ id: 'w1', kind: 'content', name: 'Narrative Finder' }], pocFolders: [mine, other], psFolders: [] }));
  jest.spyOn(require('../../lib/solPrice'), 'useSolPrice').mockReturnValue(100);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const q = t => el.querySelector(`[data-testid="${t}"]`);
  await act(async () => { root.render(<ProofDesk cat={{ id: 'c' }} kind="content" work={work} d={{}} setD={() => {}} />); });
  await act(async () => { q('ws-w1').click(); });
  expect(q('poc-pa')).not.toBeNull(); expect(q('poc-pb')).toBeNull(); expect(q('poc-mark-pa')).not.toBeNull(); expect(q('poc-mark-pb')).toBeNull();
  await act(async () => { q('poc-file-answer').click(); }); expect(work).toHaveBeenCalledWith('c', expect.objectContaining({ op: 'poc_answer', job: 'w1' }));
  expect(q('proof-usd-5')).toBeNull(); await act(async () => { q('proof-open').click(); });   // one small button until asked
  await act(async () => { q('proof-usd-5').click(); }); await act(async () => { q('proof-send').click(); });
  expect(work.mock.calls.some(c => c[1].op === 'pot_send')).toBe(false); expect(q('proof-send').textContent).toBe('Yes, send $5');
  await act(async () => { q('proof-send').click(); }); expect(work).toHaveBeenCalledWith('c', expect.objectContaining({ op: 'pot_send', job: 'pa', cap: 0.05 })); expect(q('proof-submit-sent').textContent).toContain('$5');
  await act(async () => { root.unmount(); }); el.remove();
});

test('the thin bar moves on real steps and real text, and never fakes a number', () => {
  const { buildPart } = require('./FeaturesFolder');
  expect(buildPart({ stage: 'research' })).toBeCloseTo(0.3 / 4); expect(buildPart({ stage: 'build', draft: '' })).toBe(0.5);
  expect(buildPart({ stage: 'build', draft: 'x'.repeat(12500) })).toBeCloseTo(0.625); expect(buildPart({ stage: 'review', draft: 'x'.repeat(99999) }, 25000)).toBeLessThan(0.98);
  expect(buildPart({})).toBeNull(); expect(buildPart({ stage: 'content' })).toBeNull();
  expect(buildPart({ stage: 'answer', step: 1, steps: 2 })).toBe(0.5); expect(buildPart({ stage: 'answer', step: 0, steps: 2 })).toBe(0.04);   // a PoC: minds answered of how many (owner 2026-11-09: "loading bar not true")
  expect(buildPart({ stage: 'answer' })).toBeNull();
});

test('a plan waiting on you takes the stage; approved or building, it goes back to the side', () => {
  const { planWaiting } = require('./FeaturesFolder');
  const plan = { plan: { summary: 'x', steps: ['a'] }, approved: false };
  expect(planWaiting({ plan })).toBe(true); expect(planWaiting({ plan: { ...plan, approved: true } })).toBe(false);
  expect(planWaiting({ plan, busy: { stage: 'build' } })).toBe(false); expect(planWaiting({})).toBe(false);
});

test('a long answer is kept whole and folds behind Read more at a word, never cut mid-word', () => {
  const { foldText } = require('./FeaturesFolder');
  expect(foldText('short answer')).toBeNull();
  const long = 'word '.repeat(400).trim(); const f = foldText(long);
  expect(f.endsWith('…')).toBe(true); expect(f.length).toBeLessThan(600); expect(f.slice(0, -1).endsWith('word')).toBe(true);
});

test('a stopped PoStatic says why, Finish runs the same ask, and Keep stops at the last page', async () => {
  const doc = { id: 'w1', kind: 'build', name: 'B', stage: 'review', busy: null, pending: true, versions: 5, cost: 0.02, messages: [{ by: 'you', text: 'fix the buttons' }, { by: 'Mind A', text: 'Nothing changed' }], cfg: { research: true, suggest: true, review: true, depth: 'quick' }, unfinished: { ask: 'fix the buttons', why: 'Its changes did not match the page.' } };
  const work = jest.fn(async (id, b) => (b.op === 'ws_open' ? { doc } : b.op === 'features' ? { workspaces: [{ id: 'w1', kind: 'build', name: 'B' }] } : b.op === 'ws_keep' ? { doc: { ...doc, unfinished: null, stage: 'filed', pending: false } } : b.op === 'ws_build' ? { doc: { ...doc, unfinished: null, busy: { stage: 'build', at: 1 } } } : {}));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<FeaturesFolder cat={{ id: 'c' }} d={{}} work={work} />); });
  await act(async () => { [...el.querySelectorAll('[role="tab"]')].find(b => b.textContent.includes('Your work')).click(); });
  await act(async () => { el.querySelector('[data-testid="ws-w1"]').click(); });
  const q = t => el.querySelector(`[data-testid="${t}"]`);
  expect(q('ws-finish').textContent).toContain('did not match'); expect(q('ws-finish-keep').textContent).toContain('Keep page 5'); expect(el.querySelector('[data-testid="ws-steps"] .is-stopped').textContent).toContain('other mind');
  await act(async () => { q('ws-finish-go').click(); });
  expect(work).toHaveBeenCalledWith('c', { op: 'ws_build', job: 'w1', text: 'fix the buttons', finish: true, to: 'both' }); expect(q('ws-finish')).toBeNull();
  await act(async () => root.unmount());
});

test('🧰 a kit opens in full with why it is suggested, a ready set fills the picks, and a PoW kit says it needs a pick', async () => {
  const { KitPick } = require('./FeaturesFolder');
  const calls = []; const row = { id: 'fl-coin-vet', name: 'Coin Vetter', what: 'Checks a coin', kinds: ['pow'], cat: 'Research', task: 'Trading research', skills: ['rug checks'], can: ['A check list'], examples: ['Vet the 4 hottest coins'], version: '1.0', compat: 'Read by the minds', by: 'FEELESS', license: 'FEELESS', added: true, pickOnly: true, quality: 'Untested', record: { used: 0, won: 0, lost: 0 } };
  const live = { ...row, id: 'fl-funding', name: 'Funding Reader', kinds: ['pop'], pickOnly: false, fresh: ['BTC funding +0.01%/h'], source: 'Hyperliquid' };
  let state = { kits: [row, live], picks: [], mode: 'auto', max: 3, recs: { pow: [{ id: 'fl-coin-vet', why: ['Made for this proof: trading research'] }], pop: [{ id: 'fl-funding', why: ['Fresh numbers from Hyperliquid'] }] }, stacks: [{ id: 'coin-desk', name: 'Coin desk', kind: 'pow', picks: ['fl-coin-vet'], what: 'Vetting' }] };
  const fake = async (_, b) => { calls.push(b); if (b.op === 'kit_pick') state = { ...state, picks: b.text.split(','), mode: b.job }; return state; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<KitPick cat={{ id: 'c' }} work={fake} kind="pop" />); });
  expect(el.querySelector('[data-testid="kit-would"]').textContent).toContain('Funding Reader');
  await act(async () => { el.querySelector('[data-testid="kit-discover"]').click(); });
  expect(document.querySelector('[data-testid="kit-pick-fl-coin-vet"]')).toBeNull();   // the PoP door shows PoP kits first
  await act(async () => { document.querySelector('[data-testid="kit-for-pow"]').click(); });
  await act(async () => { document.querySelector('[data-testid="kit-info-fl-coin-vet"]').click(); });
  const look = document.querySelector('[data-testid="kit-detail"]');
  for (const word of ['Made for this proof', 'A check list', 'Vet the 4 hottest coins', 'No graded proof yet']) expect(look.textContent).toContain(word);
  expect(document.querySelector('[data-testid="kit-pick-only"]')).not.toBeNull();
  await act(async () => { document.querySelector('[data-testid="kit-back"]').click(); });
  await act(async () => { document.querySelector('[data-testid="kit-stack-coin-desk"]').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'kit_pick', text: 'fl-coin-vet', job: 'mine' });
  expect(el.querySelector('[data-testid="kit-on-fl-coin-vet"]')).not.toBeNull();
  await act(async () => { root.unmount(); }); el.remove();
});

test('🗂 PoEco asks 8 questions on first open, then the dash shows the server numbers and says it moves no money', async () => {
  window.matchMedia = window.matchMedia || (() => ({ matches: true, addEventListener() {}, removeEventListener() {} }));
  const { EcoFolder } = require('./EcoFolder');
  const view = { cash: 4200, net: 900, overdue: 1, overdueUsd: 1400, dueSoon: 0, dueSoonUsd: 0, owed: 2600, owedLate: 0, runway: 2.1, taxPct: 25, taxSetAside: 225, months: [], cats: [], count: 3, coach: [{ tab: 'bills', level: 'bad', text: '1 past due, $1,400.' }], pipeline: [], goals: [], openUsd: 0, income: 0, costs: 0, hasSamples: true };
  let desk = { setup: null, ledger: [], bills: [{ id: 'b1', name: 'Rent', amount: 1400, due: '2026-11-01', every: 'month', link: 'https://pay.example.com' }], people: [], invoices: [], goals: [] };
  const calls = []; const fake = async (_, b) => { calls.push(b); if (b.op === 'eco_d_setup') desk = { ...desk, setup: { wants: b.tools.wants, tone: b.tools.tone, tax: 25 } }; return { desk, view, today: '2026-11-06', poeFolders: [] }; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<EcoFolder cat={{ id: 'c' }} d={{}} setD={() => {}} work={fake} onCommand={() => {}} />); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const q = id => el.querySelector(`[data-testid="${id}"]`); const tap = async id => { await act(async () => { q(id).click(); await new Promise(r => setTimeout(r, 30)); }); };
  expect(q('eco-step').textContent).toBe('1 of 8');
  await tap('eco-q-who-freelance');
  expect(q('eco-step').textContent).toBe('2 of 8');
  await tap('eco-q-wants-coach');   // takes Coach off: the tab must go with it
  await tap('eco-q-next'); await tap('eco-q-next'); await tap('eco-q-next'); await tap('eco-q-next');
  expect(q('eco-step').textContent).toBe('6 of 8');
  await tap('eco-q-tax-25'); await tap('eco-q-goal-organized'); await tap('eco-q-next'); await tap('eco-q-tone-hard');
  expect(q('eco-step').textContent).toBe('8 of 8');
  await tap('eco-q-done');
  expect(calls.at(-1)).toMatchObject({ op: 'eco_d_setup', tools: { who: 'freelance', tone: 'hard', goal: 'organized' } }); expect(calls.at(-1).tools.wants).not.toContain('coach');
  expect(q('eco-start')).toBeNull(); expect(q('eco-tab-coach')).toBeNull(); expect(q('eco-tab-money')).not.toBeNull();
  expect(q('eco-cash').textContent).toBe('$4,200'); expect(q('eco-samples')).not.toBeNull();
  await tap('eco-tab-bills');
  expect(q('eco-bills-note').textContent).toContain('does not send the money'); expect(q('eco-pay-b1').getAttribute('href')).toBe('https://pay.example.com');
  await tap('eco-bill-paid-b1'); expect(calls.at(-1)).toMatchObject({ op: 'eco_d_bill_paid', text: 'b1' });
  await act(async () => { root.unmount(); }); el.remove();
});

test('🧰 each proof keeps its own 3 kits: the door picks which proof, and a pick is saved for that proof only', async () => {
  const { KitPick } = require('./FeaturesFolder');
  const rows = [{ id: 'a', name: 'A', what: 'x', kinds: ['pop'], added: true, site: 'https://a.example' }, { id: 'b', name: 'B', what: 'x', kinds: ['pob'], added: true, site: 'https://b.example' }];
  const calls = []; let by = { pow: { mode: 'auto', picks: [] }, pop: { mode: 'auto', picks: [] }, pob: { mode: 'mine', picks: ['b'] }, poc: { mode: 'auto', picks: [] }, pos: { mode: 'auto', picks: [] } };
  const fake = async (_, b) => { calls.push(b); if (b.op === 'kit_pick') by = { ...by, [b.to]: { mode: b.job, picks: b.text ? b.text.split(',') : [] } }; return { kits: rows, by, max: 3 }; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<KitPick cat={{ id: 'c' }} work={fake} />); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { q('kit-door-pob').click(); }); expect(q('kit-on-b')).not.toBeNull();
  await act(async () => { q('kit-door-pop').click(); }); expect(q('kit-on-b')).toBeNull(); expect(q('kit-auto')).not.toBeNull();
  await act(async () => { q('kit-discover').click(); });
  await act(async () => { document.querySelector('[data-testid="kit-pick-a"]').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'kit_pick', text: 'a', job: 'mine', to: 'pop' }); expect(by.pob.picks).toEqual(['b']); expect(q('kit-on-a')).not.toBeNull();
  await act(async () => { root.unmount(); }); el.remove();
});


test('⚔ Collective Debate: a proof goes on the table, its grades show, contents stay locked until a trade, and the switch is off by default', async () => {
  const { DebateFolder } = require('./DebateFolder');
  const take = { by: 'Bo', verdict: 'weak', grade: 40, why: 'Only one source', better: 'Read two sites', me: false };
  const theirs = { id: 'r2', by: 'Bo', kind: 'pob', title: 'Their pick', facts: '', mine: false, traded: false, excerpt: null, settled: null, seats: 3, takes: [] };
  const mineRow = { id: 'r1', by: 'Me', kind: 'pob', title: 'NBA night', facts: '', mine: true, traded: false, excerpt: '{"x":1}', settled: { grade: 40 }, seats: 3, takes: [take] };
  let v = { rows: [theirs], offers: [], board: [{ name: 'Bo', points: 6, takes: 1, me: false }], seat: { today: 0, perDay: 5 }, open: 1, settled: 0, allowed: false, canGrade: true };
  const calls = []; const fake = async (_, b) => { calls.push(b); if (b.op === 'debate_put') v = { ...v, rows: [mineRow, theirs], settled: 1 }; if (b.op === 'debate_allow') v = { ...v, allowed: b.on }; return v; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<DebateFolder cat={{ id: 'c' }} d={{ pobFolders: [{ id: 'f1', status: 'closed', topic: 'NBA night' }, { id: 'f2', status: 'open', topic: 'Not filed' }] }} work={fake} />); });
  await act(async () => { document.querySelector('[data-testid=dbt-tab-floor]')?.click(); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('dbt-allow').checked).toBe(false); expect(q('dbt-pick').textContent).toContain('NBA night'); expect(q('dbt-pick').textContent).not.toContain('Not filed');
  await act(async () => { const s = q('dbt-pick'); Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(s, 'f1'); s.dispatchEvent(new Event('change', { bubbles: true })); });
  await act(async () => { q('dbt-put').click(); await new Promise(r => setTimeout(r, 0)); });
  expect(calls.at(-1)).toMatchObject({ op: 'debate_put', job: 'pob', text: 'f1' }); expect(q('dbt-final-r1').textContent).toBe('40');
  await act(async () => { q('dbt-open-r1').click(); }); expect(q('dbt-row-r1').textContent).toContain('Read two sites');
  await act(async () => { q('dbt-open-r2').click(); }); expect(q('dbt-locked-r2')).not.toBeNull(); expect(q('dbt-give-r2').textContent).toContain('NBA night');
  await act(async () => { q('dbt-allow').click(); }); expect(calls.at(-1)).toMatchObject({ op: 'debate_allow', on: true });
  expect(q('dbt-board').textContent).toContain('Bo');
  await act(async () => { root.unmount(); }); el.remove();
});

test('🎬 the editor finds the right moment in a cut timeline, and the same words land where the render draws them', () => {
  const { clipAt, clipLen, totalLen } = require('../../lib/videoRender');
  const p = { clips: [{ id: 'a', in: 10, out: 12, speed: 1 }, { id: 'b', in: 0, out: 4, speed: 2 }] };
  expect(clipLen(p.clips[1])).toBe(2); expect(totalLen(p)).toBe(4);
  expect(clipAt(p, 1)).toMatchObject({ start: 0, src: 11 }); expect(clipAt(p, 3).clip.id).toBe('b'); expect(clipAt(p, 3).src).toBe(2); expect(clipAt(p, 4)).toBeNull();
});

test('🧊 a device with no 3D still opens the playground, says so plainly, and can still ask', async () => {
  jest.doMock('three/examples/jsm/controls/OrbitControls.js', () => ({ OrbitControls: class {} }), { virtual: true }); jest.doMock('three/examples/jsm/objects/GroundedSkybox.js', () => ({ GroundedSkybox: class {} }), { virtual: true }); jest.doMock('three/examples/jsm/controls/TransformControls.js', () => ({ TransformControls: class {} }), { virtual: true }); jest.doMock('three/examples/jsm/environments/RoomEnvironment.js', () => ({ RoomEnvironment: class {} }), { virtual: true }); jest.doMock('three/examples/jsm/loaders/GLTFLoader.js', () => ({ GLTFLoader: class {} }), { virtual: true }); jest.doMock('three/examples/jsm/loaders/RGBELoader.js', () => ({ RGBELoader: class {} }), { virtual: true });
  jest.doMock('three', () => ({ WebGLRenderer: class { constructor() { throw new Error('no WebGL'); } } }));
  const Playground3D = require('./Playground3D').default;
  const calls = []; const asset = { id: 'Camera_01', name: 'Camera 01', url: 'https://dl.polyhaven.org/x.gltf', files: {} }; const fake = async (_, b) => { calls.push(b); if (b.op === 'play3d_get') return { scene: null, canAsk: true, notes: ['moved Tower'] }; if (b.op === 'play3d_assets') return b.to ? { asset } : { rows: [{ id: 'Camera_01', name: 'Camera 01', kind: 'model', thumb: 'https://cdn.polyhaven.com/x.png' }], credit: 'Assets from Poly Haven (CC0)' }; return { ok: true }; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<Playground3D cat={{ id: 'c' }} work={fake} onBack={() => {}} />); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('p3d-nogl')).not.toBeNull(); expect(q('p3d-learned').textContent).toContain('moved Tower'); expect(q('p3d-shoot').disabled).toBe(true);
  expect(q('p3d-list').querySelectorAll('li').length).toBe(0);   // it starts blank
  await act(async () => { await new Promise(r => setTimeout(r, 300)); }); expect(q('p3d-credit').textContent).toContain('Poly Haven');
  await act(async () => { q('p3d-asset-Camera_01').click(); await new Promise(r => setTimeout(r, 0)); }); expect(q('p3d-list').textContent).toContain('Camera 01'); expect(q('p3d-height')).not.toBeNull();
  await act(async () => { q('p3d-add-box').click(); }); expect(q('p3d-mats')).not.toBeNull(); expect(q('p3d-undo').disabled).toBe(false);
  await act(async () => { q('p3d-mat-Glass').click(); }); expect(q('p3d-glass').value).toBe('1');
  await act(async () => { root.unmount(); }); el.remove();
});

test('🔔 only a newly filed proof raises an alert, and the first look only counts', () => {
  const { proofsDone } = require('./CatWorkbench');
  const d = { psFolders: [{ status: 'closed', topic: 'GLINT' }, { status: 'closed' }], powFolders: [{ status: 'open' }] };
  expect(proofsDone(null, d)).toEqual([]); expect(proofsDone({ psFolders: 2, powFolders: 0 }, d)).toEqual([]);
  expect(proofsDone({ psFolders: 1, powFolders: 0 }, d)).toEqual(['PoStatic: GLINT is done']);
});


test('💡 ideas are marked, and a refused one moves out of the new list', async () => {
  const { IdeasFolder } = require('./IdeasFolder');
  let rows = [{ id: 'a', topic: 'money', title: 'Stable floor', what: 'Keep it', why: 'Six of six', test: 'A week', by: 'OSSY', mark: 'new' }]; const calls = [];
  const fake = async (_, b) => { calls.push(b); if (b.op === 'ideas_mark') rows = rows.map(r => (r.id === b.text ? { ...r, mark: b.job } : r)); return { rows }; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<IdeasFolder cat={{ id: 'leader' }} work={fake} />); await new Promise(r => setTimeout(r, 0)); });
  const q = id => el.querySelector(`[data-testid="${id}"]`); expect(q('idea-a').textContent).toContain('Six of six');
  await act(async () => { q('idea-bad-a').click(); await new Promise(r => setTimeout(r, 0)); }); expect(calls.at(-1)).toMatchObject({ op: 'ideas_mark', text: 'a', job: 'bad' }); expect(q('idea-a')).toBeNull();
  await act(async () => { q('ideas-view-bad').click(); }); expect(q('idea-a')).not.toBeNull();
  await act(async () => { root.unmount(); }); el.remove();
});

test('Real proofs shows each type, says when one has none, and opens a real page in a sandbox', async () => {
  const card = { id: 'x1', print: 'ps1', kind: 'PoStatic', title: 'Narrative finder', tone: 'good', said: 'Marked right', rank: 'S', score: 280, top: 300, parts: [{ label: 'Result', value: 1, weight: 40 }, { label: 'Depth', value: null, weight: 10 }], facts: [['Version', 3]], page: true };
  const work = jest.fn(async (_, b) => (b.op === 'demo_gallery' ? { kinds: [{ kind: 'PoStatic', line: 'A page', cards: [card] }, { kind: 'PoW', line: 'Traded', cards: [] }] } : b.op === 'demo_open' ? { preview: '<b>real</b>' } : DATA));
  const { el } = await mount(work);
  await act(async () => { el.querySelector('[data-testid=fea-tab-work]').click(); }); await act(async () => { el.querySelector('[data-testid=fea-sub-proofs]').click(); });
  await act(async () => { await Promise.resolve(); });
  expect(el.textContent).toContain('Narrative finder'); expect(el.textContent).toContain('Your agents have not filed a PoW yet.');
  await act(async () => { el.querySelector('[data-testid=pgl-open-x1]').click(); });
  const f = el.querySelector('[data-testid=pgl-page-x1]');
  expect(f.getAttribute('sandbox')).toBe('allow-scripts'); expect(f.getAttribute('srcdoc')).toBe('<b>real</b>');
  await act(async () => { el.querySelector('[data-testid=pgl-show-PoW]').click(); });
  expect(el.textContent).not.toContain('Narrative finder');
});

test('a kit skill is a switch that tells the server, and what is off stays off', async () => {
  const { KitPick } = require('./FeaturesFolder');
  const row = { id: 'fl-coin-vet', name: 'Coin Vetter', what: 'x', kinds: ['pos'], by: 'FEELESS', cat: 'Research', task: 'T', skills: ['holders', 'rug checks'], added: true, quality: 'Untested', license: 'Private', compat: 'Read' };
  let state = { kits: [row], picks: ['fl-coin-vet'], mode: 'mine', max: 3, recs: {}, stacks: [], by: {}, skillsOff: {} }; const calls = [];
  const fake = async (_, b) => { calls.push(b); if (b.op === 'kit_skill') state = { ...state, skillsOff: { [b.text]: [b.job] } }; return state; };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<KitPick cat={{ id: 'c' }} work={fake} kind="pos" />); });
  await act(async () => { el.querySelector('[data-testid="kit-discover"]').click(); });
  const box = () => document.querySelector('[data-testid="kit-skill-fl-coin-vet-holders"]');
  expect(box().checked).toBe(true);
  await act(async () => { box().click(); });
  expect(calls.at(-1)).toEqual({ op: 'kit_skill', text: 'fl-coin-vet', job: 'holders', on: false }); expect(box().checked).toBe(false);
  await act(async () => { root.unmount(); }); el.remove();
});


test('Showcase: a reel. Nothing to operate, each capability plays how the agent does it, and each proof has its own', async () => {
  const { ProofDoors } = require('./ProofDoors');
  const calls = []; const work = async (_, b) => { calls.push(b); if (b.op === 'tools_show') return { models: 44000, hdris: 997, textures: 869, templates: [{ id: 'night-run', kind: 'game', name: 'Night Run', what: 'x', thumb: '/t.png', ask: 'A robot game', mood: 'Neon city', things: ['robot'] }, { id: 'silver-hour', kind: 'site', name: 'Silver Hour', what: 'y', thumb: '/u.png', ask: 'A camera page', mood: 'Noir', things: [] }, { id: 'long-road-film', kind: 'film', name: 'Film', what: 'z', thumb: '/v.png' }] }; if (b.op === 'kit_list') return { kits: [], picks: [], mode: 'mine', max: 3, recs: {}, stacks: [], by: {} }; if (b.op === 'tools_showcase') return { preview: `<b>${b.job}</b>` }; return {}; };
  const onCommand = jest.fn(); const onMake = jest.fn(); const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<ProofDoors cat={{ id: 'c' }} d={{}} work={work} onCommand={onCommand} onMake={onMake} />); });
  await act(async () => { await Promise.resolve(); }); await act(async () => { await Promise.resolve(); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('pdr-count').textContent).toContain('44K'); expect(q('pdr-piece-frame').getAttribute('sandbox')).toBe('allow-scripts'); expect(calls.at(-1)).toEqual({ op: 'tools_showcase', job: 'silver-hour' }); expect(q('pdr-cap-long-road-film')).toBeNull();
  expect(q('pdr-cap-night-run')).toBeNull();   // 🎮 owner 2026-11-10: no engine runner in the reel; the games are real games
  await act(async () => { q('pdr-cap-wick-breaker').click(); }); expect(q('pdr-piece').textContent).toContain('candle chart'); expect(q('pdr-piece-frame').getAttribute('src')).toBe('/showcase/pos/wick-breaker.html?demo=1'); expect(q('pdr-cap-mempool')).toBeTruthy();
  await act(async () => { q('pdr-cap-silver-hour').click(); }); expect(calls.at(-1)).toEqual({ op: 'tools_showcase', job: 'silver-hour' });
  await act(async () => { q('sst-go').click(); }); expect(onMake).toHaveBeenCalledWith('build', ['💻', 'Silver Hour', '', 'A camera page']);   // ▶ the page on the stage starts with its own ask
  const seen = {}; for (const [door, id] of [['pow', 'pdr-pow-replay'], ['pop', 'pdr-stash'], ['pob', 'pdr-live'], ['poc', 'pdr-viral']]) { await act(async () => { q(`pdr-${door}`).click(); }); expect(q(id)).toBeTruthy(); seen[door] = id; }
  expect(new Set(Object.values(seen)).size).toBe(4);   // no two proofs open on the same demo
  await act(async () => { q('pdr-cap-video').click(); }); expect(q('pdr-video').querySelector('video').getAttribute('src')).toContain('images-assets.nasa.gov');   // 🔥 PoC opens on the real viral clips first
  for (const [cap, id] of [['image', 'pdr-image'], ['replay', 'pdr-story-replay']]) { await act(async () => { q(`pdr-cap-${cap}`).click(); }); expect(q(id)).toBeTruthy(); }
  await act(async () => { q('pdr-cap-long-road-film').click(); }); expect(calls.at(-1)).toEqual({ op: 'tools_showcase', job: 'long-road-film' });
  await act(async () => { q('pdr-pob').click(); }); await act(async () => { q('pdr-cap-parlay').click(); }); expect(q('pdr-parlay')).toBeTruthy();
  await act(async () => { q('pdr-cap-replay').click(); }); expect(q('pdr-pick-replay')).toBeTruthy(); await act(async () => { q('pdr-cap-live').click(); }); expect(q('pdr-live').querySelector('video').getAttribute('src')).toBe('/showcase/pob/gridiron.mp4');
  await act(async () => { q('pdr-cap-stash').click(); }); expect(q('pdr-stash').textContent).toContain('line moves');
  await act(async () => { q('pdr-pop').click(); }); await act(async () => { q('sst-chip-1').click(); }); await act(async () => { q('sst-go').click(); }); expect(onCommand).toHaveBeenCalledWith('file a perp on SOL and show where 10x longs get liquidated');
  expect(el.querySelectorAll('input, textarea, select').length).toBe(1);   // the one thing to fill in is the ask under the preview
  el.remove();
});


test('the score is a real chart, and what is not known says so', async () => {
  const { ProofSeal } = require('./ProofVisuals');
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<ProofSeal rank="B" tone="good" parts={[{ label: 'Result', value: 1 }, { label: 'Depth', value: 0.5 }, { label: 'Earned', value: null }]} />); });
  const seal = el.querySelector('[data-testid=pvz-seal]'); expect(seal.getAttribute('aria-label')).toContain('Earned not known'); expect(seal.querySelector('b').textContent).toBe('B'); expect(seal.querySelector('.recharts-wrapper')).toBeTruthy();
});

test('every build tile is its own page: no GLINT, no repeat brief twice in a row, a white day/night dashboard tile', () => {
  const all = STARTERS.build.flatMap(s => [].concat(s[3]));
  expect(all.some(a => /GLINT/.test(a))).toBe(false);
  expect(new Set(all).size).toBe(all.length);
  const dash = STARTERS.build.find(s => s[1] === 'Clean dashboard');
  expect([].concat(dash[3]).every(a => /white/.test(a) && /Day \/ Night/.test(a))).toBe(true);
  STARTERS.build.forEach(([, t, , ask]) => { let last = ''; for (let i = 0; i < 12; i++) { const b = briefOf(t, ask); expect([].concat(ask)).toContain(b); if ([].concat(ask).length > 1) expect(b).not.toBe(last); last = b; } });
});

test('the PoStatic reel is a mix: kinds take turns, and every example page and thumb is on disk', () => {
  const { mixPieces, EXAMPLE_PIECES } = require('./ProofDoors');
  const rows = [...['a', 'b', 'c', 'd'].map(id => ({ id, kind: 'site' })), { id: 'g', kind: 'game' }, ...EXAMPLE_PIECES];
  expect(mixPieces(rows).slice(0, 5).map(r => r.kind)).toEqual(['site', 'game', 'dash', 'chart', 'tool']);
  const fs = require('fs'); const path = require('path');
  EXAMPLE_PIECES.forEach(p => { [p.src, p.thumb].forEach(f => expect(fs.existsSync(path.join(__dirname, '../../../public', f))).toBe(true)); });
});

test('the 3D code playground runs its code in a locked frame that loads only three.js, and every starter is three.js', () => {
  const { pageOf, STARTERS } = require('./Code3D');
  const p = pageOf("import * as THREE from 'three'; '</script>'");
  expect(p).toMatch(/Content-Security-Policy/); expect(p).toMatch(/three@0\.170\.0/); expect(p).not.toMatch(/<\/script>'/);
  STARTERS.forEach(([, , c]) => { expect(c).toMatch(/import \* as THREE from 'three'/); expect(c).toMatch(/setAnimationLoop/); });
});

test('🧮 before a send: its grade and why, how far the seats can move it, and what the amount does at this grade against flawless', async () => {
  const { ProofSendForm, gradeMath } = require('./ProofKit');
  const rules = { walletCapPct: 10, cutPerX: 1, score: { potUsd: 10000, top: 300 } };
  const a = gradeMath(rules, 129, 25, 10000, 54); const b = gradeMath(rules, 300, 25, 10000, 54);
  expect(a.x).toBeCloseTo(1.29); expect(a.limit).toBeCloseTo(32.25); expect(b.limit).toBe(75); expect(b.day).toBeGreaterThan(a.day);
  global.fetch = async u => ({ ok: true, json: async () => (String(u).includes('pool/rules') ? { rules } : String(u).includes('pool-rates') ? { hotPct: 54 } : {}) });
  const weights = { p1: { score: 129.3, top: 300, rank: 'C', parts: [{ key: 'unique', label: 'Unique', weight: 1, value: 0, note: '0% new, closest is #43' }, { key: 'build', label: 'Real build', weight: 1, value: 0.52, note: '32K page' }] } };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<ProofSendForm cat={{ id: 'c' }} work={async () => ({ weights })} f={{ id: 'p1' }} kind="PoStatic" coin={false} />); });
  for (let i = 0; i < 20 && !el.querySelector('[data-testid="grade-preview"]'); i += 1) await act(async () => { await new Promise(r => setTimeout(r, 20)); });
  const g = el.querySelector('[data-testid="grade-preview"]'); expect(g.textContent).toContain('129'); expect(g.textContent).toContain('0% new, closest is #43'); expect(g.textContent).toContain('lift it at most 24');
  expect(el.querySelector('[data-testid="grade-math"]').textContent).toContain('3.00x'); expect(el.querySelector('[data-testid="proof-meter"]')).toBeNull();
  act(() => root.unmount()); el.remove();
});

test('💰 the Money dash ranks the best by risk, so the thin coin pool that tops the board never leads the safe lanes', () => {
  const { bestByLane } = require('./OwnerFolders');
  const rows = [{ id: 'a', kind: 'pool', name: 'MEME-SOL', risk: 'both', tvl: 2e5, per1k24: 90, yearPct: 3000 }, { id: 'b', kind: 'lend', name: 'USDC on kamino', risk: 'none', tvl: 4e7, per1k24: 0.22, yearPct: 8 },
    { id: 'c', kind: 'stake', name: 'JitoSOL', risk: 'coin', tvl: 9e8, per1k24: 0.18, yearPct: 6.5 }, { id: 'd', kind: 'pool', name: 'SOL-USDC', risk: 'half', tvl: 3e7, per1k24: 1.4, yearPct: 51 }];
  const by = Object.fromEntries(bestByLane(rows).map(l => [l.k, l.best?.name]));
  expect(by).toEqual({ steady: 'USDC on kamino', stake: 'JitoSOL', deep: 'SOL-USDC', hot: 'MEME-SOL' });
});

test('🎭 each kind of proof can have its own prompt and personality; All stays the agent\'s own (AGT-3 / AGT-4)', async () => {
  const { Persona } = require('./FeaturesFolder');
  const calls = []; const work = jest.fn(async (_id, b) => { calls.push(b);
    if (b.op === 'persona') return { persona: { style: 'warm', heat: 3 }, styles: ['warm', 'analyst'], heat: { 3: 'steady' }, promptBy: {}, personaBy: {} };
    return { promptBy: { pob: b.tools.prompt }, personaBy: b.tools.persona ? { pob: b.tools.persona } : {} }; });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => root.render(<Persona cat={{ id: 'c' }} work={work} />)); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('voice-prompt')).toBeNull();   // All: today's single voice
  await act(async () => q('voice-kind-pob').click());
  const ta = q('voice-prompt'); await act(async () => { Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(ta, 'Bet only with a final score source'); ta.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => q('voice-save').click());
  expect(calls.at(-1)).toEqual({ op: 'kind_voice', text: 'pob', tools: { prompt: 'Bet only with a final score source' } });
  await act(async () => q('persona-analyst').click());
  expect(calls.at(-1)).toMatchObject({ op: 'kind_voice', text: 'pob', tools: { persona: { style: 'analyst' } } });
  expect(q('voice-kind-pob').textContent).toContain('●');
  act(() => root.unmount());
});


test('🎬 every proof type shows its real proofs graded by OSSY + G4, the kits it builds with, and PoEco draws its books', async () => {
  const { ProofDoors } = require('./ProofDoors');
  const show = { reviews: { pow: [{ id: 'w1', title: 'LEEROY', score: 30, verdict: 'fail', agree: true, by: { ossy: { score: 20, verdict: 'fail', checks: ['✓ read the pool', '✗ no holders read'], answeredBy: 'local · qwen' }, g4: { score: 40, verdict: 'fail', checks: ['✓ stop fits'] } } }], poe: [] },
    books: { topic: 'Q4 books', income: 13650, costs: 9220, net: 4430, margin: 32.5, taxSetAside: 1107.5, months: [{ month: '2026-09', income: 6200, costs: 4320, net: 1880 }, { month: '2026-10', income: 7450, costs: 4900, net: 2550 }] },
    fresh: { kits: [{ kit: 'echarts', pkg: 'echarts', v: '6', prev: '5' }] }, kits: [{ id: 'echarts', name: 'ECharts', what: 'Big charts', kinds: ['pow', 'pos'], license: 'Apache-2.0' }, { id: 'tabulator', name: 'Tabulator', what: 'Tables', kinds: ['pow'], license: 'MIT' }] };
  const work = async (_, b) => (b.op === 'showcase' ? show : b.op === 'tools_show' ? { templates: [] } : {});
  const onOpen = jest.fn(); const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<ProofDoors cat={{ id: 'c' }} d={{}} work={work} onCommand={() => {}} onMake={() => {}} onOpen={onOpen} kindFirst="pow" />); });
  await act(async () => { await Promise.resolve(); }); await act(async () => { await Promise.resolve(); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { q('pdr-cap-reviews').click(); });
  expect(q('pdr-reviews').textContent).toContain('LEEROY'); expect(q('pdr-reviews').textContent).toContain('✗ no holders read'); expect(q('pdr-reviews').textContent).toContain('OSSY');
  await act(async () => { q('pdr-cap-kits').click(); });
  expect(q('pdr-kit-echarts').textContent).toContain('5 → v6'); expect(q('pdr-kits').textContent).toContain('2 kits · 1 moved up');
  await act(async () => { q('pdr-poe').click(); }); expect(q('pdr-books').textContent).toContain('NET $4,430'); expect(q('pdr-books').querySelectorAll('li')).toHaveLength(2);
  await act(async () => { q('pdr-cap-reviews').click(); }); expect(q('pdr-no-reviews')).toBeTruthy();
  await act(async () => { q('sst-go').click(); }); expect(onOpen).toHaveBeenCalledWith('poe');
  el.remove();
});

test('📱 store check: runs the server check on the latest page, shows the ring, the verdict and every store rule with its fix', async () => {
  const { StoreCheck } = require('./FeaturesFolder');
  const calls = []; const check = { score: 88, state: 'review', fails: 0, warns: 2, line: 'Ready once you decide 2 flags', rows: [
    { id: 'icon', label: 'Has an app icon', rule: 'Apple 2.3.8 Icons', state: 'warn', fix: 'Add an app icon', detail: '' },
    { id: 'viewport', label: 'Fits a phone screen', rule: 'Apple 4.0 Design', state: 'pass', fix: '', detail: '' }] };
  const el = document.createElement('div'); document.body.appendChild(el); const root = require('react-dom/client').createRoot(el);
  await require('react').act(async () => { root.render(<StoreCheck cat={{ id: 'c' }} row={{ id: 'w1' }} doc={{ preview: '<p>x</p>', versions: 3, storeCheck: { score: 70, state: 'blocked', version: 2 } }} work={async (_, b) => { calls.push(b); return { check }; }} />); });
  const btn = el.querySelector('[data-testid="store-check"]');
  expect(btn.textContent).toContain('70*');                                  // last score, starred: the page changed since
  await require('react').act(async () => { btn.click(); });
  expect(calls).toEqual([{ op: 'store_check', job: 'w1' }]);
  const panel = document.querySelector('[data-testid="store-panel"]');   // portalled to the page so no window clips it
  expect(panel.textContent).toContain('Ready once you decide 2 flags'); expect(panel.textContent).toContain('Apple 2.3.8 Icons'); expect(panel.textContent).toContain('Add an app icon');
  expect(panel.querySelectorAll('li.is-warn')).toHaveLength(1);
});

test('🎬 its ad: the owner starts the run, sees each ad’s state, and a ready ad plays with an owner-only download', async () => {
  const { AdReel } = require('./ProofDoors');
  const rows = { pos: { name: 'PoStatic', ws: 'w1', state: 'done', video: true, cost: 0.2 }, pow: { name: 'PoW', ws: 'w2', state: 'building', video: false, cost: 0 } };
  const work = jest.fn(async (_, b) => ({ ads: { budget: 1.25, spent: 0.2, rows }, running: b.text === 'go' }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<AdReel k="pow" cat={{ id: 'c' }} work={work} ads={null} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { q('adr-make').click(); }); expect(work).toHaveBeenCalledWith('c', { op: 'show_ads', text: 'go' });
  expect(el.textContent).toContain('Its mind is building the page'); expect(el.textContent).toContain('$0.20 of $1.25'); expect(q('adr-make').disabled).toBe(true);
  const el2 = document.createElement('div'); document.body.appendChild(el2);
  await act(async () => { createRoot(el2).render(<AdReel k="pos" cat={{ id: 'c' }} work={work} ads={{ cat: 'happy', rows, spent: 0.2 }} />); });
  expect(el2.querySelector('[data-testid="adr-video"]').getAttribute('src')).toContain('/api/cats/happy/showad/pos?');
  expect(el2.querySelector('[data-testid="adr-dl"]').getAttribute('href')).toContain('&dl=1');
  await act(async () => { el2.querySelector('[data-testid="adr-redo"]').click(); }); expect(work).toHaveBeenCalledWith('c', { op: 'show_ads', text: 'redo:pos' });   // ↻ one bad ad, built again
});

test('🧪 Model Lab says plainly no model exists yet and keeps the owner’s name for it', async () => {
  const { ModelLab } = require('./ModelLab');
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<ModelLab />); });
  expect(el.textContent).toContain('No model is trained yet'); expect(el.querySelectorAll('[data-testid^="mlb-step-"]').length).toBe(7);
});

test('🧪 Model Lab live: the dataset per proof type, the owner grades an open proof, the minds to beat, and a clean export', async () => {
  const { ModelLab } = require('./ModelLab');
  const kind = (k, rows, won, lost, open) => ({ kind: k, rows, won, lost, flat: 0, open, graded: 0, pairs: Math.min(won, lost), rowsPct: rows / 1000, pairsPct: Math.min(won, lost) / 200 });
  const view = graded => ({ kinds: [kind('PoB', 71, 40, 31, 2), kind('PoW', 59, 30, 29, graded ? 0 : 1)], rows: 130 + graded, pairs: 60, graded, open: graded ? 2 : 3, snapshots: 41,
    minds: [{ model: 'hy4', calls: 60, failed: 3, failRate: 0.05, avgMs: 17000, usd: 0.17, local: false, kinds: { poc: 40, pos: 20 } }], spentUsd: 0.17,
    steps: { data: 'have', clean: 'ready', base: 'todo', sft: 'todo', pref: 'have', eval: 'have', serve: 'todo' }, goals: { rows: 1000, pairs: 200 },
    queue: graded ? [] : [{ key: 'k1', kind: 'PoW', title: 'Pump coin [wallet]', source: 'pump.fun', at: 1 }] });
  const sent = []; let graded = 0; const blobs = []; const urlWas = URL.createObjectURL;
  URL.createObjectURL = jest.fn(b => { blobs.push(b); return 'blob:x'; }); URL.revokeObjectURL = jest.fn();
  const call = jest.fn(async (path, opts) => { sent.push([path, opts?.body && JSON.parse(opts.body)]); if (path.endsWith('/grade')) { graded = 1; return view(1); } if (path.endsWith('/export')) return { rows: [{ kind: 'PoB' }, { kind: 'PoW' }], count: 2 }; return view(graded); });
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<ModelLab call={call} />); });
  expect(el.querySelector('[data-testid="mlb-kind-PoB"]').textContent).toContain('31 right-vs-wrong pairs');   // min(40 right, 31 wrong)
  expect(el.querySelectorAll('.mlb-steps li.is-have').length).toBe(4); expect(el.querySelector('[data-testid="mlb-mind-hy4"]').textContent).toContain('5% failed');
  await act(async () => { el.querySelector('[data-testid="mlb-bad-k1"]').click(); });
  expect(sent.find(x => x[0] === '/admin/model-lab/grade')[1]).toEqual({ key: 'k1', verdict: 'bad', note: '' }); expect(el.textContent).toContain('Nothing open to grade');
  await act(async () => { el.querySelector('[data-testid="mlb-export"]').click(); });
  expect(blobs).toHaveLength(1); expect(el.textContent).toContain('2 rows saved');
  URL.createObjectURL = urlWas; el.remove();
});
