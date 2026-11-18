import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { TrueRecord, lastOf } from './TrueRecord';
import { ProofTile } from './ProofKit';

const checks = ok => [['minds', ok], ['sources', true], ['footprint', true], ['kits', true]].map(([key, v]) => ({ key, label: key, ok: v, why: `${key} why` }));
const real = { id: 'pob1', n: 7, at: 100, proofChecks: checks(false), ran: [{ asked: 'z-ai/glm-5.3', answered: ['z-ai/glm-5.3'], routes: ['openrouter'], calls: 2, ok: 2 }],
  mindsCheck: { ok: false, why: 'z-ai/glm-5.3 ran but the pair is local/ossy + local/g4' }, read: { sites: ['espn.com'], pages: [] }, foot: { pct: 64, nearest: 6 } };
const test_ = { id: 'pob2', n: 8, at: 200, checks: checks(true), test: { by: 'Claude', agent: "Sicario's", pair: ['local/ossy', 'local/g4'], bench: 'abc' },
  ran: [{ asked: 'local/ossy', answered: ['qwen/qwen3.5-9b'], routes: ['local'], calls: 3, ok: 3 }, { asked: 'local/g4', answered: ['qwen/qwen3.5-4b'], routes: ['lan'], calls: 3, ok: 3 }],
  mindsCheck: { ok: true, why: 'local/ossy + local/g4 ran' }, read: { sites: ['covers.com', 'nba.com', 'rotowire.com', 'espn.com'], pages: ['https://nba.com/a'] }, foot: { pct: 81, nearest: 7, sentBack: 1 } };

test('🧾 every proof window shows the last proof\'s true record: checks as meters, the minds that REALLY ran, its sources, its footprint, and TEST', async () => {
  expect(lastOf([real, test_], false).id).toBe('pob1'); expect(lastOf([real, test_], true).id).toBe('pob2'); expect(lastOf([{ id: 'old', at: 1 }])).toBe(null);
  expect(lastOf([{ id: 'pow9', at: 999, checks: 3 }])).toBe(null);   // a PoW folder's own `checks` is its live-trade counter: never read as a record   // a folder filed before Slice 0 has no record: nothing invented
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<TrueRecord kind="pob" folders={[real, test_]} />); });
  expect(el.textContent).toContain('LAST FILED · PoB #7'); expect(el.textContent).toContain('3/4');
  expect(el.querySelector('[data-testid="trc-minds"]').textContent).toContain('glm-5.3 → glm-5.3 · openrouter · 2 calls');
  expect(el.querySelector('[data-testid="trc-check-minds"]').textContent).toContain('FAIL');
  await act(async () => { el.querySelector('[data-testid="trc-lens-test"]').click(); });
  expect(el.textContent).toContain('LAST TEST · PoB #8'); expect(el.querySelector('[data-testid="trc-test"]').textContent).toBe('TEST'); expect(el.textContent).toContain('4/4');
  expect(el.querySelector('[data-testid="trc-minds"]').textContent).toContain('ossy → qwen3.5-9b · local · 3 calls');
  expect(el.querySelector('[data-testid="trc-sources"]').textContent).toContain('4 sites');
  expect(el.querySelector('[data-testid="trc-foot"]').textContent).toContain('81% new next to #7 · sent back once first');
  await act(async () => { root.render(<ProofTile label="PoB #8" testid="t8" test={test_.test} />); });
  expect(el.querySelector('[data-testid="t8-test"]').textContent).toBe('TEST');
  await act(async () => { root.render(<ProofTile label="PoB #7" testid="t7" />); });
  expect(el.querySelector('[data-testid="t7-test"]')).toBe(null);   // a real proof never wears TEST
  act(() => root.unmount());
});

test('🪦 Slice 2: a PoStatic given 3D studio pieces shows each one and whether its page really carries it', async () => {
  const pos = { id: 'ps1', n: 9, at: 300, proofChecks: [...checks(true), { key: 'studio', label: 'studio', ok: true, why: 'Tombstone' }], ran: [], read: { sites: [], pages: [] }, foot: { pct: 90 },
    studio: [{ id: 'tomb', name: 'Tombstone', height: 1.6, turn: [0, 0.6109, 0], spin: 6, used: true }] };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<TrueRecord kind="pos" folders={[pos]} />); });
  expect(el.textContent).toContain('5/5'); expect(el.querySelector('[data-testid="trc-check-studio"]').textContent).toContain('PASS');
  expect(el.querySelector('[data-testid="trc-studio"]').textContent).toBe('Tombstone · 1.6 m · 35° · spin 6 · in the page');
  await act(async () => { root.render(<TrueRecord kind="pos" folders={[{ ...pos, studio: [{ ...pos.studio[0], used: false }] }]} />); });
  expect(el.querySelector('[data-testid="trc-studio"]').className).toBe('is-bad'); expect(el.querySelector('[data-testid="trc-studio"]').textContent).toContain('MISSING');
  await act(async () => { root.render(<TrueRecord kind="pos" folders={[{ ...pos, studio: undefined }]} />); });
  expect(el.querySelector('[data-testid="trc-studio"]')).toBe(null);   // no piece, no line
  act(() => root.unmount());
});
