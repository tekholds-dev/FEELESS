import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CommandCenter } from './CommandCenter';

test('the command center shows only what the service reports: who works, who waits on you, who answered and what it cost', async () => {
  global.fetch = jest.fn(u => Promise.resolve({ ok: true, json: () => Promise.resolve(String(u).includes('/brief/proofs') ? { rows: [{ kind: 'pob', avgScore: 46, rightPct: 67, filed7: 14, reviews: 9, right: 4, wrong: 2 }] } : { rows: [{ at: Date.now() / 1000 - 120, tone: 'done', kind: 'PoB', text: 'PoB graded right' }] }) }));
  const work = jest.fn(async (_, b) => (b.op === 'agents_now' ? { agents: [{ id: 'a', name: "Sicario's", doing: [{ kind: 'Browser', say: 'rugcheck.xyz', wait: true }, { kind: 'PoW', say: '$CARLO: read' }] }, { id: 'b', name: 'Happy', doing: [] }] }
    : { routes: [{ route: 'openrouter', calls: 12, okPct: 92, usd: 0.0123, avgMs: 2100 }, { route: 'local', calls: 30, okPct: 100, usd: 0, avgMs: 900 }], reviewer: { passPct: 61, graded: 18, waiting: 2 }, reads: { kinds: [{ kind: 'pow', ageMin: 2, freshMin: 5, reused: 3, sites: 6 }], topics: 1, topicReuses: 2 }, methods: { kits: [{ kit: 'plan-first', state: 'active', followedWin: 0.6 }] } }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<CommandCenter cat={{ id: 'leader' }} work={work} />); });
  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  const t = el.querySelector('[data-testid="command-center"]').textContent;
  expect(t).toContain('1/2'); expect(t).toContain('a browser needs you'); expect(t).toContain('42'); expect(t).toContain('$0.01'); expect(t).toContain('61%');
  expect(el.querySelector('[data-testid="ccx-floor"]').textContent).toContain('rugcheck.xyz · needs you');
  expect(el.querySelector('[data-testid="ccx-quality"]').textContent).toContain('67% right'); expect(el.querySelector('[data-testid="ccx-river"]').textContent).toContain('PoB graded right');
  expect(work.mock.calls.map(c => c[1].op).sort()).toEqual(['agents_now', 'engines']);   // two reads, in parallel, no new endpoint
});
