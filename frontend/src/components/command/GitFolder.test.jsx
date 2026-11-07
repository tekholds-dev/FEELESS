import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { GitFolder } from './GitFolder';

const STATE = { files: [['README.md', 90], ['pages/launch-abc123.html', 2000], ['proofs/PoW/won/2026-11/blue-93519105.json', 3000], ['snapshots/rugcheck/a1.webp', 5000]], link: {}, tree: [], vault: {}, powShots: { f1: ['r0.jpg'] } };
const READ = {
  'proofs/PoW/won/2026-11/blue-93519105.json': { path: 'proofs/PoW/won/2026-11/blue-93519105.json', kind: 'data', data: { id: 'f1', sym: 'BLUE', pnlPct: 42, sol: 0.01, why: 'held the floor', coins: [{ sym: 'BLUE', liq: 1000, mc: 5000, ch: 4 }] } },
  'snapshots/rugcheck/a1.webp': { path: 'snapshots/rugcheck/a1.webp', kind: 'image', image: 'data:image/webp;base64,AAAA' },
  'pages/launch-abc123.html': { path: 'pages/launch-abc123.html', kind: 'page', preview: '<html>hi</html>' },
};
const work = async (_, b) => (b.op === 'git_state' ? STATE : b.op === 'git_read' ? READ[b.job] : { kits: [], picks: [], mode: 'auto' });
async function mount() { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(<GitFolder cat={{ id: 'c', handle: 'x' }} work={work} />); }); return el; }
const q = (el, t) => el.querySelector(`[data-testid="${t}"]`);

test('folders open in place, nested under their parent, like a real tree', async () => {
  const el = await mount();
  expect(el.querySelector('[role="tree"]')).not.toBeNull(); expect(q(el, 'git-dir-PoW')).toBeNull();
  await act(async () => { q(el, 'git-dir-proofs').click(); });
  expect(q(el, 'git-dir-proofs').closest('li').getAttribute('aria-expanded')).toBe('true');
  const kid = q(el, 'git-dir-PoW'); expect(q(el, 'git-dir-proofs').closest('li').contains(kid)).toBe(true); expect(kid.style.getPropertyValue('--d')).toBe('1');
  await act(async () => { q(el, 'git-dir-proofs').click(); }); expect(q(el, 'git-dir-PoW')).toBeNull();
});

test('a proof opens as a page of its data, a snapshot as a picture, a built page in a locked sandbox, never as code', async () => {
  const el = await mount();
  for (const d of ['proofs', 'PoW', 'won', '2026-11']) { await act(async () => { q(el, `git-dir-${d}`).click(); }); }
  await act(async () => { q(el, 'git-file-blue-93519105.json').click(); });
  const p = q(el, 'git-proof'); expect(p.textContent).toContain('$BLUE'); expect(p.textContent).toContain('+42%'); expect(p.textContent).toContain('held the floor'); expect(p.querySelector('img').getAttribute('src')).toContain('/powshot/f1/r0.jpg');
  expect(el.querySelector('pre')).toBeNull();
  await act(async () => { q(el, 'git-dir-snapshots').click(); }); await act(async () => { q(el, 'git-dir-rugcheck').click(); }); await act(async () => { q(el, 'git-file-a1.webp').click(); });
  expect(q(el, 'git-image').getAttribute('src')).toContain('data:image/webp');
  await act(async () => { q(el, 'git-dir-pages').click(); }); await act(async () => { q(el, 'git-file-launch-abc123.html').click(); });
  const f = q(el, 'git-page'); expect(f.getAttribute('sandbox')).toBe('allow-scripts');
});

const SORTED = { ...STATE, sealed: true, sort: { on: true, counts: { good: 0, bad: 0, disputed: 0, trash_ask: 1, unsorted: 3 }, items: { 'snapshots/rugcheck/a1.webp': { status: 'trash_ask', votes: { ossy: { verdict: 'trash', why: 'bot check' }, g4: { verdict: 'trash', why: 'blank' } } } } } };
test('the owner rules on what the minds want gone, adds notes and marks, and nothing is deleted', async () => {
  const calls = [];
  const fake = async (_, b) => { calls.push(b); if (b.op === 'git_state') return SORTED; if (b.op === 'git_read') return READ[b.job]; if (b.op === 'sort_set') return { item: { ...SORTED.sort.items['snapshots/rugcheck/a1.webp'], ...b.tools } }; if (b.op === 'sort_trash') return { item: { status: b.on ? 'trash' : 'bad', by: 'owner' } }; return { kits: [], picks: [], mode: 'auto' }; };
  const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(<GitFolder cat={{ id: 'leader' }} work={fake} scope="collective" />); });
  await act(async () => { q(el, 'sort-tab-trash').click(); }); await act(async () => { q(el, 'git-dir-snapshots').click(); }); await act(async () => { q(el, 'git-dir-rugcheck').click(); }); await act(async () => { q(el, 'git-file-a1.webp').click(); });
  await act(async () => { q(el, 'sort-more').click(); });
  expect(q(el, 'sort-vote-ossy').textContent).toContain('bot check'); expect(q(el, 'sort-ask')).not.toBeNull();
  await act(async () => { q(el, 'sort-use-pow').click(); }); expect(calls.at(-1)).toMatchObject({ op: 'sort_set', job: 'snapshots/rugcheck/a1.webp', tools: { use: ['pow'] }, to: 'collective' });
  await act(async () => { q(el, 'sort-approve').click(); }); expect(calls.at(-1)).toMatchObject({ op: 'sort_trash', on: true });
  await act(async () => { q(el, 'sort-tab-all').click(); }); expect(q(el, 'git-file-a1.webp')).toBeNull();   // approved: gone from the lists
  await act(async () => { q(el, 'sort-tab-trash').click(); }); expect(q(el, 'git-dir-snapshots')).not.toBeNull();   // still there
  expect(q(el, 'trash-desk')).not.toBeNull(); for (const d of ['snapshots', 'rugcheck']) { if (!q(el, `git-dir-${d === 'snapshots' ? 'rugcheck' : 'never'}`)) await act(async () => { q(el, `git-dir-${d}`).click(); }); } await act(async () => { q(el, 'git-file-a1.webp').click(); }); expect(q(el, 'sort-mark')).not.toBeNull(); expect(calls.some(c => /delete|drop/.test(c.op))).toBe(false);
});

test('the minds said bad: one tap trashes it, and a folder has its own options with bulk approve', async () => {
  const files = [['snapshots/x/a.webp', 100], ['snapshots/x/b.webp', 100], ['snapshots/x/c.webp', 100]];
  const items = { 'snapshots/x/a.webp': { status: 'bad', by: 'minds', votes: { ossy: { verdict: 'bad', why: '404' }, g4: { verdict: 'bad', why: '404' } } }, 'snapshots/x/b.webp': { status: 'trash_ask', by: 'minds' } };
  const work = jest.fn(async (id, b) => { if (b.op === 'git_state') return { files, link: { full: 'o/r' }, sealed: true, sort: { on: true, items, counts: {} }, tree: [] }; if (b.op === 'git_read') return { path: b.job, kind: 'text', text: 'hello world' }; if (b.op === 'sort_bulk') return { changed: 1, items: {} }; return { item: { status: b.tools?.status, by: 'owner', marks: b.tools?.marks } }; });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<GitFolder cat={{ id: 'leader' }} work={work} scope="collective" />); }); await act(async () => {});
  const q = t => el.querySelector(`[data-testid="${t}"]`); const click = n => act(async () => { n.click(); });
  await click(q('git-dir-snapshots')); await click(q('git-dir-x')); await click(q('git-file-a.webp')); await act(async () => {});
  expect(q('sort-minds').textContent).toContain('The minds say bad');
  await click(q('sort-minds-trash')); expect(work.mock.calls.at(-1)[1]).toMatchObject({ op: 'sort_set', job: 'snapshots/x/a.webp', tools: { status: 'trash' } });
  await click(q('git-dirset-x')); expect(q('git-folder-view').textContent).toContain('3 files'); await click(q('sort-bulk-trash_ask'));
  expect(work.mock.calls.at(-1)[1]).toMatchObject({ op: 'sort_bulk', tools: { paths: ['snapshots/x/b.webp'], status: 'trash' } });
  await act(async () => root.unmount());
});
test('a user can hook up their own project, and the token never shows again', async () => {
  const work = jest.fn(async (id, b) => { if (b.op === 'project_link') work.linked = true; return b.op === 'git_state' ? { files: [], link: {}, project: work.linked ? { full: 'me/app', files: 3, url: 'u', branch: 'main' } : null } : { project: {} }; });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<GitFolder cat={{ id: 'c' }} work={work} />); }); await act(async () => {});
  const q = t => el.querySelector(`[data-testid="${t}"]`); const type = (n, v) => act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(n, v); n.dispatchEvent(new Event('input', { bubbles: true })); });
  await type(q('git-project-repo'), 'me/app'); await type(q('git-project-token'), 'github_pat_xxx');
  await act(async () => { q('git-project-go').click(); }); await act(async () => {});
  expect(work.mock.calls.find(c => c[1].op === 'project_link')[1]).toMatchObject({ job: 'me/app', text: 'github_pat_xxx' });
  expect(q('git-project').textContent).toContain('me/app'); expect(el.innerHTML).not.toContain('github_pat_xxx');
  await act(async () => root.unmount());
});

test('the minds mark a picture: each mark has its window, ticks choose, approve reads the file again', async () => {
  const files = [['snapshots/x/a.webp', 100], ['snapshots/x/b.webp', 100]]; const items = { 'snapshots/x/a.webp': { status: 'bad', by: 'minds' } };
  const work = jest.fn(async (id, b) => { if (b.op === 'git_state') return { files, link: { full: 'o/r' }, sealed: true, sort: { on: true, items, counts: {} }, tree: [] }; if (b.op === 'git_read') return { path: b.job, kind: 'image', image: 'data:image/png;base64,AA', proposed: [{ id: 0, x: 0.1, y: 0.1, w: 0.2, h: 0.2, label: 'Cap', why: 'Read the cap', grade: 80, by: ['ossy', 'g4'] }, { id: 1, x: 0.5, y: 0.5, w: 0.2, h: 0.2, label: 'Noise', grade: 10, by: ['g4'] }] }; if (b.op === 'sort_bulk') return { changed: 2, items: { 'snapshots/x/a.webp': { status: 'trash', by: 'owner' } } }; return { item: { status: 'good', by: 'owner' } }; });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<GitFolder cat={{ id: 'leader' }} work={work} scope="collective" />); }); await act(async () => {});
  const q = t => el.querySelector(`[data-testid="${t}"]`); const click = n => act(async () => { n.click(); });
  await click(q('git-dir-snapshots')); await click(q('git-dir-x')); await click(q('git-file-a.webp')); await act(async () => {});
  expect(q('mark-win-p0').textContent).toContain('OSSY + G4'); expect(q('mark-win-p0').textContent).toContain('Read the cap'); expect(q('mark-approve').textContent).toContain('2');
  await click(q('mark-tick-1')); expect(q('mark-approve').textContent).toContain('1');
  await click(q('mark-approve')); expect(work.mock.calls.find(c => c[1].op === 'sort_approve')[1]).toMatchObject({ job: 'snapshots/x/a.webp', tools: { keep: [0] } }); await act(async () => {});
  await click(q('sort-select')); await click(q('sort-pick-all')); expect(q('sort-bulkbar').textContent).toContain('2'); await click(q('sort-picked-trash'));
  expect(work.mock.calls.find(c => c[1].op === 'sort_bulk')[1].tools).toEqual({ paths: ['snapshots/x/a.webp', 'snapshots/x/b.webp'], patch: { status: 'trash' } });
  await act(async () => root.unmount());
});

test('a PoStatic proof, whose plan is one sentence, opens instead of crashing the page', async () => {
  const { FileView } = require('./GitFolder');
  const el = document.createElement('div'); document.body.appendChild(el); const root = require('react-dom/client').createRoot(el);
  await act(async () => { root.render(<FileView doc={{ kind: 'data', path: 'proofs/PoS/right/a.json', data: { topic: 'A page', plan: 'Make it fast', steps: ['Read', 'Build'] } }} shots={[]} />); });
  expect(el.textContent).toContain('Make it fast'); expect(el.textContent).toContain('Build');
  await act(async () => { root.render(<FileView doc={{ kind: 'data', path: 'x.json', data: { plan: { nested: true } } }} shots={[]} />); }); expect(el.querySelector('[data-testid="git-proof"]')).not.toBeNull();
  await act(async () => { root.unmount(); }); el.remove();
});

test('the Trash has two clear piles, counts down, brings back, and asks before a delete', async () => {
  const now = Date.now() / 1000; const A = 'snapshots/x/a.webp'; const B = 'snapshots/x/b.webp'; const C = 'snapshots/x/c.webp';
  const state = { files: [[A, 10], [B, 10], [C, 10]], tree: {}, sort: { on: false, items: { [A]: { status: 'trash_ask' }, [B]: { status: 'trash', by: 'owner', trashedAt: now - 2 * 86400 }, [C]: { status: 'trash', by: 'owner', trashedAt: now - 3600 } } }, vault: {}, link: null, waiting: 0, total: 3, counts: {} };
  const calls = []; const fake = async (_, b) => { calls.push(b); if (b.op === 'git_state') return state; if (b.op === 'sort_delete') return { deleted: b.tools.paths, items: { [A]: state.sort.items[A], [C]: state.sort.items[C] } }; if (b.op === 'sort_set') return { item: {} }; if (b.op === 'sort_trash') return { item: { status: b.on ? 'trash' : 'bad', by: 'owner', trashedAt: now } }; return {}; };
  const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(<GitFolder cat={{ id: 'leader' }} work={fake} scope="collective" />); });
  await act(async () => { q(el, 'sort-tab-trash').click(); });
  expect(q(el, 'trash-asked').textContent).toContain('Nothing happens'); expect(q(el, `trash-left-${B}`).textContent).toBe('5d left'); expect(q(el, `trash-left-${C}`).textContent).toBe('7d left');
  await act(async () => { q(el, `trash-delete-${B}`).click(); }); expect(calls.some(c => c.op === 'sort_delete')).toBe(false); expect(q(el, `trash-delete-${B}`).textContent).toBe('Delete for good?');
  await act(async () => { q(el, `trash-delete-${B}`).click(); }); expect(calls.at(-1)).toMatchObject({ op: 'sort_delete', tools: { paths: [B] } }); expect(q(el, `trash-left-${B}`)).toBeNull();
  await act(async () => { q(el, `trash-restore-${C}`).click(); }); expect(calls.at(-1)).toMatchObject({ op: 'sort_set', job: C, tools: { status: 'none' } });
  await act(async () => { q(el, `trash-move-${A}`).click(); }); expect(calls.at(-1)).toMatchObject({ op: 'sort_trash', job: A, on: true });
  el.remove();
});

test('the token tutorial walks three steps and connects for real', async () => {
  document.body.innerHTML = ''; const { GitTour } = require('./GitFolder'); const onLink = jest.fn(async () => {}); const onClose = jest.fn(); const el = document.createElement('div'); document.body.append(el); const root = createRoot(el);
  await act(async () => { root.render(<GitTour onClose={onClose} onLink={onLink} />); });
  const q = t => document.body.querySelector(`[data-testid="${t}"]`);
  expect(q('gtt-open').getAttribute('href')).toContain('contents=write'); await act(async () => { q('gtt-next').click(); }); expect(document.body.textContent).toContain('Only select repositories'); await act(async () => { q('gtt-next').click(); });
  const type = (n, v) => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(n, v); n.dispatchEvent(new Event('input', { bubbles: true })); };
  await act(async () => { type(q('gtt-repo'), 'me/app'); }); await act(async () => { type(q('gtt-token'), 't0ken'); }); expect(q('gtt-link').disabled).toBe(false); await act(async () => { q('gtt-link').closest('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); });
  expect(onLink).toHaveBeenCalledWith('me/app', 't0ken'); expect(onClose).toHaveBeenCalled(); await act(async () => { root.unmount(); });
});

test('🧬 each proof type shows what it got right and wrong', () => {
  const { wireRows } = require('./GitFolder');
  const rows = wireRows({ powFolders: [{ status: 'closed', pnlPct: 3 }, { status: 'closed', pnlPct: -2 }, { status: 'open' }], psFolders: [{ status: 'closed', graded: 'right' }, { status: 'closed' }], popFolders: [{ status: 'closed', noTrade: true }] });
  expect(rows[0]).toMatchObject({ label: 'PoW', total: 2, good: 1, bad: 1, open: 0 }); expect(rows[4]).toMatchObject({ label: 'PoStatic', good: 1, open: 1 }); expect(rows[1]).toMatchObject({ good: 0, bad: 0, open: 1 });
});


test('the Git chat asks its agent and shows the answer, and a failed ask keeps the words', async () => {
  const sent = []; let fail = false;
  const fake = jest.fn(async (_, b) => { if (b.op === 'git_chat') { sent.push(b); if (fail) throw new Error('No model'); return { said: 'Two proof folders.', usd: 0.0012 }; } return { files: [['a.json', 3]], link: {} }; });
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<GitFolder cat={{ id: 'c' }} work={fake} />); });
  await act(async () => { el.querySelector('[data-testid=git-chat-open]').click(); });
  await act(async () => { el.querySelector('[data-testid=git-chat-ask]').click(); });
  expect(sent[0].text).toBe('What is in here?'); expect(el.textContent).toContain('Two proof folders.'); expect(el.textContent).toContain('$0.0012');
  fail = true;
  const box = el.querySelector('[data-testid=git-chat-text]');
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(box, 'why?'); box.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('form.ckit-composer').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); });
  expect(el.textContent).toContain('No model'); expect(el.querySelector('[data-testid=git-chat-text]').value).toBe('why?');
  el.remove();
});
