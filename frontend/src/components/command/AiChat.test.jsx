import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { AiChat, metaLine, CHAT_MODES, DataChip } from './AiChat';

jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const mockHub = { hubApply: jest.fn(), hubLoad: jest.fn() };
jest.mock('../../lib/agentHub', () => ({ hubApply: (...a) => mockHub.hubApply(...a), hubLoad: (...a) => mockHub.hubLoad(...a), useAi: x => x, useAgentHub: () => ({}) }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); return el; };
const q = (el, id) => el.querySelector(`[data-testid="${id}"]`);
const type = async (el, v) => { const i = q(el, 'cch-input'); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; await act(async () => { set.call(i, v); i.dispatchEvent(new Event('input', { bubbles: true })); }); };
const P = { id: 'p1', agent: 'trigger', kind: 'cfg', key: 'chartWait', old: false, new: true, reason: 'WAIT charts lost 13%', effect: 'fewer bad entries', rollback: 'flip the same switch back', status: 'pending' };

test('💬 chat: three modes, a normal-language answer with provider · model · latency · tokens, Clear — and only this panel is patched', async () => {
  const call = jest.fn(async (path, opt) => {
    if (!opt) return { history: [], proposals: { pending: [], decided: [] } };
    if (path === '/admin/ai/chat/clear') return { history: [] };
    return { ok: true, mode: 'chat', reply: 'Reaper banks winners at about +2%.', provider: 'OPENROUTER', model: 'gpt-x', ms: 4200, tokens: { in: 900, out: 60 },
      history: [{ role: 'user', text: 'why small wins?' }, { role: 'assistant', text: 'Reaper banks winners at about +2%.' }], proposals: { pending: [], decided: [] } };
  });
  const el = await mount(<AiChat call={call} focus="M1" focusSym="AAA" />);
  expect(CHAT_MODES.map(m => m[0])).toEqual(['chat', 'case', 'improve', 'build']); expect(q(el, 'cch-send').disabled).toBe(true);
  await type(el, 'why small wins?'); await act(async () => { q(el, 'cch-send').click(); });
  expect(call).toHaveBeenCalledWith('/admin/ai/chat', expect.objectContaining({ method: 'POST', body: JSON.stringify({ text: 'why small wins?', mode: 'chat', focus: 'M1', provider: 'auto' }) }));
  expect(q(el, 'cch-log').textContent).toContain('Reaper banks winners at about +2%.'); expect(q(el, 'cch-log').textContent).not.toContain('"stance"');
  expect(q(el, 'cch-meta').textContent).toBe('OPENROUTER · gpt-x · 4.2s · 900→60 tok');
  expect(mockHub.hubApply).not.toHaveBeenCalled(); expect(mockHub.hubLoad).not.toHaveBeenCalled();   // no full-tab repaint: the answer lives in this panel
  expect(q(el, 'cch-mood').dataset.mood).toBe('on'); expect(q(el, 'cch-mood').textContent).toContain('LOCKED IN');
  await act(async () => { q(el, 'cch-clear').click(); }); expect(q(el, 'cch-log').textContent).toContain('Fixes only on your');
  expect(metaLine({ provider: 'LOCAL AI' })).toBe('LOCAL AI'); expect(metaLine(null)).toBe('');
});

test('🛠 a proposal shows agent · now → proposed · why · effect · rollback, and only Approve / Reject call the backend', async () => {
  const sent = [];
  const call = jest.fn(async (path, opt) => {
    if (!opt) return { history: [], proposals: { pending: [P], decided: [] } };
    sent.push([path, JSON.parse(opt.body)]);
    return { ok: true, applied: 'chartWait: False → True', proposals: { pending: [], decided: [{ ...P, status: JSON.parse(opt.body).approve ? 'approved' : 'rejected', applied: JSON.parse(opt.body).approve ? 'chartWait: False → True' : undefined }] } };
  });
  const el = await mount(<AiChat call={call} />);
  const card = q(el, 'cch-prop-p1').textContent;
  ['TRIGGER', 'chartWait', 'NOW', 'OFF', 'PROPOSED', 'ON', 'WAIT charts lost 13%', 'fewer bad entries', 'flip the same switch back'].forEach(w => expect(card).toContain(w));
  expect(sent).toHaveLength(0);                                                                // showing a proposal applies nothing
  await act(async () => { q(el, 'cch-approve-p1').click(); });
  expect(sent).toEqual([['/admin/ai/proposals/decide', { id: 'p1', approve: true }]]);
  expect(q(el, 'cch-prop-p1')).toBeNull(); await act(async () => { q(el, 'cch-done').click(); });   // decided fixes fold under one line
  expect(q(el, 'cch-prop-p1').textContent).toContain('APPROVED'); expect(q(el, 'cch-prop-p1').textContent).toContain('chartWait: False → True'); expect(q(el, 'cch-approve-p1')).toBeNull();
  const el2 = await mount(<AiChat call={call} />);
  await act(async () => { q(el2, 'cch-reject-p1').click(); });
  expect(sent[1]).toEqual(['/admin/ai/proposals/decide', { id: 'p1', approve: false }]); await act(async () => { q(el2, 'cch-done').click(); }); expect(q(el2, 'cch-prop-p1').textContent).toContain('REJECTED');
});

test('🧠 the Brain learns on your tap, deletes one message, fires a one-tap prompt and pops out full-window', async () => {
  const sent = [];
  const H = [{ role: 'user', text: 'why small wins?' }, { role: 'assistant', text: 'The trail arms at +4% and banks near +2%.' }];
  const call = jest.fn(async (path, opt) => {
    if (!opt) return { history: H, proposals: { pending: [], decided: [] }, learned: 3, brain: { provider: 'OPENROUTER', model: 'gpt-x', ms: 4000 } };
    sent.push([path, JSON.parse(opt.body)]);
    if (path === '/admin/ai/chat/remember') return { ok: true, learned: 4 };
    if (path === '/admin/ai/chat/clear') return { history: H.slice(1), learned: 4 };
    return { ok: true, mode: 'improve', reply: 'ok', history: H, proposals: { pending: [], decided: [] } };
  });
  const el = await mount(<AiChat call={call} variant="mini" />);
  expect(q(el, 'cch').className).toContain('is-mini'); expect(q(el, 'cch-learned').textContent).toContain('3'); expect(q(el, 'cch-mood').textContent).toContain('OPENROUTER · gpt-x · 4.0s');
  expect(q(el, 'cch-rem-0')).toBeNull();                                                        // only the model's lines can be remembered
  await act(async () => { q(el, 'cch-rem-1').click(); });
  expect(sent[0]).toEqual(['/admin/ai/chat/remember', { text: 'The trail arms at +4% and banks near +2%.' }]); expect(q(el, 'cch-learned').textContent).toContain('4');
  await act(async () => { q(el, 'cch-del-0').click(); });
  expect(sent[1]).toEqual(['/admin/ai/chat/clear', { index: 0, mode: 'chat' }]); expect(q(el, 'cch-log').textContent).not.toContain('why small wins?');
  await act(async () => { q(el, 'cch-mode-improve').click(); });
  await act(async () => { q(el, 'cch-quick').querySelector('button').click(); });
  expect(sent[2][0]).toBe('/admin/ai/chat'); expect(sent[2][1].mode).toBe('improve'); expect(sent[2][1].text).toMatch(/Propose the changes/);
  await act(async () => { q(el, 'cch-pop').click(); });
  expect(document.querySelector('[data-testid="cch-shade"] .cch.is-pop')).not.toBeNull(); expect(q(el, 'cch-popped')).not.toBeNull();
  await act(async () => { document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); });
  expect(document.querySelector('[data-testid="cch-shade"]')).toBeNull();
  expect(mockHub.hubApply).not.toHaveBeenCalled();
});

test('🧠 no HQ session = the Brain says how to sign in and asks nothing; brainMood reads real state', async () => {
  const { MiniBrain } = require('../MiniBrain'); const { brainMood } = require('./AiChat');
  localStorage.removeItem('feeless:cc-session');
  const el = await mount(<MiniBrain address="CREATOR" />);
  expect(q(el, 'mini-brain-gate').textContent).toMatch(/Open HQ once/); expect(q(el, 'mini-brain')).toBeNull();
  expect((await mount(<MiniBrain address={null} />)).textContent).toBe('');
  expect(brainMood(true, null, null).key).toBe('work'); expect(brainMood(false, null, null).key).toBe('off'); expect(brainMood(false, { provider: 'LOCAL AI' }, null).line).toBe('LOCAL AI');
});

test('🛠 in the mini cat the fixes sit folded under one bar until you open them', async () => {
  const call = jest.fn(async () => ({ history: [], proposals: { pending: [P], decided: [] } }));
  const el = await mount(<AiChat call={call} variant="mini" />);
  expect(q(el, 'cch-props-toggle').textContent).toContain('· 1'); expect(q(el, 'cch-props').querySelector('ul').hidden).toBe(true);
  await act(async () => { q(el, 'cch-props-toggle').click(); });
  expect(q(el, 'cch-props').querySelector('ul').hidden).toBe(false); expect(q(el, 'cch-approve-p1')).not.toBeNull();
});

test('🧵 each mode has its own thread; 🧱 Build this queues a line (the tap is the permission) and the build queue shows in Build mode', async () => {
  const sent = [];
  const B = { open: 1, items: [{ id: 'b1', title: 'Judge meter', text: 'a live meter', status: 'queued' }] };
  const call = jest.fn(async (path, opt) => {
    if (opt) sent.push([path, JSON.parse(opt.body)]);
    if (path === '/admin/ai/build') return { ok: true, build: { open: 2, items: [{ id: 'b2', title: 'Rug meter', text: 'x', status: 'queued' }, ...B.items] } };
    return { threads: { chat: [{ role: 'user', text: 'chat thread q' }, { role: 'assistant', text: 'chat thread answer' }], case: [], improve: [], build: [{ role: 'assistant', text: 'build a rug meter on seats' }] },
      build: B, proposals: { pending: [], decided: [] } };
  });
  const el = await mount(<AiChat call={call} />);
  await act(async () => { await Promise.resolve(); });
  expect(q(el, 'cch-log').textContent).toContain('chat thread answer'); expect(q(el, 'cch-bq').textContent).toContain('1');
  await act(async () => { q(el, 'cch-mode-build').click(); });
  expect(q(el, 'cch-log').textContent).toContain('build a rug meter'); expect(q(el, 'cch-log').textContent).not.toContain('chat thread answer');
  expect(q(el, 'cch-bqlist').textContent).toContain('Judge meter');
  await act(async () => { q(el, 'cch-build-0').click(); });
  expect(sent[0][0]).toBe('/admin/ai/build'); expect(sent[0][1].text).toBe('build a rug meter on seats');
  expect(q(el, 'cch-bq').textContent).toContain('2'); expect(q(el, 'cch-bqlist').textContent).toContain('Rug meter');
});

test('🎛 model switch rides the message; ✏ edit rewinds the thread and puts the words back; the pop-out sits above HQ', async () => {
  const sent = [];
  const call = jest.fn(async (path, opt) => {
    if (opt) sent.push([path, JSON.parse(opt.body)]);
    if (path === '/admin/ai/chat/clear') return { threads: { chat: [] } };
    if (opt) return { ok: true, mode: 'chat', reply: 'ok', threads: { chat: [{ role: 'user', text: 'q' }, { role: 'assistant', text: 'ok' }] } };
    return { threads: { chat: [{ role: 'user', text: 'old question' }, { role: 'assistant', text: 'old answer' }] }, providers: [{ key: 'openrouter', label: 'OPENROUTER', state: 'ONLINE', model: 'openai/gpt-x' }], proposals: { pending: [], decided: [] } };
  });
  const el = await mount(<AiChat call={call} />);
  await act(async () => { await Promise.resolve(); });
  const sel = q(el, 'cch-model'); expect(sel.textContent).toContain('OPENROUTER');
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(sel, 'openrouter'); sel.dispatchEvent(new Event('change', { bubbles: true })); });
  await act(async () => { q(el, 'cch-edit-0').click(); });
  expect(sent[0]).toEqual(['/admin/ai/chat/clear', { mode: 'chat', from: 0 }]); expect(q(el, 'cch-input').value).toBe('old question');
  await act(async () => { q(el, 'cch-send').click(); });
  expect(sent[1][1]).toMatchObject({ text: 'old question', provider: 'openrouter' });
  localStorage.removeItem('feeless.brainProv');
});

test('⚙ settings save listed values; 🗂 a saved conversation reopens into its mode', async () => {
  const sent = [];
  const call = jest.fn(async (path, opt) => {
    if (opt) sent.push([path, JSON.parse(opt.body)]);
    if (path === '/admin/ai/chat/open') return { mode: 'build', threads: { build: [{ role: 'user', text: 'the old build talk' }] }, saved: [] };
    if (path === '/admin/ai/chat/settings') return { settings: { temp: 0.9, len: 'normal', allowSmall: false } };
    return { threads: { chat: [] }, saved: [{ id: 'c1', mode: 'build', title: 'the old build talk', at: 1, n: 2 }], settings: { temp: 0.3, len: 'normal', allowSmall: false }, proposals: { pending: [], decided: [] } };
  });
  const el = await mount(<AiChat call={call} />);
  await act(async () => { await Promise.resolve(); });
  await act(async () => { q(el, 'cch-set').click(); });
  await act(async () => { q(el, 'cch-temp-0.9').click(); });
  expect(sent[0]).toEqual(['/admin/ai/chat/settings', { temp: 0.9 }]); expect(q(el, 'cch-temp-0.9').className).toContain('active');
  const sel = q(el, 'cch-saved');
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(sel, 'c1'); sel.dispatchEvent(new Event('change', { bubbles: true })); });
  expect(sent[1]).toEqual(['/admin/ai/chat/open', { id: 'c1' }]); expect(q(el, 'cch-log').textContent).toContain('the old build talk');
  expect(q(el, 'cch-mode-build').getAttribute('aria-checked')).toBe('true');
});

test('🎨 draw: the text in the box becomes a picture in this thread; the provider refusal is shown as it is', async () => {
  const sent = []; let fail = false;
  const call = jest.fn(async (path, opt) => {
    if (opt) sent.push([path, JSON.parse(opt.body)]);
    if (path === '/admin/ai/image') { if (fail) throw new Error('🎨 This request requires at least $1.00 in balance'); return { mode: 'chat', usd: 0.04, threads: { chat: [{ role: 'user', text: '🎨 neon atom' }, { role: 'assistant', text: 'here it is', meta: { img: '/api/reputation/uploads/a.png' } }] } }; }
    return { threads: { chat: [] }, proposals: { pending: [], decided: [] } };
  });
  const el = await mount(<AiChat call={call} />);
  await type(el, 'neon atom'); await act(async () => { q(el, 'cch-draw').click(); });
  expect(sent[0]).toEqual(['/admin/ai/image', { prompt: 'neon atom', mode: 'chat' }]); expect(el.querySelector('.cch-img').getAttribute('src')).toBe('/api/reputation/uploads/a.png');
  fail = true; await type(el, 'another'); await act(async () => { q(el, 'cch-draw').click(); });
  expect(q(el, 'cch-log').textContent).toContain('$1.00');
});

test('🧵 no glitch: a mode switch never replays the thread, Talk stays mounted behind Coach, fixes fold outside 🛠 / 🧱', async () => {
  const hist = [{ role: 'user', text: 'one?' }, { role: 'assistant', text: 'answer one here' }];
  const call = jest.fn(async (path, opt) => (!opt ? { threads: { chat: hist, improve: hist }, proposals: { pending: [P], decided: [] } }
    : { ok: true, mode: 'chat', threads: { chat: [...hist, { role: 'user', text: 'two?' }, { role: 'assistant', text: 'answer two' }], improve: hist }, proposals: { pending: [P], decided: [] } }));
  const extras = [['coach', '👑 Coach', <p key="c" data-testid="coach-node">coach</p>]];
  const el = await mount(<AiChat call={call} extras={extras} />);
  expect(el.querySelectorAll('.cch-msg.is-fresh').length).toBe(0);                      // loaded history is still
  expect(q(el, 'cch-props-toggle').getAttribute('aria-expanded')).toBe('false');          // 💬 chat: fixes folded, the log keeps its room
  expect(q(el, 'cch-props').querySelector('ul').hidden).toBe(true);
  await act(async () => { q(el, 'cch-mode-improve').click(); });
  expect(q(el, 'cch-props-toggle').getAttribute('aria-expanded')).toBe('true');           // 🛠 fix mode opens them
  expect(el.querySelectorAll('.cch-msg.is-fresh').length).toBe(0);                      // switching modes replays nothing
  await act(async () => { q(el, 'cch-mode-chat').click(); });
  await type(el, 'two?'); await act(async () => { q(el, 'cch-send').click(); });
  expect([...el.querySelectorAll('.cch-msg.is-fresh')].map(m => m.textContent)).toEqual([expect.stringContaining('two?'), expect.stringContaining('answer two')]);
  await act(async () => { q(el, 'cch-pane-coach').click(); });
  expect(el.querySelector('.cch-talkpane').hidden).toBe(true); expect(q(el, 'cch-log')).not.toBeNull();   // still mounted: no remount, scroll kept
  await act(async () => { q(el, 'cch-pane-talk').click(); }); expect(el.querySelector('.cch-talkpane').hidden).toBe(false);
});

test('💻 local boost: the ⚙ switch posts localBoost, the header wears BOOST and the 24h watch draws one bar per hour', async () => {
  const local = { boost: true, leftH: 23.5, every: 45, why: 'boost on', reads24h: 31, fails24h: 1, paused24h: 2, hours: [{ hour: 3600, n: 3, ok: 3, fail: 0, paused: 0 }, { hour: 7200, n: 1, ok: 0, fail: 1, paused: 1 }] };
  const call = jest.fn(async (path, opt) => (!opt ? { threads: {}, local, settings: { temp: 0.3, len: 'normal' }, proposals: { pending: [], decided: [] } } : { local: { ...local, boost: false } }));
  const el = await mount(<AiChat call={call} />);
  expect(q(el, 'cch-boostchip')).not.toBeNull();
  await act(async () => { q(el, 'cch-set').click(); });
  expect(q(el, 'cch-watch').textContent).toContain('31 local reads in 24h'); expect(q(el, 'cch-watch').querySelectorAll('i').length).toBe(2);
  await act(async () => { q(el, 'cch-boost').click(); });
  expect(call).toHaveBeenCalledWith('/admin/ai/chat/settings', expect.objectContaining({ body: JSON.stringify({ localBoost: false }) }));
});

test('DATA chip says where the answer came from and what is missing', async () => {
  const el = await mount(<div><DataChip d={{ state: 'LIVE FEELESS', window: 'last night', exits: 41, gaps: [] }} /><DataChip d={{ state: 'NO HISTORY', gaps: ['no real exits in this window', 'no Judge reviews'] }} /></div>);
  const [a, b] = el.querySelectorAll('[data-testid="cch-data"]');
  expect(a.textContent).toBe('DATA: LIVE FEELESS · last night · 41 real exits');
  expect(a.className).toContain('is-live');
  expect(b.className).toContain('is-none');
  expect(b.getAttribute('data-tip')).toContain('no Judge reviews');
});
