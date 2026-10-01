import React from 'react';

// Animated chat backgrounds, chosen per room in the chat ⚙ panel (saved in chat prefs as themes[room]).
// Every theme carries the FEE mark; motion is transform/opacity only and stops under fx-lite / reduced motion.
export const CHAT_THEMES = [['fee', 'FEE glow'], ['aurora', 'Aurora'], ['grid', 'Neon grid'], ['stars', 'Starfield'], ['pulse', 'Heartbeat'], ['off', 'Plain']];
export const chatTheme = (prefs, room) => (prefs?.themes || {})[room] || 'fee';

export function ChatFx({ theme }) {
  if (theme === 'off') return null;
  return <div className={`chat-fx fx-${theme}`} aria-hidden="true" data-testid="chat-fx"><i className="chat-fx-a" /><i className="chat-fx-b" /><img className="chat-fx-logo" src="/assets/feeless-logo.png" alt="" /></div>;
}
