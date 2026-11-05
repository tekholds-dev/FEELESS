import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FeaturesFolder, FEATURES } from './FeaturesFolder';
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
