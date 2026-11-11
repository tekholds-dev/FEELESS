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

test('🔊 AGT-6: answers speak back in the most natural voice; asked by mic → read out once; links + [tags] are skipped', async () => {
  const { SpeakBtn, speak, speakable, takeVoiced } = require('./ChatKit');
  const said = []; window.SpeechSynthesisUtterance = function U(t) { this.text = t; };
  window.speechSynthesis = { cancel: jest.fn(), getVoices: () => [{ name: 'Fred', lang: 'en-US' }, { name: 'Samantha (Enhanced)', lang: 'en-US' }], speak: u => { said.push(u); } };
  expect(speakable('Desk is flat [agents] see https://x.y/z **now**')).toBe('Desk is flat see link now');
  expect(speak('hello')).toBe(true); expect(said[0].voice.name).toBe('Samantha (Enhanced)');
  expect(takeVoiced()).toBe(true); expect(takeVoiced()).toBe(false);   // the mic test above spoke; it is used once
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => root.render(<SpeakBtn text="gm degen" testid="say" />));
  const b = el.querySelector('[data-testid="say"]'); await act(async () => b.click());
  expect(said[1].text).toBe('gm degen'); expect(b.textContent).toContain('Stop');
  await act(async () => said[1].onend());
  expect(b.textContent).toContain('Listen');
  delete window.speechSynthesis; await act(async () => root.render(<SpeakBtn text="x" testid="say2" />)); expect(el.querySelector('[data-testid="say2"]')).toBeNull();
});
