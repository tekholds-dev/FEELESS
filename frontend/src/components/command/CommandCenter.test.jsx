import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CommandCenter, DeskLane, deskSums } from './CommandCenter';

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
  expect(work.mock.calls.map(c => c[1].op).sort()).toEqual(['agents_now', 'engines', 'pool', 'wallet']);   // the floor's two reads + the desk's two, no new endpoint
});

test('THIS DESK: its wallet, its 24h thinking bills and its Pool from real reads; a failed read says why, nothing is filled in', async () => {
  const now = Date.now() / 1000;
  const work = jest.fn(async (_, b) => (b.op === 'wallet' ? { address: 'AbCdEfGh1234', sol: 0.0421, usdc: 3.5, modelReceipts: [{ at: now - 60, usd: 0.012, model: 'qwen' }, { at: now - 100000, usd: 9 }] }
    : Promise.reject(new Error('The Pool is closed right now.'))));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<DeskLane cat={{ id: 'x' }} work={work} />); });
  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  const t = el.querySelector('[data-testid="ccx-desk"]').textContent;
  expect(t).toContain('0.0421 SOL'); expect(t).toContain('$3.50 USDC'); expect(t).toContain('$0.0120'); expect(t).toContain('1 paid calls'); expect(t).not.toContain('$9');
  expect(el.querySelector('[data-testid="ccx-desk-perr"]').textContent).toBe('The Pool is closed right now.');
});

test('deskSums reads the Fuse books for the desk that trades from the card, and counts owed up live', () => {
  const f = deskSums({ fuse: true, walletSol: 0.13, cardSol: 0.1, reserveSol: 0.02, outsideSol: 0.01 }, null);
  expect(f.fuse).toBe(true); expect(f.sol).toBe(0.13); expect(f.card).toBe(0.1); expect(f.owed).toBe(null);
  const p = deskSums({ sol: 1 }, { pool: { owedUsd: 1, ratePerSecUsd: 0.5, at: 100, sentUsd: 2 } }, 110);
  expect(p.owed).toBe(6); expect(p.sent).toBe(2);
});
