import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { ProofFile, OPEN_PROOF, partsOf } from './ProofFile';
import { FileView } from './GitFolder';


let el; let root;
beforeEach(() => { el = document.createElement('div'); document.body.appendChild(el); root = createRoot(el); });
afterEach(() => { act(() => root.unmount()); el.remove(); });
const render = ui => act(() => { root.render(ui); });
const $ = id => el.querySelector(`[data-testid="${id}"]`);
const screen = { getByTestId: id => { const x = $(id); if (!x) throw new Error(`no ${id}`); return x; }, queryByTestId: $, getByText: t => { if (!el.textContent.includes(t)) throw new Error(`no text ${t}`); return t; } };
const fireEvent = { click: x => act(() => { x.click(); }) };
const has = (x, t) => expect(x.textContent).toContain(t);

// 🗂 Slice 14: a proof file opens to its full record; an old one says what it never recorded; the button opens its proof window.
const REC = {
  v: 1, kind: 'PoB', id: 'pob1795019335', n: 2, test: true,
  true: { ran: [{ asked: 'local/ossy', answered: ['qwen/qwen3.5-9b'], routes: ['local'], calls: 9, ok: 9, usd: 0, secs: 121.5 }], read: { sites: ['espn.com', 'kalshi.com'] }, foot: { pct: 37, nearest: 1 },
    checks: [{ key: 'minds', label: 'minds', ok: true, why: 'local/ossy + local/g4 ran' }, { key: 'new', label: 'new', ok: false, why: 'mostly the same sites' }], test: { by: 'Claude', agent: "Sicario's", pair: ['local/ossy', 'local/g4'], bench: 'b1' } },
  snapshots: { pages: [{ site: 'kalshi.com', at: 1795019140, file: 'm0_0.jpg', mind: 0, found: 1 }], stash: [{ site: 'espn.com', at: 1795019150, hit: true, scrape: { kept: true, chars: 9000 }, static: { kept: true, bytes: 52000 }, shot: { kept: false } }], stashTally: { hits: 1, browsed: 2 }, private: true },
  steps: [{ at: 1795019131, mind: 0, asked: 'local/ossy', model: 'qwen/qwen3.5-9b', route: 'local', secs: 27.2, usd: 0, ok: true }, { at: 1795019170, mind: 1, asked: 'local/g4', model: 'qwen/qwen3.5-4b', route: 'lan', secs: 37.9, usd: 0.0012, ok: true }],
  stepTotals: { calls: 2, usd: 0.0012, secs: 65.1 }, kits: ['d3', 'echarts'], kitsDid: [],
  judges: { score: 71, verdict: 'pass', why: 'solid', hidden: { passed: 9, total: 10, pct: 90 }, judges: [], calls: [{ asked: 'local/zed', ok: true, usd: 0 }] },
  deal: { type: 'bid', venue: 'Kalshi', paper: false, rows: [{ ticker: 'KXNBA-1', title: 'Lakers win', side: 'yes', price: 0.6, status: 'sent', receipt: { confirmed: true, orderKept: true } }] },
  window: { win: 'bids', id: 'pob1795019335', kind: 'pob', agent: 'cat1', say: 'Open PoB #2 in its proof window' }, missing: [],
};

test('every part of the full record shows', () => {
  render(<ProofFile rec={REC} />);
  screen.getByText('6/6');
  expect(screen.getByTestId('pfr-check-minds').classList.contains('is-ok')).toBe(true); expect(screen.getByTestId('pfr-check-new').classList.contains('is-bad')).toBe(true);
  has(screen.getByTestId('pfr-minds'), 'ossy'); has(screen.getByTestId('pfr-minds'), 'qwen3.5-9b');
  has(screen.getByTestId('pfr-snaps'), 'kalshi.com'); expect(screen.getByTestId('pfr-snaps').querySelector('img').getAttribute('src')).toContain('/api/cats/cat1/powshot/pob1795019335/m0_0.jpg');
  has(screen.getByTestId('pfr-stash'), 'STASH HIT'); has(screen.getByTestId('pfr-stash'), '9,000 chars');
  has(screen.getByTestId('pfr-steps'), 'qwen3.5-4b'); has(screen.getByTestId('pfr-steps'), '$0.0012');
  has(screen.getByTestId('pfr-kits'), 'echarts');
  has(screen.getByTestId('pfr-judges'), '9/10');
  has(screen.getByTestId('pfr-deal'), 'KXNBA-1'); has(screen.getByTestId('pfr-receipt'), 'CONFIRMED');
  expect(screen.queryByTestId('pfr-missing')).toBeNull();
});

test('the button opens its proof window on the desk', () => {
  const got = []; const on = e => got.push(e.detail); window.addEventListener(OPEN_PROOF, on);
  render(<ProofFile rec={REC} />); fireEvent.click(screen.getByTestId('pfr-open'));
  window.removeEventListener(OPEN_PROOF, on);
  expect(got).toEqual([{ id: 'cat1', win: 'bids', proof: 'pob1795019335' }]);
});

test('an old file shows what it has and names what was never recorded', () => {
  const old = { v: 1, kind: 'PoStatic', id: 'ps1', n: 1, true: null, snapshots: { pages: [], stash: [] }, steps: [], kits: [], kitsDid: [], judges: null, deal: null, window: { win: 'postatic', id: 'ps1', agent: 'cat1' },
    missing: ['The step log: it was filed before the call log began.', 'Judge reviews: this proof was never reviewed.'] };
  render(<ProofFile rec={old} />);
  screen.getByText('0/6'); expect(screen.getByTestId('pfr-part-steps').classList.contains('is-off')).toBe(true);
  has(screen.getByTestId('pfr-missing'), 'filed before the call log began'); has(screen.getByTestId('pfr-missing'), 'never reviewed');
  expect(partsOf(old)).toEqual({ true: false, snaps: false, steps: false, kits: false, judges: false, deal: false });
});

test('a proof file written before Slice 14 still opens, and says so', () => {
  render(<FileView doc={{ kind: 'data', path: 'proofs/PoB/open/2026-11/x-1.json', data: { id: 'pob1', topic: 'nba', cost: 0 } }} />);
  has(screen.getByTestId('git-proof'), 'nba');
  has(screen.getByTestId('pfr'), 'written before proof files carried their full record');
});

test('the GitHub folder opens a proof file to its full record', () => {
  render(<FileView doc={{ kind: 'data', path: 'proofs/PoB/open/2026-11/x-1.json', data: { id: 'pob1795019335', topic: 'nba', fileRecord: REC } }} />);
  expect(screen.getByTestId('git-proof').contains(screen.getByTestId('pfr-steps'))).toBe(true);
});
