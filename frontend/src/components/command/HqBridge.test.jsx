import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { HqBridge, HqStyleSwitch, bridgeKpis, groupLines, plain, readHqStyle } from './HqBridge';

const D = { 'money-pulse': { feesTodayUsd: 12.5, fees7dUsd: 80, adminSol: 0.42, checks: [{ key: 'a', label: 'Chain read', ok: false }, { key: 'b', label: 'Fee', ok: true }], alerts: [] },
  security: { score: 92, checks: [{ ok: false }, { ok: true }], stats: { blocklisted: 10, customBadges: 2 }, signals: { forgedSignatures: 0, replays: 1 } },
  traffic: { daily: [{ uniques: 3, views: 5 }, { uniques: 8, views: 14 }], referrers: [{ host: 'x.com', visits: 9 }], topPages24h: [{ page: '/', views: 4 }] },
  latency: { providers: [{ name: 'Jup', ok: true, ms: 300 }, { name: 'Hel', ok: false, ms: 900 }], alarms: [] },
  shield: { counts: { bot: 2, watch: 1 }, scanned: 13 }, bugs: { bugs: [{ status: 'open' }, { status: 'fixed' }] }, numbers: { holders: { count: 7 } }, pulse: { messages24h: 5, fee: { balanceSol: 1, wins: 3, losses: 1, winRate: 75 } } };

test('the band reads every group and never shows a fake zero before data arrives', () => {
  const k = Object.fromEntries(bridgeKpis(D).map(x => [x.k, x]));
  expect(k.fees.value).toBe('$12.5'); expect(k.visits.value).toBe('8'); expect(k.sec.sub).toBe('1 check to fix');
  expect(k.bugs.value).toBe('1'); expect(k.bots.tone).toBe('warn'); expect(k.lag.sub).toBe('1 provider down'); expect(k.lag.tone).toBe('down');
  const empty = Object.fromEntries(bridgeKpis({}).map(x => [x.k, x]));
  expect(empty.bugs.value).toBe('—'); expect(empty.lag.value).toBe('—'); expect(empty.lag.sub).toBe('—'); expect(empty.sec.sub).toBe('—');
});

test('each group gets its own two lines and a chip label never doubles its emoji', () => {
  expect(groupLines('System', D)).toEqual([['Slowest provider', 'Hel · 900 ms'], ['Providers up', '1 of 2']]);
  expect(groupLines('Agents', D)[1][1]).toBe('3–1 · 75%');
  expect(plain("🎩 Sicario's")).toBe("Sicario's"); expect(plain('Fee 🐱')).toBe('Fee'); expect(plain('⚛️ Fuse')).toBe('Fuse');
});

test('the Bridge renders, lists what needs the owner and jumps to a tool', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const went = [];
  const call = async p => D[p.replace('/admin/', '')] || {};
  await act(async () => { root.render(<HqBridge call={call} groups={[['Safety', ['shield', 'bugs'], '🛡', 'safety']]} label={id => id} icon={{}} onGo={id => went.push(id)} />); });
  await act(async () => { await new Promise(r => setTimeout(r, 0)); });
  expect(el.querySelector('[data-testid=hqb-attn]').textContent).toContain('Chain read');
  await act(async () => { el.querySelector('[data-testid=hqb-kpi-bugs]').click(); el.querySelector('.hqb-chip').click(); });
  expect(went).toEqual(['bugs', 'shield']);
  await act(async () => root.unmount()); el.remove();
});

test('the HQ look is saved and read back, and junk falls back to Ops', async () => {
  localStorage.setItem('feeless.hq.style', 'nope'); expect(readHqStyle()).toBe('ops');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); let v = 'ops';
  await act(async () => { root.render(<HqStyleSwitch value={v} onChange={x => { v = x; }} />); });
  await act(async () => { [...el.querySelectorAll('button')].find(b => b.textContent === 'Ledger').click(); });
  expect(v).toBe('ledger'); expect(readHqStyle()).toBe('ledger');
  await act(async () => root.unmount()); el.remove(); localStorage.removeItem('feeless.hq.style');
});
