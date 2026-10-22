import React, { useState } from 'react';
import { ChatFx, ChatThemePicker, CHAT_THEMES } from '../components/ChatFx';

// 🧪 DEV ONLY (`/dev/themes`): every chat theme as a big room + the shared picker at $7 of $FEE (one perk: vortex).
export default function ThemesHarness() {
  const [prefs, setP] = useState({ themes: {} });
  return <div style={{ height: '100vh', overflowY: 'auto', boxSizing: 'border-box', padding: 16, background: '#040806', color: '#dfe', display: 'grid', gap: 14 }}>
    <h2 className="m-label">🧪 DEV PREVIEW · chat themes</h2>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))', gap: 10 }}>{CHAT_THEMES.filter(t => t[0] !== 'off').map(([id, label]) =>
      <div key={id} className="has-cfx" style={{ height: 150, borderRadius: 12, border: '1px solid #1d2a22', overflow: 'hidden', background: '#060b08', padding: 8 }}><ChatFx theme={id} room="solana-general" /><b className="m-label">{label}</b></div>)}</div>
    <div style={{ maxWidth: 420 }}><ChatThemePicker prefs={prefs} setPrefs={p => setP(x => ({ ...x, ...p }))} room="brain" feeUsd={7} unlocked={['vortex']} /></div>
  </div>;
}
