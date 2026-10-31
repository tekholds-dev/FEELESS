import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { mindStats, tradeChat, catLogItems, AgentLog, MindVitals, TradeChat, readSkin } from './CatCockpit';
import { genLog } from './CatWorkbench';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mount = async node => { const el = document.createElement('div'); const root = createRoot(el); await act(async () => { root.render(node); }); return el; };
const CAT = { id: 'c1', brainsCfg: { brains: ['a/ossy', 'b/g4'], decisions: [{ at: 10, word: 'BUY', sym: 'GERM', by: 'ossy', why: 'germ floor', usd: 0.001 }, { at: 20, word: 'SKIP', sym: 'RUG', by: 'g4', why: 'bundlers' }],
  cloud: [{ at: 30, word: 'BUY', sym: 'GERM', by: ['g4', 'ossy'] }], chime: [{ at: 15, text: 'watch SOL' }] } };

test('🧠 each mind\'s vitals come from its own calls; the chat puts A left, B right, you on the right', () => {
  expect(mindStats(CAT, 'a/ossy')).toMatchObject({ calls: 1, buys: 1, agreed: 1, spark: ['up'] });
  expect(mindStats(CAT, 'b/g4')).toMatchObject({ calls: 1, buys: 0, agreed: 1 });
  expect(tradeChat(CAT).map(r => r.side)).toEqual(['a', 'you', 'b']);
});

test('📁 the log files every kind of thing in its folder, newest first', async () => {
  const ev = [{ type: 'BUY', ts: 40000, detail: 'Bought 0.05 SOL of GERM' }, { type: 'STOPPED', ts: 50000, detail: 'paused: cap' }];
  const items = catLogItems(CAT, ev);
  expect(items[0].f).toBe('guards'); expect(new Set(items.map(x => x.f))).toEqual(new Set(['trades', 'guards', 'thoughts', 'cloud']));
  const el = await mount(<AgentLog items={items} />);
  expect(el.querySelectorAll('.ck-rows li')).toHaveLength(items.length);
  await act(async () => { el.querySelector('[data-testid="log-cloud"]').click(); });
  expect(el.querySelectorAll('.ck-rows li')).toHaveLength(1);
  expect(genLog({ chat: [{ by: 'you', text: 'best bet?', at: 5 }], refusals: [{ why: 'Refused: create a coin', at: 9 }] }).map(x => x.f)).toEqual(['guards', 'tasks']);
});

test('🛸 vitals + chat render, the chime goes out, a broken skin falls back', async () => {
  const send = jest.fn(() => Promise.resolve(true));
  const el = await mount(<><MindVitals cat={CAT} model="a/ossy" i={0} live /><TradeChat cat={CAT} onSend={send} /></>);
  expect(el.textContent).toContain('BRAIN A'); expect(el.querySelectorAll('.ck-msg')).toHaveLength(3);
  await act(async () => { const i = el.querySelector('[data-testid="ck-chime"]'); Object.getOwnPropertyDescriptor(Object.getPrototypeOf(i), 'value').set.call(i, 'hold longer'); i.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('.ck-say').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); });
  expect(send).toHaveBeenCalledWith('hold longer');
  localStorage.setItem('feeless.deskSkin', '{"bg":"lava","acc":"#000"}'); expect(readSkin()).toEqual({ bg: 'globe', acc: '#b388ff' });
});

test('🔐 the one-time safe-keeping box shows right AFTER the first funding lands (owner 2026-10-30) — funding itself is never blocked', async () => {
  const { FundCat } = require('./CatReal');
  localStorage.removeItem('feeless.recoverySaved.c9'); localStorage.setItem('feeless.fundIntent.c9', '25');
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ feeUsd: 2, minUsd: 10, topupMinUsd: 1 }) }));
  const onConfirm = jest.fn(); const wallet = { address: 'AgEnTwa11et1111111111111111111111111111111' };
  const el = await mount(<FundCat cat={{ id: 'c9', name: 'Scout', agentWallet: wallet }} addr="OwnerWa11et" session={() => Promise.resolve('s')} sign={jest.fn()} onConfirm={onConfirm} />);
  expect(el.querySelector('[data-testid="cr-safe"]')).toBeNull(); expect(el.querySelector('[data-testid="cr-fund-quote"]').disabled).toBe(false);
  expect(el.querySelector('[data-testid="cr-fund-in"], .cr-fund-in input').value).toBe('25');                   // the $ typed at launch
  const paid = await mount(<FundCat cat={{ id: 'c9', name: 'Scout', agentWallet: wallet, agentFunded: [{ usd: 25 }] }} addr="OwnerWa11et" session={() => Promise.resolve('s')} sign={jest.fn()} onConfirm={onConfirm} />);
  expect(paid.querySelector('[data-testid="cr-safe-addr"]').textContent).toContain('AgEnTwa11et');
  await act(async () => { paid.querySelector('[data-testid="cr-safe-check"]').click(); });
  expect(onConfirm).toHaveBeenCalled(); localStorage.removeItem('feeless.fundIntent.c9');
});

test('👀 a visitor sees the agent — never its controls', async () => {
  const { CatDesk } = require('./CatDesk');
  const cat = { id: 'v1', name: 'Scout', handle: 'scout', status: 'running', positions: [], risk: {}, brainsCfg: { brains: ['a/x', 'b/y'], kind: 'general', decisions: [], cloud: [{ text: 'both: SOL holds 150' }] } };
  const el = await mount(<CatDesk cat={cat} canEdit={false} onAct={jest.fn()} />);
  expect(el.querySelector('[data-testid="kd-stop"]')).toBeNull(); expect(el.querySelector('.kd-side')).toBeNull();
  expect(el.textContent).toContain('VIEWING'); expect(el.querySelector('[data-testid="cwb-public"]')).not.toBeNull(); expect(el.textContent).toContain('SOL holds 150');
});

test('🗄 a visitor watches it file things: the drawer pops for a NEW stored item (not the one already there), then shuts; rails show both minds', async () => {
  jest.useFakeTimers();
  const { StoredPop, MindRail } = require('./CatWorkbench');
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<StoredPop item={{ text: 'old note', at: 1 }} />); });
  expect(el.querySelector('[data-testid="cwb-stored"]')).toBeNull();
  await act(async () => { root.render(<StoredPop item={{ text: 'SOL holds 150', at: 2 }} />); });
  expect(el.querySelector('[data-testid="cwb-stored"]').textContent).toContain('SOL holds 150');
  await act(async () => { jest.advanceTimersByTime(3700); });
  expect(el.querySelector('[data-testid="cwb-stored"]')).toBeNull(); act(() => root.unmount()); jest.useRealTimers();
  const r = await mount(<MindRail side="right" w={{ i: 1, model: 'haiku', status: 'working', host: 'x.com', action: 'read', steps: 6 }} d={{ wins: 2, losses: 1, pnlSol: 0.5 }} />);
  expect(r.textContent).toContain('MIND B'); expect(r.textContent).toContain('2 / 1'); expect(r.textContent).toContain('+0.500 SOL'); expect(r.querySelector('.cwb-rail.is-go')).not.toBeNull();
});

test('🏆 the board ranks by the chosen view and the activity card knows its coin + light', () => {
  const { metric, metricWord, eventCard } = require('./AgentBoards');
  const r = { realizedPnlSol: -0.02, volumeSol: 3, winRate: 55 };
  expect(metric(r, 'pnl')).toBe(-0.02); expect(metricWord(r, 'win_rate')).toBe('55%'); expect(metricWord(r, 'pnl')).toBe('−0.0200 SOL');
  expect(eventCard({ type: 'BUY', detail: 'Bought 0.05 SOL of GERM at live price', marketCapUsd: 50000 })).toMatchObject({ sym: 'GERM', light: 'go', entry: 50000 });
  expect(eventCard({ type: 'SELL', detail: 'Sold GERM at -12%', pnlSol: -0.01 })).toMatchObject({ sym: 'GERM', light: 'stop' });
});

test('📸 one activity card per agent (5 more in its dropdown) and a real P/L snapshot path', () => {
  const { groupByAgent, curvePath } = require('./AgentBoards');
  const ev = [1, 2, 3, 4, 5, 6, 7].map(i => ({ id: `a${i}`, catId: 'A' })).concat([{ id: 'b1', catId: 'B' }]);
  const g = groupByAgent(ev);
  expect(g.map(x => x.e.id)).toEqual(['a1', 'b1']); expect(g[0].more.map(x => x.id)).toEqual(['a2', 'a3', 'a4', 'a5', 'a6']);
  expect(curvePath([1])).toBeNull(); const c = curvePath([0, 1, 2]); expect(c.up).toBe(true); expect(c.line.startsWith('M0.0')).toBe(true);
});

test('🔐 the cabinet never shows a password, key or seed phrase; 🧾 each window carries its owner vitals', () => {
  const { safeLine } = require('./CatCockpit'); const { coinVitals } = require('./AgentLive');
  expect(safeLine('signed up on x.com password: hunter2!! done')).not.toContain('hunter2');
  expect(safeLine(`key ${'3'.repeat(40)}${'A'.repeat(30)} pasted`)).toContain('•••• hidden');
  expect(safeLine('abandon ability able about above absent absorb abstract absurd abuse access accident')).toBe('•••• hidden');
  expect(safeLine('Bought 0.06 SOL of GERM at live price')).toBe('Bought 0.06 SOL of GERM at live price');
  const prose = 'FeeCat AI said exit: $WALT has the best next coin with the highest buyers and pool size and more'; expect(safeLine(prose)).toBe(prose);   // plain words stay
  expect(safeLine('my recovery phrase: abandon ability able about above absent absorb abstract absurd abuse access accident')).not.toContain('abandon');
  expect(coinVitals({ open: true, sol: 0.06, pct: 12.5, at: Date.now() / 1000 - 600 }).map(x => x[0])).toEqual(['SIZE', 'P&L', 'HELD']);
  expect(coinVitals({ open: false, pct: -2.2, pnl: -0.0013, after: 8, at: Date.now() / 1000 - 120 }).map(x => [x[0], x[2] || ''])).toEqual([['EXIT', 'dn'], ['P&L', 'dn'], ['AFTER', ''], ['SOLD', '']]);
});

test('🙈 log drawers hide one by one and one button brings them all back; repeats fold into ×N', async () => {
  const React = require('react'); const { act } = React; const { createRoot } = require('react-dom/client');
  const { AgentLog } = require('./CatCockpit'); const { genLog } = require('./CatWorkbench');
  globalThis.IS_REACT_ACT_ENVIRONMENT = true; localStorage.removeItem('feeless:log-hidden');
  const stop = { by: 'cats', text: '🧠🧠: (stopped: budget reached: the next call could exceed your remaining cap)', at: 5 };
  const items = genLog({ chat: [{ by: 'you', text: 'hi', at: 1 }, stop, { ...stop, at: 6 }, { ...stop, at: 7 }], refusals: [{ why: 'no', at: 2 }] });
  expect(items.find(x => /budget/.test(x.text)).n).toBe(3);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AgentLog items={items} />); });
  await act(async () => { el.querySelector('[data-testid="log-hide-guards"]').click(); });
  expect(el.querySelector('[data-testid="log-guards"]')).toBeNull(); expect(JSON.parse(localStorage.getItem('feeless:log-hidden'))).toEqual(['guards']);
  expect(el.querySelector('[data-testid="log-hide-all"]')).toBeNull();   // "All files" never hides
  await act(async () => { el.querySelector('[data-testid="log-unhide"]').click(); });
  expect(el.querySelector('[data-testid="log-guards"]')).not.toBeNull(); expect(el.querySelector('[data-testid="log-unhide"]')).toBeNull();
  expect(el.textContent).toContain('×3');
  await act(async () => root.unmount()); el.remove();
});
