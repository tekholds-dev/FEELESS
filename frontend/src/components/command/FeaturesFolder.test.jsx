import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FeaturesFolder, FEATURES, ProofDesk } from './FeaturesFolder';
import { nextMove } from './CollectiveTop';

jest.mock('../terminal/TradeTape', () => ({ TradeTape: () => <i data-testid="tape" /> }));
jest.mock('./FeeCatShell', () => ({ goTo: jest.fn() }));
const DATA = { workspaces: [], memory: { notes: 3, mindNotes: 1, recent: ['a note'], personal: '' }, print: { level: 40, proofs: 6, traits: [{ t: 'source pump', score: 2, n: 3, won: 3 }] }, edge: [{ id: 'x', cat: 'safety', t: 'Mint on', read: 'r', means: 'm', do: 'd', stop: 's' }], edgeCats: { safety: 'Rugs' }, indicators: [{ id: 'rsi', t: 'RSI' }], pocFolders: [] };
async function mount(work, d = { setup: { use: 'code' } }) { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(<FeaturesFolder cat={{ id: 'c' }} d={d} work={work} onCommand={() => {}} />); }); await act(async () => { await Promise.resolve(); }); await act(async () => { el.querySelector('[data-testid="fea-tab-features"]').click(); }); return { el, q: id => el.querySelector(`[data-testid="${id}"]`) }; }
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
  jest.doMock('three/examples/jsm/controls/OrbitControls.js', () => ({ OrbitControls: class {} }), { virtual: true }); jest.doMock('three/examples/jsm/controls/TransformControls.js', () => ({ TransformControls: class {} }), { virtual: true }); jest.doMock('three/examples/jsm/environments/RoomEnvironment.js', () => ({ RoomEnvironment: class {} }), { virtual: true }); jest.doMock('three/examples/jsm/loaders/GLTFLoader.js', () => ({ GLTFLoader: class {} }), { virtual: true }); jest.doMock('three/examples/jsm/loaders/RGBELoader.js', () => ({ RGBELoader: class {} }), { virtual: true });
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
  await act(async () => { el.querySelector('[data-testid=fea-tab-real]').click(); });
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


test('Proofs: a door per proof, its real tools, real numbers and a start that works', async () => {
  const { ProofDoors } = require('./ProofDoors');
  const calls = []; const kit = { id: 'fl-funding', name: 'Funding Reader', what: 'x', by: 'FEELESS', kinds: ['pop'], fresh: ['BTC funding 0.01%'], source: 'Hyperliquid', skills: ['funding'], quality: 'Untested' };
  const work = async (_, b) => { calls.push(b); if (b.op === 'tools_show') return { models: 44000, hdris: 997, textures: 869 }; if (b.op === 'kit_list') return { kits: [kit], picks: [], mode: 'mine', max: 3, recs: {}, stacks: [], by: {} }; if (b.op === 'demo_gallery') return { kinds: [] }; if (b.op === 'tools_demo') return { preview: '<b>world</b>' }; return {}; };
  const onCommand = jest.fn(); const onMake = jest.fn(); const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<ProofDoors cat={{ id: 'c' }} d={{ popFolders: [{}] }} work={work} onCommand={onCommand} onMake={onMake} />); });
  await act(async () => { await Promise.resolve(); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('ptl-n-MODELS').textContent).toBe('44K'); expect(q('ptl-world-frame').getAttribute('sandbox')).toBe('allow-scripts');
  await act(async () => { q('ptl-w-aurora').click(); }); expect(calls.at(-1)).toEqual({ op: 'tools_demo', tools: { world: 'aurora', hero: 'star' } });
  await act(async () => { q('ptl-go').click(); }); expect(onMake).toHaveBeenCalledWith('build');
  await act(async () => { q('ptl-pop').click(); });
  expect(q('pvz-empty')).toBeTruthy(); expect(q('ptl-no-proof').textContent).toContain('PoP'); expect(el.textContent).not.toContain('Research');
  await act(async () => { q('ptl-go').click(); }); expect(onCommand).toHaveBeenCalledWith('file a perp');
  el.remove();
});


test('each proof has its own demo, drawn from its own real data', async () => {
  const { ContentCut, FundingSea, ProofSeal, ScoreBoard, TradeFlight } = require('./ProofVisuals');
  const paint = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); return el; };
  const sea = await paint(<FundingSea kits={[{ fresh: ['PUMP funding -0.0079%/h (-69%/yr pace), open interest $69.9M', 'BTC mark $75,713: 3x long $51,422 / short $100,004, 10x long $69,088 / short $82,338'] }]} />);
  expect(sea.querySelector('.pvz-bubbles .is-short b').textContent).toBe('PUMP'); expect(sea.querySelector('.pvz-ladder .is-mark').textContent).toContain('BTC');
  const board = await paint(<ScoreBoard kits={[{ fresh: ['NFL JAX 33 at BAL 10, Final', 'NBA DEN 0 at IND 0, 11/7 - 5:00 PM EST', 'not a game'] }]} />);
  expect(board.querySelectorAll('article').length).toBe(2); expect(board.querySelector('.is-final').textContent).toContain('33'); expect(board.textContent).toContain('5:00 PM');
  const cut = await paint(<ContentCut kits={[{ id: 'fl-trend', fresh: ['Hacker News: A new story', 'Wikipedia: Another'] }, { id: 'x', fresh: ['NBA DEN 0 at IND 0, 11/7'] }]} />);
  expect(cut.textContent).toContain('A new story'); expect(cut.textContent).not.toContain('NBA');
  await act(async () => { cut.querySelector('[data-testid=pvz-shot-1]').click(); }); expect(cut.querySelector('.pvz-reel b').textContent).toBe('Another');
  const fly = await paint(<TradeFlight catId="c" t={{ id: 'p', sym: 'WIF', pnl: 12, entry: 1, tp: 20, sl: 6, line: [1, 1.1, 1.12], files: [{ file: 'a.jpg', site: 'x.com' }] }} />);
  expect(fly.textContent).toContain('$WIF'); expect(fly.querySelector('.pvz-flight.is-won')).toBeTruthy(); expect(fly.querySelector('.pvz-film img').alt).toBe('x.com');
  expect((await paint(<TradeFlight t={null} />)).querySelector('[data-testid=pvz-empty]')).toBeTruthy();
  const seal = await paint(<ProofSeal rank="B" score={200} tone="good" parts={[{ label: 'Result', value: 1 }, { label: 'Depth', value: 0.5 }, { label: 'Earned', value: null }]} />);
  expect(seal.querySelector('svg').getAttribute('aria-label')).toContain('Earned not known'); expect(seal.querySelectorAll('.pvz-dot').length).toBe(2);
});
