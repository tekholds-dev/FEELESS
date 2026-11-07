import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FeaturesFolder, FEATURES, ProofDesk } from './FeaturesFolder';
import { nextMove } from './CollectiveTop';

jest.mock('../terminal/TradeTape', () => ({ TradeTape: () => <i data-testid="tape" /> }));
jest.mock('./FeeCatShell', () => ({ goTo: jest.fn() }));
const DATA = { workspaces: [], memory: { notes: 3, mindNotes: 1, recent: ['a note'], personal: '' }, print: { level: 40, proofs: 6, traits: [{ t: 'source pump', score: 2, n: 3, won: 3 }] }, edge: [{ id: 'x', cat: 'safety', t: 'Mint on', read: 'r', means: 'm', do: 'd', stop: 's' }], edgeCats: { safety: 'Rugs' }, indicators: [{ id: 'rsi', t: 'RSI' }], pocFolders: [] };
async function mount(work, d = { setup: { use: 'code' } }) { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(<FeaturesFolder cat={{ id: 'c' }} d={d} work={work} onCommand={() => {}} />); }); await act(async () => { await Promise.resolve(); }); return { el, q: id => el.querySelector(`[data-testid="${id}"]`) }; }
const type = async (n, v) => { await act(async () => { const set = Object.getOwnPropertyDescriptor(n.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype, 'value').set; set.call(n, v); n.dispatchEvent(new Event('input', { bubbles: true })); }); };

test('this agent’s use comes first, every feature has a demo marked as an example and a create button', async () => {
  const { el, q } = await mount(jest.fn(async () => DATA));
  expect(el.querySelector('.fea-cat b').textContent).toBe('Build'); expect(q('fea-demo').textContent).toContain('EXAMPLE');
  for (const k of Object.keys(FEATURES)) { await act(async () => { q(`fea-${k}`).click(); }); expect(q('fea-create').textContent).toContain(FEATURES[k].t); expect(q('fea-demo')).not.toBeNull(); }
});
test('create makes a real folder and opens it: blank screen, a mind picker, send goes to the owner door', async () => {
  const doc = { id: 'w1', kind: 'build', name: 'Site', messages: [], versions: 0, code: '', preview: '', busy: null };
  const work = jest.fn(async (_, b) => (b.op === 'feature_create' ? { folder: { id: 'w1', kind: 'build', name: 'Site' }, workspaces: [{ id: 'w1', kind: 'build', name: 'Site' }] } : b.op === 'ws_open' ? { doc } : b.op === 'ws_build' ? { doc: { ...doc, messages: [{ by: 'you', text: b.text }], busy: null } } : DATA));
  const { el, q } = await mount(work);
  await act(async () => { q('fea-create').click(); }); await act(async () => { await Promise.resolve(); });
  expect(el.textContent).toContain('A blank screen'); expect(q('ws-mark').disabled).toBe(true);
  await act(async () => { q('ws-to-a').click(); }); await type(q('ws-input'), 'make a timer');
  await act(async () => { q('ws-send').click(); });
  expect(work).toHaveBeenCalledWith('c', expect.objectContaining({ op: 'ws_build', job: 'w1', text: 'make a timer', to: 'a' }));
});
test('a built page runs only in a sandbox with no same-origin, and code and static switch', async () => {
  const doc = { id: 'w1', kind: 'build', name: 'Site', messages: [], versions: 1, by: 'Mind A', code: '<b>hi</b>', preview: '<b>hi</b>', busy: null };
  const work = jest.fn(async (_, b) => (b.op === 'ws_open' ? { doc } : { ...DATA, workspaces: [{ id: 'w1', kind: 'build', name: 'Site' }] }));
  const { q } = await mount(work);
  await act(async () => { q('fea-tab-mine').click(); }); await act(async () => { q('ws-w1').click(); }); await act(async () => { await Promise.resolve(); });
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
  await act(async () => { [...el.querySelectorAll('[role="tab"]')].find(b => b.textContent.includes('Your folders')).click(); });
  await act(async () => { el.querySelector('[data-testid="ws-w1"]').click(); });
  expect(el.querySelector('[data-testid="ws-steps"] .is-now').textContent).toContain('You approve');
  expect(el.querySelector('[data-testid="ws-plan"]').textContent).toContain('A desk'); expect(el.querySelector('[data-testid="ws-plan"]').textContent).toContain('Blocked');
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
});

test('a stopped PoStatic says why, Finish runs the same ask, and Keep stops at the last page', async () => {
  const doc = { id: 'w1', kind: 'build', name: 'B', stage: 'review', busy: null, pending: true, versions: 5, cost: 0.02, messages: [{ by: 'you', text: 'fix the buttons' }, { by: 'Mind A', text: 'Nothing changed' }], cfg: { research: true, suggest: true, review: true, depth: 'quick' }, unfinished: { ask: 'fix the buttons', why: 'Its changes did not match the page.' } };
  const work = jest.fn(async (id, b) => (b.op === 'ws_open' ? { doc } : b.op === 'features' ? { workspaces: [{ id: 'w1', kind: 'build', name: 'B' }] } : b.op === 'ws_keep' ? { doc: { ...doc, unfinished: null, stage: 'filed', pending: false } } : b.op === 'ws_build' ? { doc: { ...doc, unfinished: null, busy: { stage: 'build', at: 1 } } } : {}));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<FeaturesFolder cat={{ id: 'c' }} d={{}} work={work} />); });
  await act(async () => { [...el.querySelectorAll('[role="tab"]')].find(b => b.textContent.includes('Your folders')).click(); });
  await act(async () => { el.querySelector('[data-testid="ws-w1"]').click(); });
  const q = t => el.querySelector(`[data-testid="${t}"]`);
  expect(q('ws-finish').textContent).toContain('did not match'); expect(q('ws-finish-keep').textContent).toContain('Keep page 5'); expect(el.querySelector('[data-testid="ws-steps"] .is-stopped').textContent).toContain('other mind');
  await act(async () => { q('ws-finish-go').click(); });
  expect(work).toHaveBeenCalledWith('c', { op: 'ws_build', job: 'w1', text: 'fix the buttons', finish: true, to: 'both' }); expect(q('ws-finish')).toBeNull();
  await act(async () => root.unmount());
});

