import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { AiChat, metaLine, CHAT_MODES } from './AiChat';

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
  expect(CHAT_MODES.map(m => m[0])).toEqual(['chat', 'case', 'improve']); expect(q(el, 'cch-send').disabled).toBe(true);
  await type(el, 'why small wins?'); await act(async () => { q(el, 'cch-send').click(); });
  expect(call).toHaveBeenCalledWith('/admin/ai/chat', expect.objectContaining({ method: 'POST', body: JSON.stringify({ text: 'why small wins?', mode: 'chat', focus: 'M1' }) }));
  expect(q(el, 'cch-log').textContent).toContain('Reaper banks winners at about +2%.'); expect(q(el, 'cch-log').textContent).not.toContain('"stance"');
  expect(q(el, 'cch-meta').textContent).toBe('OPENROUTER · gpt-x · 4.2s · 900→60 tok');
  expect(mockHub.hubApply).not.toHaveBeenCalled(); expect(mockHub.hubLoad).not.toHaveBeenCalled();   // no full-tab repaint: the answer lives in this panel
  await act(async () => { q(el, 'cch-clear').click(); }); expect(q(el, 'cch-log').textContent).toContain('Ask it anything');
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
  expect(q(el, 'cch-prop-p1').textContent).toContain('APPROVED'); expect(q(el, 'cch-prop-p1').textContent).toContain('chartWait: False → True'); expect(q(el, 'cch-approve-p1')).toBeNull();
  const el2 = await mount(<AiChat call={call} />);
  await act(async () => { q(el2, 'cch-reject-p1').click(); });
  expect(sent[1]).toEqual(['/admin/ai/proposals/decide', { id: 'p1', approve: false }]); expect(q(el2, 'cch-prop-p1').textContent).toContain('REJECTED');
});
