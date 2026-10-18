import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { TradeTape, CoachBox } from './CoachTape';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const q = id => document.querySelector(`[data-testid="${id}"]`);
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); await act(async () => { root.render(node); }); return el; };
beforeEach(() => { document.body.innerHTML = ''; });
const TAPE = { stats: { n: 1, won: 1, medPct: 20, open: 1, medSlipPct: 2 }, sources: { movers: { n: 9, med: -33, won: 1 }, pump: { n: 4, med: 6, won: 3 } }, rules: { R5: { n: 8, med: -33.5, won: 0 } },
  rows: [{ mint: 'B', sym: 'OPN', at: Date.now() / 1000 - 30, open: true, buy: { usd: 0.5, sig: 'B2' }, why: {}, sells: [] },
    { mint: 'A', sym: 'AAA', at: Date.now() / 1000 - 600, open: false, buy: { usd: 1, slipPct: 2, landSec: 3, sig: 'B1' }, why: { structure: 'UPTREND' }, ai: { stance: 'CAUTION', summary: 'dev unloading', label: 'GROQ' },
      sells: [{ sig: 'S1', usd: 1.2, why: 'R7 trail' }], result: { pct: 20, usd: 0.2, heldMin: 5, rule: 'R7 trail' }, judge: { kind: 'win', why: 'banked' } }] };

test('🎬 the tape shows each real trade as one story, filters, and picks a coin for the chart', async () => {
  const onPick = jest.fn();
  await mount(<TradeTape tape={TAPE} mint="A" onPick={onPick} />);
  expect(q('ctp-stats').textContent).toContain('1 closed · 1 won · typical +20.0%');
  expect(q('ctp-res-AAA').textContent).toContain('WIN'); expect(q('ctp-res-AAA').textContent).toContain('+20.0%'); expect(q('ctp-res-OPN').textContent).toBe('HELD');
  act(() => { q('ctp-more-AAA').click(); });   // ▸ the story (folded by default)
  expect(q('ctp-trade-AAA').textContent).toContain('dev unloading'); expect(q('ctp-trade-AAA').textContent).toContain('✅ win');
  expect(q('ctp-trade-AAA').querySelector('a').getAttribute('href')).toBe('https://solscan.io/tx/B1');
  expect(q('ctp-sources').textContent).toContain('movers'); expect(q('ctp-rules').textContent).toContain('R5');
  await act(async () => { q('ctp-trade-OPN').querySelector('button').click(); }); expect(onPick).toHaveBeenCalledWith('B');
  await act(async () => { q('ctp-show-won').click(); }); expect(q('ctp-trade-OPN')).toBeNull(); expect(q('ctp-trade-AAA')).not.toBeNull();
  document.body.innerHTML = ''; await mount(<TradeTape tape={null} />); expect(q('ctp-tape').textContent).toContain('No confirmed agent buy');
});

test('👑 the creator teaches a cause, backs the model, and pulls a seat with a reason', async () => {
  const call = jest.fn(async () => ({ ok: true })); window.confirm = jest.fn(() => true);
  const coach = { blocked: 1, causes: [{ key: 'crowd fomo', words: 'top' }, { key: 'bundled', words: 'b' }], ai: { summary: 'desk keeps aping the top', source: 'GROQ' },
    rules: [{ id: 7, key: 'bundled', by: 'ai', points: -4, why: 'three bundled rugs', left: 7200 }, { id: null, key: 'thin pool', by: 'judge', points: -8 }] };
  const seats = [{ seat: 1, open: false, symbol: 'RUG', mint: 'M1', pair: 'P1', pct: -4.2 }, { seat: 2, open: true }];
  await mount(<CoachBox coach={coach} seats={seats} tpl="degen" call={call} isOwner />);
  expect(q('ctp-ai-said').textContent).toContain('desk keeps aping the top'); expect(q('ctp-rule-thin-pool').querySelector('button')).toBeNull();   // the Judge's own rule has no buttons
  await act(async () => { q('ctp-back-7').click(); });
  expect(call).toHaveBeenLastCalledWith('/admin/agents', { method: 'POST', body: JSON.stringify({ coach: { strengthen: 7 } }) });
  expect(q('ctp-teach-go').disabled).toBe(true); expect(q('ctp-pull-go').disabled).toBe(true);
  await act(async () => { q('ctp-cause-crowd-fomo').click(); });
  await act(async () => { q('ctp-teach-go').click(); });
  expect(call).toHaveBeenLastCalledWith('/admin/agents', { method: 'POST', body: JSON.stringify({ coach: { key: 'crowd fomo', why: '' } }) });
  await act(async () => { const s = q('ctp-seat'); const set = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set; set.call(s, 'M1'); s.dispatchEvent(new Event('change', { bubbles: true })); });
  await act(async () => { q('ctp-pull-go').click(); await Promise.resolve(); await Promise.resolve(); });
  expect(window.confirm).toHaveBeenCalled();
  expect(call.mock.calls.slice(-2)).toEqual([['/admin/arena/prime', { method: 'POST', body: JSON.stringify({ manualSell: { tpl: 'degen', pairAddress: 'P1', pct: 100, ack: true } }) }],
    ['/admin/agents', { method: 'POST', body: JSON.stringify({ coach: { key: 'crowd fomo', why: '', mint: 'M1', sym: 'RUG' } }) }]]);   // the card's own sell path first, THEN the lesson
  document.body.innerHTML = ''; await mount(<CoachBox coach={coach} seats={seats} tpl="degen" call={call} isOwner={false} />);
  expect(q('ctp-teach')).toBeNull(); expect(q('ctp-back-7')).toBeNull();                                                              // a non-creator sees the rules, never the controls
});

test('🎬 your trade replays: the path, a line at every would-sell %, your exit', () => {
  const { replayGeom } = require('./CoachTape');
  const g = replayGeom({ path: [0, 5, 12, 30, 40], would: [{ rule: 'R7', pct: 12 }], end: 40 });
  expect(g.marks).toHaveLength(1); expect(g.d.startsWith('M0.0,')).toBe(true); expect(g.end).toBe(40);
  expect(replayGeom({ path: [1] })).toBeNull();
});


test('🏁 recent results: a pill per closed trade (win / loss), the tally, yours marked', () => {
  const { recentResults, snapChips } = require('../../lib/coachTape');
  const r = recentResults([{ mint: 'M', sym: 'Macca', who: 'you', result: { pct: 154, usd: 0.23 } }, { mint: 'N', sym: 'Nih', result: { pct: -16.1, usd: -0.02 } }, { mint: 'O', sym: 'Open', open: true }]);
  expect(r.you.won).toBe(1); expect(r.you.usd).toBeCloseTo(0.23); expect(r.agents.lost).toBe(1);
  expect(r.won).toBe(1); expect(r.lost).toBe(1); expect(r.list.map(x => x.sym)).toEqual(['Macca', 'Nih']); expect(r.list[0].yours).toBe(true); expect(r.usd).toBeCloseTo(0.21);
  expect(snapChips({ chart: 'UPTREND', germ: 6, buyers: 61 }).map(c => c[2])).toEqual(['', 'is-good', 'is-good']);
});

test('🏁 Trades: closes first by close time, then open by buy time', () => {
  const { tapeOrder } = require('./CoachTape');
  const r = tapeOrder([{ id: 'o1', open: true, at: 9 }, { id: 'c1', closedAt: 5 }, { id: 'c2', closedAt: 7 }, { id: 'o2', open: true, at: 10 }]);
  expect(r.map(x => x.id)).toEqual(['c2', 'c1', 'o2', 'o1']);
});

test('🧪 the agents proof tile: since the fixes vs before, "too few" until 10', async () => {
  const { ProofTile } = require('./CoachTape');
  const { createRoot } = require('react-dom/client'); const { act } = require('react');
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<ProofTile p={{ n: 12, won: 58, typical: 3.1, verdict: 'better', base: { n: 58, won: 25, typical: -4.7 } }} />); });
  expect(el.textContent).toContain('58% · +3.1%'); expect(el.textContent).toContain('better');
});
