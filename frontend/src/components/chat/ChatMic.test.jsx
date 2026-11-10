import React, { act, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ChatComposer, ChatInput, ChatSend } from './ChatKit';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
function Box() { const [t, setT] = useState('buy'); return <ChatComposer onSubmit={e => e.preventDefault()} field={<ChatInput value={t} onChange={e => setT(e.target.value)} data-testid="in" />} action={<ChatSend />} />; }

test('🎙 AGT-6: the mic lives in the shared composer: talking writes into that chat\'s own state, after what was typed; no mic where the browser has none', async () => {
  let rec; window.webkitSpeechRecognition = function R() { rec = this; this.start = jest.fn(); this.stop = () => this.onend?.(); this.abort = jest.fn(); };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => root.render(<Box />));
  const mic = el.querySelector('[data-testid="ckit-mic"]'); expect(mic).toBeTruthy();
  await act(async () => { mic.click(); }); expect(rec.start).toHaveBeenCalled(); expect(mic.getAttribute('aria-pressed')).toBe('true'); expect(rec.continuous).toBe(true);
  await act(async () => { rec.onresult({ results: [[{ transcript: 'the dip on' }], [{ transcript: ' sol' }]] }); });
  expect(el.querySelector('[data-testid="in"]').value).toBe('buy the dip on sol');                 // React state got it (controlled input)
  await act(async () => { mic.click(); }); expect(mic.getAttribute('aria-pressed')).toBe('false');
  await act(async () => { mic.click(); }); await act(async () => { rec.onerror({ error: 'not-allowed' }); rec.onend(); });
  expect(mic.getAttribute('data-tip')).toContain('Allow the microphone');
  act(() => root.unmount()); delete window.webkitSpeechRecognition;
  const el2 = document.createElement('div'); const root2 = createRoot(el2); await act(async () => root2.render(<Box />));
  expect(el2.querySelector('[data-testid="ckit-mic"]')).toBeNull(); act(() => root2.unmount()); el.remove();
});
