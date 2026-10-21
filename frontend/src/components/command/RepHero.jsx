import React from 'react';
import { Search, HelpCircle, Shield, UserCheck, Trophy, Skull, BookOpen, Ruler } from 'lucide-react';
import '../../styles/repHero.css';

// 🛡 THE REP PAGE (owner, 2026-10-21: "rep needs a branded new UI layout — real backdrops, 3D artifact animation, no cards in cards"): a hero
// with a live 3D shield (rings turning in depth, a scan beam, wallets orbiting — green = trusted, red = flagged) and the page's real numbers,
// then ONE section at a time behind a sticky icon nav (less scroll, nothing stacked inside anything).
export const REP_SECTIONS = [
  ['investigate', 'Investigate', Search], ['why', 'Why it pumped', HelpCircle], ['markets', 'Rep markets', Shield], ['standing', 'Standing', UserCheck],
  ['board', 'Leaderboard', Trophy], ['rugs', 'Rugs', Skull], ['terms', 'Meme terms', BookOpen], ['how', 'How scores work', Ruler],
];
const DOTS = Array.from({ length: 10 }, (_, i) => i);

export function RepHero({ creators, tokens, chain }) {
  return (
    <header className="rph" data-testid="rep-hero">
      <div className="rph-copy">
        <span className="rph-eyebrow"><Shield size={13} /> FEELESS REP · THE TRUST LAYER</span>
        <h1>Check anyone <em>before you touch them.</em></h1>
        <p>Every wallet and coin is scored from evidence you can open — launch forensics, the funding graph, the blocklist and the trade history.</p>
        <div className="rph-nums">
          <span><b key={creators}>{Number(creators || 0).toLocaleString('en-US')}</b><em>CREATORS TRACKED</em></span>
          <span><b key={tokens}>{Number(tokens || 0).toLocaleString('en-US')}</b><em>TOKENS OBSERVED</em></span>
          <span><b>{chain || '—'}</b><em>CHAIN</em></span>
        </div>
      </div>
      <div className="rph-art" aria-hidden="true">
        <div className="rph-scene">
          <i className="rph-ring r1" /><i className="rph-ring r2" /><i className="rph-ring r3" />
          <i className="rph-core"><Shield size={46} strokeWidth={1.6} /></i>
          <i className="rph-beam" />
          <div className="rph-orbit">{DOTS.map(i => <i key={i} className={`rph-dot ${i % 4 === 1 ? 'is-bad' : ''}`} style={{ '--i': i }} />)}</div>
        </div>
      </div>
    </header>
  );
}

export function RepNav({ sec, setSec }) {
  return <nav className="rph-nav" role="tablist" aria-label="Rep sections">{REP_SECTIONS.map(([k, label, Icon]) => <button key={k} type="button" role="tab" aria-selected={sec === k}
    className={sec === k ? 'active' : ''} onClick={() => setSec(k)} data-testid={`rep-sec-${k}`}><Icon size={14} aria-hidden="true" /><span>{label}</span></button>)}</nav>;
}
