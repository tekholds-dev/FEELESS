import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CatDesk, deskVitals, curveOf } from './CatDesk';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../terminal/PriceChart', () => ({ PriceChart: () => null }));   // lightweight-charts is ESM jest can't parse (the desk's live windows load it lazily)
const today = new Date().toISOString().slice(0, 10);
const CAT = { id: 'c1', name: 'Specter', handle: 'specter', avatar: 'Solaris Spots', look: { gear: 'crown', aura: 'gold', eyes: 'laser' }, status: 'running', level: 2, xp: 60, wallet: 'W'.repeat(44),
  balanceSol: 9.6, startingBalanceSol: 10, realizedPnlSol: -0.12, totalPnlSol: -0.08, wins: 3, losses: 5, winRate: 38, strategyLabel: 'Breakouts',
  positions: [{ symbol: 'MOON', pairAddress: 'P1', mint: 'M1', currentChange: 12.5, costSol: 0.25, openedAt: Date.now() / 1000 - 1800, reason: 'germ floor held' }, { symbol: 'RUG', pairAddress: 'P2', currentChange: -20, costSol: 0.2 }],
  pnlHistory: [{ value: 0 }, { value: 0.1 }, { value: -0.2 }, { value: -0.08 }], risk: { maxPositionSol: 0.25, maxDailyLossSol: 0.5, allowlist: [], blocklist: ['SCAM'] },
  dailyLoss: { [today]: 0.4 }, learn: { params: { runnerTrail: 25, takeProfit1: 40 }, log: [{ note: 'Sold $X at +8 %, it ran +60 % — give runners room' }] } };

test('🤖 the desk numbers: today\'s loss against its cap, slots, mood; the P/L curve crosses zero where it should', () => {
  const v = deskVitals(CAT, today);
  expect(v).toMatchObject({ bal: 9.6, start: 10, open: 2, slots: 5, lossToday: 0.4, cap: 0.5, closed: 8, mood: 'pounce' });
  expect(v.capUsed).toBeCloseTo(0.8);
  expect(deskVitals({ ...CAT, status: 'stopped' }).mood).toBe('sleep'); expect(deskVitals({ ...CAT, positions: [], realizedPnlSol: 1 }).mood).toBe('celebrate');
  const c = curveOf(CAT.pnlHistory); expect(c.up).toBe(false); expect(c.line.startsWith('M0.00')).toBe(true); expect(c.zero).toBeGreaterThan(2); expect(c.zero).toBeLessThan(38);
  expect(curveOf([]).line).toContain('M0.00');   // a fresh cat still draws a flat line, never a crash
});

test('🤖 the desk renders an agent HOLDING coins (the old page crashed on a deleted row component), acts, opens a coin\'s war room, saves limits', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const onAct = jest.fn(); const room = jest.fn();
  window.addEventListener('feeless:war-room', room);
  await act(async () => { root.render(<CatDesk cat={CAT} onBack={() => {}} onAct={onAct} Activity={<p data-testid="feed">feed</p>} />); });
  expect(el.querySelector('[data-testid="kd-dl"]').getAttribute('aria-label')).toContain(CAT.name);   // ⬇ its picture as a PNG
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('kd-state').textContent).toContain('HOLDING 2'); expect(el.textContent).toContain('$MOON'); expect(el.textContent).toContain('+12.5%'); expect(el.textContent).toContain('-20.0%');
  const dq = id => document.querySelector(`[data-testid="${id}"]`);
  await act(async () => { q('kd-open-desktop').click(); });   // its wallet + limits live on its desktop
  await act(async () => { dq('dsk-ico-wallet').click(); });
  expect(dq('dsk-win-wallet').textContent).toContain('0.400 / 0.5 SOL');
  await act(async () => { dq('dsk-ico-log').click(); }); expect(dq('dsk-win-log').querySelector('[data-testid="feed"]')).not.toBeNull();   // its log has its own folder, the wallet is only money
  expect(el.querySelector('.g-crown')).not.toBeNull();                                                   // its built look, drawn
  act(() => dq('kd-pos-0').click()); expect(room.mock.calls[0][0].detail).toMatchObject({ pairAddress: 'P1', baseToken: { symbol: 'MOON' } });
  act(() => q('kd-stop').click()); expect(onAct).toHaveBeenLastCalledWith('stop');
  act(() => q('kd-run').click()); expect(onAct).toHaveBeenLastCalledWith('run');
  await act(async () => { (dq('dsk-ico-brains') || dq('dsk-ico-limits')).click(); }); if (dq('dsk-tab-limits')) await act(async () => { dq('dsk-tab-limits').click(); });
  act(() => dq('kd-save').click()); expect(onAct.mock.calls.at(-1)[0]).toBe('controls'); expect(onAct.mock.calls.at(-1)[1]).toMatchObject({ maxPositionSol: 0.25, blocklist: 'SCAM' });
  await act(async () => { root.render(<CatDesk cat={{ ...CAT, status: 'stopped', positions: [] }} onBack={() => {}} onAct={onAct} />); });
  expect(q('kd-state').textContent).toContain('STOPPED'); act(() => q('kd-start').click()); expect(onAct).toHaveBeenLastCalledWith('start');
  window.removeEventListener('feeless:war-room', room); act(() => root.unmount());
});

test('🐱 Fee on her desk: the creator gets her tools, never a button the server only answers 403 to; a visitor just views', async () => {
  globalThis.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ cat: { id: 'leader', positions: [] }, events: [] }) }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const q = id => el.querySelector(`[data-testid="${id}"]`); const fee = { ...CAT, id: 'leader', name: 'Fee', isLeader: true };
  await act(async () => { root.render(<CatDesk cat={fee} canEdit onBack={() => {}} onAct={() => {}} Tools={<p data-testid="tools">tools</p>} />); });
  expect(q('tools')).not.toBeNull(); expect(q('fee-live')).not.toBeNull(); expect(el.textContent).toContain('YOUR AGENT');
  ['kd-stop', 'kd-run', 'kd-save', 'kd-withdraw', 'kd-revoke'].forEach(id => expect(q(id)).toBeNull());
  await act(async () => { root.render(<CatDesk cat={fee} canEdit={false} onBack={() => {}} onAct={() => {}} />); });
  expect(el.textContent).toContain('VIEWING'); expect(el.textContent).not.toContain('YOUR AGENT');
  act(() => root.unmount());
});

test('💵 a general agent with a wallet shows its real wallet, credit and coins, never the paper tiles', async () => {
  globalThis.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ balance: { sol: 0.0266, usdc: 0 } }) }));
  const gen = { ...CAT, brainsCfg: { kind: 'general', brains: ['a/x'], brainMode: 'turns', credit: 12.5, spent: 0.5 }, agentWallet: { address: 'R'.repeat(44), mode: 'approve' }, realHeld: { M1: { symbol: 'JUP', pair: 'P1' } }, agentTx: [{ status: 'success' }, { status: 'failed' }] };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CatDesk cat={gen} canEdit onBack={() => {}} onAct={() => {}} />); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('kd-real-tiles')).toBeNull(); expect(q('kd-tab-desk').getAttribute('aria-selected')).toBe('true');   // 🖥 the Desk tab is one screen: windows + chat
  const dq = id => document.querySelector(`[data-testid="${id}"]`);
  await act(async () => { q('kd-open-desktop').click(); });
  await act(async () => { dq('dsk-ico-wallet').click(); });
  expect(dq('kd-real-tiles').textContent).toContain('0.0266 SOL'); expect(dq('kd-real-tiles').textContent).toContain('$12.50');
  expect(dq('kd-real-holds').textContent).toContain('$JUP'); expect(q('kd-wallet').textContent).toContain('ITS WALLET'); expect(dq('kd-curve')).toBeNull(); expect(el.textContent).not.toContain('PAPER WALLET');
  act(() => root.unmount());
});

test('📊 model × proof: real rows per model and kind, a pick only where the record is big enough (COL-5)', async () => {
  const { ModelVitals } = require('./CatDesk');
  globalThis.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ missions: [{}, {}], chain: { intact: true, count: 40 }, vitals: { rows: [
    { model: 'z-ai/glm-5.3-flash', kind: 'pos', proofs: 1, calls: 3, localCalls: 0, perProofUsd: 0.0061, quality: 142.1, verified: 0, winRate: null, failRate: 0, enough: false },
    { model: 'local/ossy', kind: 'pob', proofs: 6, calls: 14, localCalls: 14, perProofUsd: 0, quality: 118.4, verified: 6, winRate: 0.667, failRate: 0.286, enough: true }],
    pick: { pos: { model: null, why: 'not enough settled proofs yet' }, pob: { model: 'local/ossy', why: 'cheapest within 10 points' } } } }) }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<ModelVitals cat={{ id: 'c1' }} />); }); await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  const t = el.textContent;
  expect(globalThis.fetch.mock.calls[0][0]).toContain('/api/cats/c1/missions?'); expect(t).toContain('2 proofs · record intact · 40 events');
  expect(t).toContain('glm-5.3-flash'); expect(t).toContain('too few to rank'); expect(t).toContain('67%'); expect(t).toContain('14 local');
  expect(el.querySelector('.kd-mv-n.is-bad')).toBeTruthy();   // 29% of calls failed
  expect(t).toContain('PoB → ossy: cheapest within 10 points'); expect(t).toContain('PoStatic : not enough settled proofs yet');
  act(() => root.unmount());
});

test('⬇ the desk has a download button on its picture; the file name is the agent\'s', () => {
  const { fileName, inlineSvg } = require('../../lib/svgPng');
  expect(fileName('Night Claw')).toBe('night-claw-feeless.png'); expect(fileName('')).toBe('agent-feeless.png');
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('viewBox', '0 0 10 20'); svg.setAttribute('class', 'x');
  const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle'); c.style.fill = 'rgb(179, 136, 255)'; svg.appendChild(c); document.body.appendChild(svg);
  const out = inlineSvg(svg, 512);
  expect(out).toContain('width="512"'); expect(out).toContain('height="1024"'); expect(out).toContain('fill: rgb(179, 136, 255)'); expect(out).not.toContain('class="x"');
  svg.remove();
});

test('🃏 one owner desk: a two-brain trader gets the same desk as a general agent — brain vitals · head cloud + chat · vitals — and Files flips it to its cabinet', async () => {
  global.fetch = async () => ({ ok: true, json: async () => ({}) });
  const t0 = Date.now() / 1000;
  const cat = { ...CAT, brainsCfg: { kind: 'trading', brains: ['nvidia/nemotron-a:free', 'nvidia/nemotron-b:free'], credit: 1, decisions: [{ by: 'nemotron-a', word: 'BUY', sym: 'HUSS', why: 'volume', at: t0 }], chime: [], cloud: [] } };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const onAct = jest.fn();
  await act(async () => { root.render(<CatDesk cat={cat} canEdit onBack={() => {}} onAct={onAct} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('desk-flip')).not.toBeNull(); expect(q('ck-vitals-0').textContent).toContain('BUY');   // its ":free" model still counts its calls
  expect(q('cwb-cockpit').textContent).toContain('Chat with Specter'); expect(q('ck-chat')).not.toBeNull();
  await act(async () => { q('cwb-flip').click(); });
  expect(el.querySelector('.cwb-flip').className).toContain('is-back'); expect(q('cwb-sheet').textContent).toContain('API keys');
  await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); });
  expect(el.querySelector('.cwb-flip').className).not.toContain('is-back');
  act(() => root.unmount());
});

test('🧠🧠 by proof: a kind picks its own two minds from the agent\'s own, saves them, and can go back to the pair above (COL-2)', async () => {
  const { KindMinds } = require('./CatDesk');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const onAct = jest.fn();
  const cat = { name: 'Sicario', brainsCfg: { brains: ['local/ossy', 'local/g4'], byKind: { pow: ['local/g4'] } } };
  await act(async () => root.render(<KindMinds cat={cat} d={{ models: [] }} kind="general" mind="MIND" busy={false} onAct={onAct} row={() => null} />));
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('kd-kind-pow').textContent).toContain('●'); expect(q('kd-kind-pos').getAttribute('aria-checked')).toBe('true');
  expect(q('kd-kind-save').disabled).toBe(true);   // nothing changed yet
  await act(async () => q('kd-kind-own-0-g4').click()); await act(async () => q('kd-kind-own-1-ossy').click());
  await act(async () => q('kd-kind-save').click());
  expect(onAct).toHaveBeenLastCalledWith('kind_models', { text: 'pos', brains: ['local/g4', 'local/ossy'] });
  await act(async () => q('kd-kind-pow').click());
  expect(q('kd-kind-drop-0')).toBeTruthy(); await act(async () => q('kd-kind-drop-0').click());
  expect(q('kd-kind-save').textContent).toBe('Back to the pair above');
  await act(async () => q('kd-kind-save').click());
  expect(onAct).toHaveBeenLastCalledWith('kind_models', { text: 'pow', brains: [] });
  act(() => root.unmount()); el.remove();
});
