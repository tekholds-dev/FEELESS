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
