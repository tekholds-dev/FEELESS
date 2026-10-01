import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ChatFx, chatTheme, CHAT_THEMES } from './ChatFx';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('each room keeps its own background (FEE glow by default), every theme shows the FEE mark, Plain shows nothing', () => {
  const prefs = { themes: { 'coin-x': 'grid' } };
  expect(chatTheme(prefs, 'coin-x')).toBe('grid');
  expect(chatTheme(prefs, 'solana-general')).toBe('fee');
  const host = document.createElement('div'); document.body.appendChild(host);
  const root = createRoot(host);
  for (const [id] of CHAT_THEMES.filter(([t]) => t !== 'off')) {
    act(() => root.render(<ChatFx theme={id} />));
    expect(host.querySelector('[data-testid="chat-fx"]').className).toContain(`fx-${id}`);
    expect(host.querySelector('.chat-fx-logo').getAttribute('src')).toBe('/assets/feeless-logo.png');
  }
  act(() => root.render(<ChatFx theme="off" />));
  expect(host.querySelector('[data-testid="chat-fx"]')).toBeNull();
});
