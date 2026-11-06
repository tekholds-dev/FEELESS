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
  expect(q(el, 'sort-vote-ossy').textContent).toContain('bot check'); expect(q(el, 'sort-ask')).not.toBeNull();
  await act(async () => { q(el, 'sort-use-pow').click(); }); expect(calls.at(-1)).toMatchObject({ op: 'sort_set', job: 'snapshots/rugcheck/a1.webp', tools: { use: ['pow'] }, to: 'collective' });
  await act(async () => { q(el, 'sort-approve').click(); }); expect(calls.at(-1)).toMatchObject({ op: 'sort_trash', on: true });
  await act(async () => { q(el, 'sort-tab-all').click(); }); expect(q(el, 'git-file-a1.webp')).toBeNull();   // approved: gone from the lists
  await act(async () => { q(el, 'sort-tab-trash').click(); }); expect(q(el, 'git-dir-snapshots')).not.toBeNull();   // still there
  expect(q(el, 'sort-mark')).not.toBeNull(); expect(calls.some(c => /delete|drop/.test(c.op))).toBe(false);
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
