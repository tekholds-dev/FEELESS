import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { AgentDesk } from './AgentDesk';
import { heat, reasonsOf, scopeOf, docketOf, listFor, seatMoves, CardNow, CourtBand, Court, MissionBar, DutyBox, dutyLeft, GrowthCards, PowerLadder } from './AgentScreens';

const row = (mint, symbol, d5, lean, trig, dev, go, drivers, rug) => ({ mint, symbol, pair: `P${mint}`, go, nums: { d5, pace: 2, buy: 60 }, why: { lean, drivers }, trigger: [trig, 'why t'], devil: [dev, dev === 'object' ? 'its read is BOND RUN' : ''], vitals: { top10: 40, rug, organic: 3 } });
const table = [row('A', 'GOOD', 4, 2.4, 'enter', 'agree', true, [['surge', 1, 'volume surging'], ['buyers', 0.5, 'buyers in charge']], 10),
  row('B', 'RUN', 9, 1.9, 'enter', 'object', false, [['surge', 1, 'volume surging'], ['swarm', -1, 'copy-paste callers']], 70), row('C', 'MEH', -2, 0.2, 'wait', '—', false, [], 20)];
const view = { agents: [['tally', '📊', 'Tally'], ['sherlock', '🔍', 'Sherlock'], ['trigger', '⏱', 'Trigger'], ['devil', '⚖', 'Devil']].map(([key, icon, name]) => ({ key, icon, name, job: 'job', n: 12, med: 1, right: 55 })),
  stage: { h: 5, conquered: [], needN: 30, needWin: 55 }, desk: { start: 20, now: 20, x: 1, best: 1, busts: 0, trades: 0 }, road: { pct: 3, paper: { done: false, x: 1, need: 10, n: 0, needN: 30 }, real: { open: false, n: 0, needN: 10 } },
  bar: 1.5, perf: { tally: 1, sherlock: 2, trigger: 1, devil: 1, coins: 3, at: Date.now() / 1000 - 10 }, tasks: { tally: 'read 3 coins' }, life: {}, thoughts: [], table, cfg: { agentLearn: true },
  growth: { tally: { level: 2, icon: '🧒', name: 'Rookie', xp: 40, next: 60, nextName: '🦾 Veteran', pct: 33, earned: 57, gen: 1, stunted: false, genes: [], skills: [], scars: 0 },
    sherlock: { level: 1, icon: '🐣', name: 'Hatchling', xp: 44, next: 30, nextName: '🧒 Rookie', pct: 0, earned: 31, gen: 2, stunted: true, genes: ['callers piling in (-6%)'], skills: [], scars: 1 } },
  power: { seats: 1, held: 1, steps: [{ key: 'learn', icon: '🎓', seats: 1, on: true, done: true, pct: 100, need: 'your switch' }, { key: 'trust', icon: '🤝', seats: 2, on: false, done: false, pct: 30, need: '3/10 closed · +8.0%' }, { key: 'proven', icon: '🏆', seats: 3, on: true, done: false, pct: 7, need: '1.17× of 10× · 12/30 calls' }] },
  card: { tpl: 'degen', seats: [{ symbol: 'BOT', pair: 'P1', mint: 'M1', kind: 'agent', pct: 5, take: 10, action: 'hold', why: '+5.0% — holding until +10%' }, { symbol: 'MINE', pair: 'P2', mint: 'M2', kind: 'yours', pct: null }, { kind: 'open', symbol: null, pct: null }] } };

test('screen helpers: heat, reasons (who carries them), the scope (bar at the middle), the docket and the click-through order', () => {
  expect(heat(0)).toBe(0.12); expect(heat(-5)).toBe(0.5); expect(heat(40)).toBe(1);
  const rs = reasonsOf(table); expect(rs[0]).toMatchObject({ key: 'surge', n: 2, w: 1, mints: ['A', 'B'] }); expect(rs.find(r => r.key === 'swarm').w).toBe(-1);
  const sc = scopeOf([{ mint: 'X', symbol: 'X', nums: { d5: 0 }, why: { lean: 1.5 }, trigger: ['enter'], go: true }], 1.5);
  expect(sc[0]).toMatchObject({ go: true, call: 'enter', y: 0.5 }); expect(sc[0].x).toBeCloseTo(1 / 3);
  expect(docketOf(table).map(x => [x.sym, x.ok, x.go, x.rug])).toEqual([['GOOD', true, true, 10], ['RUN', false, false, 70]]);
  expect(listFor('tally', table)).toEqual(['A', 'B', 'C']); expect(listFor('devil', table)).toEqual(['A', 'B']); expect(listFor('trigger', table)[0]).toBe('A');
  expect(listFor('sherlock', table, 'swarm')).toEqual(['B']); expect(listFor('devil', [table[2]])).toEqual(['C']);   // no ENTER → the whole pass
});

test('tap a mini screen → the zoom: tap a mark or step ‹ › through the coins, switch agent, filter by a reason, Esc closes', async () => {
  const call = jest.fn(async () => view); const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AgentDesk call={call} />); });
  const q = id => document.querySelector(`[data-testid="${id}"]`);
  expect(q('screen-tally').textContent).toContain('3'); expect(q('screen-devil').textContent).toContain('1/2'); expect(q('ags-zoom')).toBeNull();
  await act(async () => { q('screen-tally').click(); });
  expect(q('ags-zoom')).not.toBeNull(); expect(q('tile-GOOD')).not.toBeNull(); expect(q('ags-dossier').textContent).toContain('$GOOD'); expect(q('ags-dossier').textContent).toContain('1 / 3');
  await act(async () => { q('tile-RUN').click(); });
  expect(q('ags-dossier').textContent).toContain('$RUN'); expect(q('ags-dossier').textContent).toContain('OBJECTED'); expect(q('ags-dossier').textContent).toContain('BOND RUN');
  await act(async () => { q('ags-next').click(); });
  expect(q('ags-dossier').textContent).toContain('$MEH');
  await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight' })); });
  expect(q('ags-dossier').textContent).toContain('$GOOD');   // wraps
  await act(async () => { q('zoom-sherlock').click(); });
  expect(q('reason-surge').textContent).toContain('×2'); expect(q('chip-MEH')).not.toBeNull();
  await act(async () => { q('reason-swarm').click(); });
  expect(q('chip-MEH')).toBeNull(); expect(q('chip-GOOD')).toBeNull(); expect(q('ags-dossier').textContent).toContain('$RUN');   // only the coins with that reason
  await act(async () => { q('zoom-devil').click(); });
  expect(q('ticket-GOOD').textContent).toContain('GO'); expect(q('ticket-RUN').textContent).toContain('✕');
  await act(async () => { q('zoom-trigger').click(); });
  expect(q('dot-GOOD')).not.toBeNull();
  await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); });
  expect(q('ags-zoom')).toBeNull();
  expect(q('ags-card').textContent).toContain('$BOT'); expect(q('ags-pow').textContent).toContain('1 / 1 seats');   // the real card strip is always on screen
  await act(async () => { root.unmount(); });
});

test('the real card as seats, growth cards and the seat ladder', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<><CardNow card={view.card} power={view.power} cfg={view.cfg} /><GrowthCards growth={view.growth} agents={view.agents} /><PowerLadder power={view.power} /></>); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('seat-BOT').className).toContain('is-agent'); expect(q('seat-BOT').textContent).toContain('+5.0%'); expect(q('seat-BOT').textContent).toContain('⏳');
  expect(q('seat-MINE').textContent).toContain('—'); expect(q('ags-card').textContent).toContain('open');   // no price = "—", never a fake 0%
  expect(q('grow-tally').textContent).toContain('Rookie'); expect(q('grow-tally').textContent).toContain('40/60'); expect(q('grow-tally').textContent).toContain('57% earned');
  expect(q('grow-sherlock').className).toContain('is-stunted'); expect(q('grow-sherlock').textContent).toContain('⚠ stunted'); expect(q('grow-sherlock').textContent).toContain('☠×1'); expect(q('grow-sherlock').textContent).toContain('🧬 callers piling in');
  expect(q('rung-learn').textContent).toContain('✓ live'); expect(q('rung-trust').textContent).toContain('3/10 closed'); expect(q('rung-trust').textContent).toContain('switch off'); expect(q('ags-ladder').textContent).toContain('1 held of 1');
  await act(async () => { root.render(<CardNow card={{}} cfg={{}} />); });
  expect(q('ags-card').textContent).toContain('paper only');
  await act(async () => { root.unmount(); });
});

const judge = { n: 4, wins: 2, losses: 2, trial: 'trigger', handicap: 'bar +0.5', mvp: 'sherlock', needNet: 2,
  score: { tally: { credit: 0, blame: 0, net: 0 }, sherlock: { credit: 2, blame: 0, net: 2 }, trigger: { credit: 0, blame: 2, net: -2 }, devil: { credit: 0, blame: 0, net: 0 } },
  rulings: [{ sym: 'GOOD', mint: 'A', pct: 8, at: 2, verdict: 'win', credit: 'sherlock', blame: null, kind: 'go' }, { sym: 'RUN', mint: 'B', pct: -6, at: 1, verdict: 'loss', credit: null, blame: 'trigger', kind: 'go' }] };

test('every seat is a control: an open seat fills with a GO coin, a held seat swaps one in, the agents\' seat pulls — a ⚠ comes back as "do it anyway"', async () => {
  const gos = [{ mint: 'G1', symbol: 'GO1', pair: 'PG1' }, { mint: 'M1', symbol: 'BOT', pair: 'P1' }];
  expect(seatMoves({ kind: 'open' }, 'degen', gos)[0].body).toEqual({ fillSeat: { tpl: 'degen', to: 'G1', toPair: 'PG1', via: 'agents' } });
  expect(seatMoves({ kind: 'agent', symbol: 'BOT', pair: 'P1' }, 'degen', gos.slice(0, 1)).map(m => m.k)).toEqual(['manualSell', 'pickSwap']);
  expect(seatMoves({ kind: 'yours', symbol: 'MINE', pair: 'P2', state: 'ride' }, 'degen', gos)).toEqual([]);   // a riding coin is never swapped from here
  const call = jest.fn(async (path, o) => { const b = JSON.parse(o.body); if (b.pickSwap && !b.pickSwap.ack) throw new Error('⚠ ⏳ $MINE was bought 4 min ago'); return { ok: true }; });
  const done = jest.fn(); const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CardNow card={view.card} power={view.power} cfg={view.cfg} gos={gos} call={call} onDone={done} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('ags-tray')).toBeNull();
  await act(async () => { q('seat-open-2').click(); });
  expect(q('move-fill-GO1')).not.toBeNull(); expect(q('move-fill-BOT')).toBeNull();   // a GO coin already on the card is never offered
  await act(async () => { q('move-fill-GO1').click(); });
  expect(JSON.parse(call.mock.calls[0][1].body)).toEqual({ fillSeat: { tpl: 'degen', to: 'G1', toPair: 'PG1', via: 'agents' } }); expect(done).toHaveBeenCalledTimes(1); expect(q('ags-tray')).toBeNull();
  await act(async () => { q('seat-MINE').click(); });
  await act(async () => { q('move-swap-GO1').click(); });
  expect(q('ags-tray').textContent).toContain('bought 4 min ago');   // the card's own warning, shown — nothing sent past it
  await act(async () => { q('seat-ack').click(); });
  expect(JSON.parse(call.mock.calls[2][1].body).pickSwap).toMatchObject({ pairAddress: 'P2', to: 'G1', ack: true, now: true });
  await act(async () => { q('seat-BOT').click(); });
  await act(async () => { q('move-pull').click(); });
  expect(JSON.parse(call.mock.calls[3][1].body)).toEqual({ manualSell: { tpl: 'degen', pairAddress: 'P1', pct: 100 } });
  await act(async () => { root.unmount(); });
});

test('the Judge band: W–L, who is on trial + its handicap, the 👑, the ruling tape; proof pips for paper and card; the court zoom', async () => {
  const pick = jest.fn(); const court = jest.fn(); const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const proof = { paper: { n: 3, w: 2, l: 1, last: [8, -6, 4], syms: ['GOOD', 'RUN', 'OK'] }, card: { n: 0, w: 0, l: 0, last: [] } };
  await act(async () => { root.render(<><CourtBand judge={judge} proof={proof} desk={{ heat: 'heater', stake: 35 }} onPick={pick} onCourt={court} /><Court judge={judge} onPick={pick} /></>); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('ags-judge').textContent).toContain('2W'); expect(q('ags-judge').textContent).toContain('2L');
  expect(q('ags-trial').textContent).toContain('⏱ ON TRIAL · bar +0.5'); expect(q('ags-mvp').textContent).toContain('👑 🔍');
  expect(q('rule-GOOD').className).toContain('is-win'); expect(q('rule-RUN').textContent).toContain('-6.0%'); expect(q('rule-RUN').textContent).toContain('⏱');
  expect(q('ags-proof').querySelectorAll('.ags-pips i.is-up').length).toBe(2); expect(q('ags-proof').textContent).toContain('none yet'); expect(q('ags-stake').textContent).toContain('🔥 next stake 35%');
  await act(async () => { q('rule-RUN').click(); q('ags-judge').click(); });
  expect(pick).toHaveBeenCalledWith('RUN'); expect(court).toHaveBeenCalled();
  expect(q('score-trigger').className).toContain('is-trial'); expect(q('score-sherlock').textContent).toContain('+2'); expect(q('case-GOOD').textContent).toContain('🔍✓');
  await act(async () => { root.unmount(); });
});

test('the mission: breakeven first as a distance (never a promise), then the paper 10×; the scalp plan they learned vs holding', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { root.render(<MissionBar mission={{ key: 'breakeven', value: 0.81, putIn: 22.5, pct: 3.6, needX: 27.8 }} scalp={{ n: 7, needN: 20, best: null, flat: {} }} desk={{ x: 1.17 }} />); });
  expect(q('goal-breakeven').className).toContain('is-now'); expect(q('goal-breakeven').textContent).toContain('$0.81'); expect(q('goal-breakeven').textContent).toContain('needs 27.8×');
  expect(q('goal-tenx').textContent).toContain('1.17×'); expect(q('ags-scalp').textContent).toContain('LEARNING'); expect(q('ags-scalp').textContent).toContain('7 / 20 paths');
  await act(async () => { root.render(<MissionBar mission={{ key: 'tenx', value: 30, putIn: 22.5 }} scalp={{ n: 24, needN: 20, best: { tp: 8, sl: 0, avg: 3.1 }, flat: { avg: -2 }, peak: 9, live: { tp: 8, sl: 0 } }} desk={{ x: 2 }} />); });
  expect(q('goal-breakeven').className).toContain('is-done'); expect(q('goal-tenx').className).toContain('is-now');
  expect(q('ags-scalp').textContent).toContain('LIVE'); expect(q('ags-scalp').textContent).toContain('TP +8%'); expect(q('ags-scalp').textContent).toContain('no stop'); expect(q('ags-scalp').textContent).toContain('+3.1%'); expect(q('ags-scalp').textContent).toContain('-2%');
  await act(async () => { root.unmount(); });
});

test('the 10-minute duty: a clock to the next move, their lives on real money, the breakeven lock and a case file per coin', async () => {
  expect(dutyLeft({ at: 1000, every: 600 }, 1250)).toBe(350); expect(dutyLeft({ at: 1000, every: 600 }, 9999)).toBe(0); expect(dutyLeft({ at: 0 }, 5)).toBe(0);
  const now = Date.now() / 1000; const pick = jest.fn();
  const duty = { on: true, every: 600, at: now - 100, cases: [
    { mint: 'A', symbol: 'BEST', lean: 1.2, cleared: true, checks: [['scan', true, 'holder scan passed'], ['age', true, '3.0h old'], ['pool', true, 'pool $60K'], ['burn', true, 'not burned'], ['devil', true, 'no evidence against it']] },
    { mint: 'B', symbol: 'BABY', lean: 3, cleared: false, checks: [['scan', true, 'holder scan passed'], ['age', false, '0.3h old'], ['pool', true, 'pool $60K'], ['burn', true, 'not burned'], ['devil', true, 'ok']] }] };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { root.render(<DutyBox duty={duty} lives={{ n: 7, of: 9 }} underwater onPick={pick} />); });
  expect(q('duty-clock').textContent).toMatch(/next move 8:[12]\d/); expect(q('ags-lives').textContent).toBe('❤❤❤❤❤❤❤♡♡'); expect(q('ags-lock').textContent).toContain('until breakeven');
  expect(q('case-file-BEST').className).toContain('is-clear'); expect(q('case-file-BEST').textContent).toContain('NEXT UP'); expect(q('case-file-BEST').querySelectorAll('.is-ok').length).toBe(5);
  expect(q('case-file-BABY').className).toContain('is-blocked'); expect(q('case-file-BABY').textContent).toContain('0.3h old'); expect(q('case-file-BABY').querySelectorAll('.is-no').length).toBe(1);
  await act(async () => { q('case-file-BABY').click(); });
  expect(pick).toHaveBeenCalledWith('BABY');
  await act(async () => { root.render(<DutyBox duty={{ ...duty, at: now - 700, cases: duty.cases.slice(1) }} lives={{ n: 9, of: 9 }} />); });
  expect(q('duty-clock').textContent).toContain('nothing cleared yet'); expect(q('ags-lock')).toBeNull();
  await act(async () => { root.render(<DutyBox duty={{ on: false, cases: [] }} />); });
  expect(q('duty-clock').textContent).toContain('not in control');
  await act(async () => { root.unmount(); });
});
