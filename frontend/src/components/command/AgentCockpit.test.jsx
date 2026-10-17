import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { AgentCockpit, huntSplit } from './AgentCockpit';
import { AiKeyBox } from './AiKeyBox';
import { AiProviders, aiChip } from './AiProviders';
import { AgentHubProvider, selectors, hubReset } from '../../lib/agentHub';
import { D } from './__fixtures__/cockpit';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const charts = [];
jest.mock('../terminal/PriceChart', () => ({ PriceChart: props => { charts.push(props); return <div data-testid="price-chart" data-metric={props.metric} />; } }));   // canvas-free
jest.mock('../CoinDrawer', () => ({ openCoin: jest.fn() }));
const AGENTS = ['tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden', 'courier', 'reaper', 'archivist', 'judge'].map(k => ({ key: k, name: k[0].toUpperCase() + k.slice(1), icon: '•', job: `${k} job` }));
const AI = { providers: [{ key: 'local', label: 'LOCAL LM STUDIO', priority: 1, enabled: true, state: 'ONLINE', model: 'qwen2.5-7b-instruct-mlx', host: '127.0.0.1', lastMs: 42, requests: 3, failures: 0 },
  { key: 'groq', label: 'GROQ', priority: 2, enabled: true, state: 'KEY MISSING', why: 'KEY MISSING', model: 'llama-3.1-8b-instant', requests: 0, failures: 0 }],
  order: ['local', 'groq'], totals: { asked: 3, answered: 3, fallbacks: 0, cached: 0, none: 0 }, never: ['tally', 'trigger', 'reaper', 'courier', 'warden'],
  notes: { MINTZYN: { devil: { source: 'local', label: 'LOCAL AI', advice: { stance: 'WAIT', priority: 60, summary: 'Identity warning — wait for a site.' } } } } };
const data = { ...D, office: { ...D.office, agents: AGENTS, ai: AI, generations: AGENTS.map(a => ({ role: a.key, generation: 2, status: 'ACTIVE', netImpact: a.key === 'reaper' ? 1.5 : null })),
  deskStats: { reaper: { accuracy: 61, winResp: 5, lossResp: 2 } } } };
const flush = () => act(async () => { await new Promise(r => setTimeout(r, 0)); });
const pickSel = (s, v) => { Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(s, v); s.dispatchEvent(new Event('change', { bubbles: true })); };

function mount() {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  return { el, root, q: id => document.querySelector(`[data-testid="${id}"]`) };
}
afterEach(() => { hubReset(); charts.length = 0; document.body.innerHTML = ''; });

test('the cockpit, laid out like the reference: ribbon → 4 seats → MC chart + live decisions | decision panel → matrix | review queue → operator controls', async () => {
  const call = jest.fn(async path => (path === '/admin/ai/providers' ? AI : { ok: true, owner: { mint: 'MINTNEW', list: [...D.office.ownerReview, { mint: 'MINTNEW00000000000000000000000000000000pump', symbol: 'NEW', mode: 'arm', state: 'RESOLVING', why: 'waiting for the next agent pass', pending: [] }] } }));
  const hub = { d: data, livePx: new Map(), sel: selectors(data), load: jest.fn() };
  const { el, root, q } = mount();
  await act(async () => { root.render(<AgentHubProvider value={hub}><AgentCockpit call={call} /></AgentHubProvider>); });
  await flush();
  const order = [...q('agent-cockpit').children].map(c => c.getAttribute('data-testid') || c.className);
  expect(order).toEqual(['ack-money', 'ack-topseats', 'ack-main', 'ack-deckwrap']);   // 🪑 the seats across the top   // 💵 one sticky strip, the chart, then ONE pane behind the nav expect(q('ack-ops')).not.toBeNull();   // one deck under the chart (one pane at a time)
  expect([...q('ack-money').querySelectorAll('.ack-nav > [role=tab]')].map(b => b.getAttribute('data-testid'))).toEqual(['ack-nav-chart', 'ack-deck-seats', 'ack-deck-you', 'ack-deck-live', 'ack-deck-tape', 'ack-deck-review', 'ack-deck-controls', 'ack-deck-stats']);
  // 💵 the ribbon: the card's own numbers
  for (const k of ['putin', 'equity', 'net', 'phase', 'be', 'lives', 'occ', 'cycle', 'last', 'cash', 'keeper', 'exec']) expect(q(`ack-rt-${k}`)).not.toBeNull();
  expect(q('ack-rt-putin').textContent).toContain('$32.50'); expect(q('ack-rt-phase').textContent).toContain('RECOVERY'); expect(q('ack-rt-keeper').textContent).toContain('1 ACTIVE');
  expect(q('ack-rt-exec').textContent).toContain('HEALTHY'); expect(q('ack-rt-occ').textContent).toContain('2 / 3');
  // 🪑 seats in the reference's words
  expect(q('ack-seat-state-1').textContent).toBe('PROTECT'); expect(q('ack-seat-state-2').textContent).toBe('ARMED'); expect(q('ack-seat-state-3').textContent).toBe('HUNTING');
  expect(q('ack-seat-1').textContent).toContain('$CARLO'); expect(q('ack-seat-1').textContent).toContain('$857.0K');
  expect(q('ack-seat-pct-1').textContent).toBe('+17.4%'); expect(q('ack-seat-usd-1').textContent).toBe('+$0.06'); expect(q('ack-seat-last-1').textContent).toContain('Reaper · PROTECT');
  expect(q('ack-seat-now-1').textContent).toContain('R7 trail'); expect(q('ack-seat-mc-2').textContent).toBe('—');                    // unknown = —, never $0
  expect(q('ack-seat-bar-1')).not.toBeNull(); expect(q('ack-seat-bar-1').getAttribute('data-tip')).toContain('peak +20%');              // 💹 each seat: stop … now … peak … take
  expect(q('ack-trade-peak').textContent).toContain('PEAK +20%'); expect(q('ack-trade-peak').textContent).toContain('gave back 2.7');   // the HUD on the chart
  expect(q('ack-trade-usd')).not.toBeNull(); expect(q('ack-trade-held').textContent).toMatch(/\dm \d\ds|\d\.\dh/);
  expect(q('ack-seat-3').textContent).toContain('1 READY candidate');
  // 📊 market cap is the chart's language; real events lettered T D W B R X
  const last = () => charts[charts.length - 1];
  expect(q('price-chart').getAttribute('data-metric')).toBe('marketCap'); expect(last().pair.marketCap).toBeCloseTo(1_006_000);
  expect(last().fuse.lines.map(l => l.title)).toEqual(['entry', 'take +50%', 'stop -15%', 'peak +20.1%']);
  expect(last().markers).toHaveLength(1); expect(last().markers[0].shape).toBe('arrowUp'); expect(last().markers[0].text).toBe('');   // only the real fill, no letters expect(q('ack-chart-mc').textContent).toBe('$1.01M');
  expect(q('ack-mrail').textContent).toContain('Trigger enter'); expect(q('ack-mk-3').getAttribute('data-tip')).toContain('Reaper · PROTECT');
  expect(q('ack-iv-5m').parentElement.className).toContain('ack-iv');                                                              // the candle selector is one horizontal seg
  // ⚡ live decisions: newest first
  expect(q('ack-tape').querySelectorAll('.ack-tcard')).toHaveLength(4); expect(q('ack-tape').querySelector('.ack-tcard').textContent).toContain('HARD VETO');
  // 🧠 the panel: the agent controlling the seat (Reaper) by default
  expect(q('ack-agent-sel').value).toBe('reaper'); expect(q('ack-verdict').textContent).toBe('PROTECT'); expect(q('ack-kernel-verdict').textContent).toBe('PROTECT');
  for (const k of ['live', 'inputs', 'seats', 'review', 'trace']) expect(q(`ack-ptab-${k}`)).not.toBeNull();
  await act(async () => { q('ack-ptab-inputs').click(); });
  expect(q('ack-pane-inputs').textContent).toMatch(/price/); expect(q('ack-pane-inputs').textContent).toMatch(/LIVE|FRESH|PARTIAL|STALE|PENDING|UNAVAILABLE/);
  await act(async () => { q('ack-ptab-seats').click(); });
  expect(q('ack-pane-seats').querySelectorAll('tbody tr')).toHaveLength(3);
  await act(async () => { q('ack-ptab-trace').click(); });
  expect(q('ack-pane-trace').querySelectorAll('li[data-testid^="ack-tr-"]')).toHaveLength(10); expect(q('ack-tr-reaper').textContent).toContain('PROTECT');
  await act(async () => { q('ack-ptab-live').click(); });
  // a queue row → its chart + the desk standing in its way; the AI note is shown with its source, advisory only
  await act(async () => { q('ack-q-ZYN').click(); });
  expect(q('ack-kernel-verdict').textContent).toBe('🟢 READY'); expect(last().pair.marketCap).toBe(400000); expect(last().fuse.lines).toEqual([]);
  expect(q('ack-qmc-ZYN').textContent).toBe('$400.0K'); expect(q('ack-qst-ZYN').textContent).toBe('READY');
  await act(async () => { pickSel(q('ack-agent-sel'), 'devil'); });
  expect(q('ack-ai-note').textContent).toContain('LOCAL AI'); expect(q('ack-ai-note').textContent).toContain('Identity warning');
  await act(async () => { q('ack-q-PLAIN').click(); });                                                                               // no supply → no price chart in its place
  expect(q('ack-mc-unavailable')).not.toBeNull(); expect(q('price-chart')).toBeNull();
  // 🤖 ten agents: tap = panel focus + its tape lines; records only when real
  expect(q('ack-matrix').querySelectorAll('.ack-agent')).toHaveLength(10);
  expect(q('ack-rec-reaper').textContent).toBe('61% · 5W 2L'); expect(q('ack-rec-tally').textContent).toBe('no real record yet');
  await act(async () => { q('ack-agent-reaper').click(); });
  expect(q('ack-agent-sel').value).toBe('reaper'); expect(q('ack-tape').querySelectorAll('.ack-tcard')).toHaveLength(1);
  await act(async () => { q('ack-tape-all-agents').click(); });
  await act(async () => { q('ack-tape-more').click(); });
  expect(q('ack-tape').querySelectorAll('.ack-trow')).toHaveLength(4);
  // 👤 owner review only edits the owner's list (no order, no quote)
  expect(q('ack-own-list').textContent).toContain('$REV'); expect(q('ack-act-arm').disabled).toBe(true);
  const input = q('ack-intake'); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  await act(async () => { set.call(input, 'https://pump.fun/coin/MINTNEW00000000000000000000000000000000pump'); input.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { q('ack-act-arm').click(); });
  expect(call).toHaveBeenCalledWith('/admin/agents', { method: 'POST', body: JSON.stringify({ owner: { input: 'https://pump.fun/coin/MINTNEW00000000000000000000000000000000pump', action: 'arm' } }) });
  await act(async () => { q('ack-own-ignore-MINTRE').click(); });
  expect(call).toHaveBeenLastCalledWith('/admin/agents', { method: 'POST', body: JSON.stringify({ owner: { input: 'MINTREV', action: 'ignore' } }) });
  // 🎛 operator controls: the creator's own limits on the same cfg path
  expect(q('ack-op-agentSl').getAttribute('data-value')).toBe('25'); expect(q('ack-op-agentSl-25').getAttribute('aria-checked')).toBe('true');
  expect(q('ack-op-agentSl').className).toContain('is-you'); expect(q('ack-op-agentTp').textContent).toContain('AGENTS');           // who decides it, on the row
  expect(q('ack-op-agentTp-50').textContent).toBe('+50%'); expect(q('ack-op-agentSl-15').textContent).toBe('−15%');
  await act(async () => { q('ack-op-agentTp-50').click(); });
  expect(call).toHaveBeenCalledWith('/admin/agents', { method: 'POST', body: JSON.stringify({ cfg: { agentTp: 50 } }) });
  expect(q('acx-band-word').textContent).toBe('$12K–$300K'); expect(q('acx-band').querySelectorAll('.acx-dot').length).toBeGreaterThan(0);   // the band + this pass's coins on it
  await act(async () => { q('ack-op-agentMcMax-500000').click(); });
  expect(call).toHaveBeenCalledWith('/admin/agents', { method: 'POST', body: JSON.stringify({ cfg: { agentMcMax: 500000 } }) });
  expect(q('acx-model')).not.toBeNull(); expect(q('ack-op-agentAiLearn-on').getAttribute('aria-checked')).toBe('true');
  expect(call.mock.calls.every(([, o]) => !/"(buy|sell|swap|quote|order)"/.test(o?.body || ''))).toBe(true);                       // nothing here trades
  // 🧠 AI chip → the providers sheet
  expect(q('ack-aichip').textContent).toContain('LOCAL ● 42ms');
  await act(async () => { q('ack-aichip').click(); });
  await flush();
  expect(q('ai-providers')).not.toBeNull(); expect(q('aip-state-local').textContent).toBe('ONLINE'); expect(q('aip-state-groq').textContent).toBe('KEY MISSING');
  await act(async () => { q('aip-close').click(); });
  expect(q('ai-providers')).toBeNull();
  expect(el.textContent).not.toMatch(/undefined|NaN|expected move|est\. time/i);                                                     // nothing invented, no broken labels
  await act(async () => { root.unmount(); });
});

test('⚡ an agent pulses ONLY when a new real tape event of its own arrives — never on first paint, never on a timer', async () => {
  localStorage.setItem('feeless.agentDeck', 'agents');   // an old saved Desk tab opens ⚡ Live desk (the desk lives there now) (a hidden pane is frozen: it skips live updates until opened)
  const hub = { d: data, livePx: new Map(), sel: selectors(data), load: jest.fn() };
  const { root, q } = mount(); const call = jest.fn(async () => ({}));
  const fetchSpy = jest.fn(); const realFetch = global.fetch; global.fetch = fetchSpy;                                              // the 30fps glide is display only: no market / RPC request of its own
  await act(async () => { root.render(<AgentHubProvider value={hub}><AgentCockpit call={call} /></AgentHubProvider>); });
  expect(q('ack-matrix').querySelectorAll('.is-pulse')).toHaveLength(0);
  const d2 = { ...data, office: { ...data.office, tape: [...data.office.tape, { id: 9, at: 1100, agent: 'warden', action: 'SIZE $0.20', why: 'tier B', mint: 'MINTZYN', symbol: 'ZYN' }] } };
  await act(async () => { root.render(<AgentHubProvider value={{ ...hub, d: d2, sel: selectors(d2) }}><AgentCockpit call={call} /></AgentHubProvider>); });
  expect(q('ack-agent-warden').querySelector('.is-pulse')).not.toBeNull(); expect(q('ack-agent-devil').querySelector('.is-pulse')).toBeNull();
  expect(fetchSpy.mock.calls.filter(([u]) => !String(u).includes('/api/reputation/edge'))).toHaveLength(0); global.fetch = realFetch;   // only the shared coin-edge poller (🦠 germ chips) may ask
  await act(async () => { root.unmount(); });
  localStorage.setItem('feeless.agentDeck', 'live');   // ⚡ the feed open: the new tape line is marked new
  const b = mount();
  await act(async () => { b.root.render(<AgentHubProvider value={hub}><AgentCockpit call={call} /></AgentHubProvider>); });
  await act(async () => { b.root.render(<AgentHubProvider value={{ ...hub, d: d2, sel: selectors(d2) }}><AgentCockpit call={call} /></AgentHubProvider>); });
  expect(b.q('ack-tape-9').className).toContain('is-new');
  await act(async () => { b.root.unmount(); });
  localStorage.removeItem('feeless.agentDeck');
});

test('🧠 AI providers: order / on-off / test go to the server; the page never holds a key', async () => {
  const calls = [];
  const call = jest.fn(async (path, opts) => { calls.push([path, opts?.body]); return path === '/admin/ai/test' ? { ...AI, ok: true, ms: 40 } : AI; });
  const { root, q } = mount(); const close = jest.fn();
  await act(async () => { root.render(<AiProviders call={call} ai={AI} close={close} />); });
  await flush();
  await act(async () => { q('aip-down-local').click(); });
  expect(calls).toContainEqual(['/admin/ai/providers', JSON.stringify({ order: ['groq', 'local'] })]);
  await act(async () => { q('aip-on-groq').click(); });
  expect(calls).toContainEqual(['/admin/ai/providers', JSON.stringify({ enabled: { groq: false } })]);
  await act(async () => { q('aip-test-local').click(); });
  expect(calls).toContainEqual(['/admin/ai/test', JSON.stringify({ provider: 'local' })]);
  await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); }); expect(close).toHaveBeenCalled();
  expect(aiChip(null).parts[0][1]).toBe('not loaded'); expect(aiChip({ providers: [{ key: 'local', label: 'LOCAL', enabled: true, state: 'OFFLINE' }] }).cls).toBe('is-off');
  await act(async () => { root.unmount(); });
});

test('🔑 AI key box: tests and saves through the server, shows only set + the last 4, never the key', async () => {
  const status = { providers: [{ key: 'openai', label: 'OpenAI', set: false, hint: null, active: false }, { key: 'anthropic', label: 'Anthropic', set: false }, { key: 'custom', label: 'Any OpenAI-compatible', set: false, hint: null, active: false }], active: null, note: 'Advisory only.' };
  const saved = { ...status, ok: true, ms: 140, models: ['gpt-4o-mini'], active: 'openai', model: 'gpt-4o-mini', providers: [{ ...status.providers[0], set: true, hint: '…wxyz', active: true }, status.providers[2]] };
  const call = jest.fn(async (path, opts) => (opts ? saved : status));
  const { el, root, q } = mount();
  await act(async () => { root.render(<AiKeyBox call={call} />); });
  await flush();
  expect(q('ai-key-anthropic')).toBeNull();                                                                                         // only providers the router can use
  expect(q('ai-key-input').getAttribute('type')).toBe('password'); expect(q('ai-key-save').disabled).toBe(true);
  await act(async () => { q('ai-prov-openai').click(); });
  const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; const KEY = 'sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789wxyz';
  await act(async () => { set.call(q('ai-key-input'), KEY); q('ai-key-input').dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { set.call(q('ai-key-model'), 'gpt-4o-mini'); q('ai-key-model').dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { q('ai-key-save').click(); });
  expect(call).toHaveBeenLastCalledWith('/admin/ai-key', { method: 'POST', body: JSON.stringify({ provider: 'openai', key: KEY, model: 'gpt-4o-mini' }) });
  expect(q('ai-key-input').value).toBe(''); expect(el.textContent).not.toContain(KEY); expect(q('ai-key-openai').textContent).toContain('set …wxyz');
  expect(q('ai-key-models').textContent).toContain('gpt-4o-mini');
  await act(async () => { q('ai-prov-custom').click(); });
  expect(q('ai-key-base')).not.toBeNull();
  await act(async () => { q('ai-key-clear-openai').click(); });
  expect(call).toHaveBeenLastCalledWith('/admin/ai-key', { method: 'POST', body: JSON.stringify({ provider: 'openai', clear: true }) });
  await act(async () => { root.unmount(); });
});

test('🗂 one deck: ⚡ Live open by default, the Brain its own pane; 👑 Coach and 🎓 Teach live INSIDE the Brain', async () => {
  const call = jest.fn(async () => ({ ok: true }));
  const hub = { d: data, livePx: new Map(), sel: selectors(data), load: jest.fn() };
  const { root, q } = mount();
  await act(async () => { root.render(<AgentHubProvider value={hub}><AgentCockpit call={call} /></AgentHubProvider>); });
  await flush();
  expect(q('ack-deck-coach')).toBeNull(); expect(q('ack-deckpane-live').hidden).toBe(false); expect(q('ack-brain-drawer')).toBeNull();
  await act(async () => { q('ack-brain-open').click(); }); expect(q('ack-brain-drawer')).not.toBeNull(); expect(q('ack-deckpane-live').hidden).toBe(false);   // 🧠 the Brain slides out; the page stays
  expect(q('cch-extra-coach').hidden).toBe(true); expect(q('cch-extra-coach').children.length).toBeGreaterThan(0);
  await act(async () => { q('cch-pane-coach').click(); });
  expect(q('cch-extra-coach').hidden).toBe(false); expect(q('cch-modes').closest('.cch-talkpane').hidden).toBe(true);   // Talk stays mounted (hidden): no remount glitch
  await act(async () => { q('cch-pane-talk').click(); });
  expect(q('cch-extra-coach').hidden).toBe(true);
});

test('📡 an empty seat reads its blocker as a headline + its numbers', () => {
  expect(huntSplit('cleared but on the rebuy cooldown: $BUPE · 0 of 14 case files clear')).toEqual(['cleared but on the rebuy cooldown', '$BUPE · 0 of 14 case files clear']);
  expect(huntSplit('')).toEqual(['waiting for a coin that clears every check', '']);
  expect(huntSplit('no colon here')).toEqual(['no colon here', '']);
});

test('📣 chart callouts: only the models\' calls on THIS coin, newest 3 first', () => {
  const { chartCalls } = require('./AgentCockpit');
  const rows = [{ mint: 'A', at: 1, cap: 10 }, { mint: 'B', at: 2, cap: 10 }, { mint: 'A', at: 3, cap: 0 }, { mint: 'A', at: 4, cap: 9, model: 'OSSY', action: 'BUY' }, { mint: 'A', at: 5, cap: 9, talk: true, view: 'SELL' }];
  expect(chartCalls(rows, 'A').map(r => r.at)).toEqual([1, 4, 5]); expect(chartCalls(rows, 'A')[1]).toMatchObject({ icon: 'OS', action: 'BUY', kind: 'ai' });
  expect(chartCalls(rows, 'A')[2]).toMatchObject({ action: 'TALK', kind: 'talk' }); expect(chartCalls(null, 'A')).toEqual([]);
});

test('🖼 avatars: OSSY / G4 use the owner\'s pictures, each agent its own GIF, agent pins need a cap', () => {
  const { avatarOf } = require('../../lib/aiAvatars'); const { agentPins } = require('./AgentCockpit');
  expect(avatarOf('OSSY')).toMatch(/ossy\.webp$/); expect(avatarOf('lan')).toMatch(/g4\.webp$/); expect(avatarOf('reaper')).toMatch(/reaper\.gif$/); expect(avatarOf('bob')).toBe(null);
  const p = agentPins([{ id: 1, agent: 'reaper', action: 'hold', mc: 90000, at: 5, why: 'w' }, { id: 2, agent: 'reaper', mc: null, at: 6 }]);
  expect(p).toHaveLength(1); expect(p[0]).toMatchObject({ who: 'Reaper', cap: 90000, action: 'HOLD', kind: 'agent' });
});

test('✋ / 👍 one click on a seat posts the hint', async () => {
  const { SeatHints } = require('./AgentCockpit');
  const { createRoot } = require('react-dom/client'); const { act } = require('react');
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const sent = []; const call = (_p, o) => { sent.push(JSON.parse(o.body)); return Promise.resolve({}); };
  act(() => root.render(<SeatHints s={{ seat: 2, mint: 'M' }} call={call} />));
  await act(async () => { el.querySelector('[data-testid="ack-hint-hold-2"]').click(); });
  expect(sent[0]).toEqual({ seatHint: { mint: 'M', kind: 'hold' } });
  expect(el.querySelector('[data-testid="ack-hint-hold-2"]').getAttribute('aria-pressed')).toBe('true');
  act(() => root.unmount());
});
