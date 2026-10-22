import React from 'react';
import { Search, HelpCircle, Shield, UserCheck, Trophy, Skull, BookOpen, Ruler } from 'lucide-react';
import '../../styles/repHero.css';
import { BADGE_LABEL } from '../../lib/reputation';
import { useGlide } from '../../lib/useGlide';

// 🛡 THE REP PAGE (owner, 2026-10-21: "rep needs a branded new UI layout — real backdrops, no cards in cards"): a hero with the TRUST RADAR (real
// creators, below) and the board's own numbers, then ONE section at a time behind a sticky icon nav (less scroll, nothing stacked inside anything).
export const REP_SECTIONS = [
  ['investigate', 'Investigate', Search], ['why', 'Why it pumped', HelpCircle], ['markets', 'Rep markets', Shield], ['standing', 'Standing', UserCheck],
  ['board', 'Leaderboard', Trophy], ['rugs', 'Rugs', Skull], ['terms', 'Meme terms', BookOpen], ['how', 'How scores work', Ruler],
];
// 📡 THE TRUST RADAR (2026-10-22 redo — owner: "fake 3D, slang with no real vitals"): every dot is a REAL creator from the board — trusted ones
// sit near the core, risky / flagged ones out at the rim (distance = 100 − score), colour = its badge, hover = the wallet + its score + why.
// The beam sweeps; the numbers beside it are the board's own (trusted share, rugs caught, serial dumpers) and glide when they change.
export const BADGE_TONE = { trusted: '#45e486', veteran: '#7ff0cf', building: '#6fd3ff', unproven: '#b9c4bf', risky: '#ffb347', flagged: '#ff4d6d' };
const hash = s => { let h = 0; for (const c of String(s || '')) h = (h * 31 + c.charCodeAt(0)) | 0; return Math.abs(h); };
// pure: where a creator sits on the radar (x, y in a 240 box) and its tone
export function radarPoint(row) {
  const r = 18 + (Math.max(0, Math.min(100, 100 - (Number(row.score) || 0))) / 100) * 92; const a = (hash(row.address) % 3600) / 3600 * Math.PI * 2;
  return { x: +(120 + r * Math.cos(a)).toFixed(1), y: +(120 + r * Math.sin(a)).toFixed(1), tone: BADGE_TONE[row.badge] || '#b9c4bf' };
}
// pure: the board's own vitals
export function repVitals(rows) {
  const rs = rows || []; const n = rs.length || 1; const by = {};
  rs.forEach(r => { by[r.badge] = (by[r.badge] || 0) + 1; });
  return { trustedPct: Math.round(((by.trusted || 0) + (by.veteran || 0)) / n * 100), rugs: rs.reduce((a, r) => a + (Number(r.ruggedCount) || 0), 0),
    dumpers: rs.filter(r => r.serialDumper).length, mix: Object.entries(by).sort((a, b) => b[1] - a[1]).map(([k, c]) => ({ k, c, w: c / n })) };
}
// pure: what a creator's launches became, as bar parts
export function recordParts(row) {
  const n = Math.max(1, Number(row.tokenCount) || 0);
  const parts = [['sustained', row.sustainedCount, '#45e486'], ['dumped', row.dumpedCount, '#ffb347'], ['dead', row.deadCount, '#8a93a6'], ['rugged', row.ruggedCount, '#ff4d6d']]
    .map(([k, v, c]) => ({ k, v: Number(v) || 0, c, w: (Number(v) || 0) / n })).filter(p => p.v > 0);
  return { parts, other: Math.max(0, 1 - parts.reduce((a, p) => a + p.w, 0)), n };
}
function Glide({ v, suffix = '' }) { const g = useGlide(Number(v) || 0, 900); return <>{Math.round(g || 0).toLocaleString('en-US')}{suffix}</>; }

export function RepHero({ creators, tokens, chain, rows = [] }) {
  const pts = (rows || []).slice(0, 48); const vt = repVitals(pts);
  return (
    <header className="rph" data-testid="rep-hero">
      <div className="rph-copy">
        <span className="rph-eyebrow"><Shield size={13} /> FEELESS REP · THE TRUST LAYER</span>
        <h1>Check anyone <em>before you touch them.</em></h1>
        <p>Every dot is a real creator FEELESS tracks — closer to the core = a cleaner record. Tap one in the board below to open its case file.</p>
        <div className="rph-nums">
          <span data-tip="Creators FEELESS has scored on this chain"><b><Glide v={creators} /></b><em>CREATORS TRACKED</em></span>
          <span data-tip="Tokens their launches were judged on"><b><Glide v={tokens} /></b><em>TOKENS OBSERVED</em></span>
          <span data-tip="Share of the creators on the radar with a trusted / veteran record"><b className="is-good"><Glide v={vt.trustedPct} suffix="%" /></b><em>TRUSTED NOW</em></span>
          <span data-tip="Rugs these creators' launches ended in (the evidence behind the red dots)"><b className="is-bad"><Glide v={vt.rugs} /></b><em>RUGS ON RECORD</em></span>
        </div>
        {vt.mix.length ? <div className="rph-mix" data-tip="The trust mix of the creators on the radar"><span>{vt.mix.map(m => <i key={m.k} style={{ flexGrow: Math.max(0.02, m.w), background: BADGE_TONE[m.k] || '#b9c4bf' }} />)}</span>
          <small>{vt.mix.slice(0, 4).map(m => <em key={m.k}><u style={{ background: BADGE_TONE[m.k] || '#b9c4bf' }} />{m.k} {m.c}</em>)}{chain ? <em>· {chain}</em> : null}</small></div> : null}
      </div>
      <div className="rph-art">
        <svg className="rph-radar" viewBox="0 0 240 240" role="img" aria-label={`${pts.length} creators on the trust radar`}>
          <defs><radialGradient id="rphCore" cx=".5" cy=".5" r=".5"><stop offset="0" stopColor="#45e486" stopOpacity=".35" /><stop offset="1" stopColor="#45e486" stopOpacity="0" /></radialGradient>
            <linearGradient id="rphBeam" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#7ff0cf" stopOpacity="0" /><stop offset="1" stopColor="#7ff0cf" stopOpacity=".32" /></linearGradient></defs>
          <circle cx="120" cy="120" r="112" className="rr o" /><circle cx="120" cy="120" r="82" className="rr" /><circle cx="120" cy="120" r="52" className="rr" /><circle cx="120" cy="120" r="26" className="rr in" />
          <path d="M120,6 V234 M6,120 H234" className="rx" />
          <text x="120" y="88" className="rl">CLEAN AT THE CORE</text><text x="120" y="232" className="rl">RISKY AT THE RIM</text>
          <g className="rph-sweep"><path d="M120,120 L120,8 A112,112 0 0 1 199,41 Z" fill="url(#rphBeam)" /></g>
          <circle cx="120" cy="120" r="30" fill="url(#rphCore)" />
          {pts.map((r, i) => { const p = radarPoint(r); return <g key={r.address} className="rph-node" style={{ '--i': i, '--c': p.tone }}>
            <circle cx={p.x} cy={p.y} r={r.badge === 'flagged' || r.badge === 'risky' ? 4.2 : 3.4} /><title>{`${r.address.slice(0, 4)}…${r.address.slice(-4)} · score ${r.score} · ${BADGE_LABEL[r.badge] || r.badge}${(r.reasons || []).length ? ` · ${r.reasons.slice(0, 2).join(' · ')}` : ''}`}</title></g>; })}
          <g transform="translate(120 120)" className="rph-shield"><path d="M0,-17 L14,-11 L12,5 C10,12 5,16 0,19 C-5,16 -10,12 -12,5 L-14,-11 Z" /><path d="M-6,0 L-1,5 L7,-5" className="ck" /></g>
        </svg>
      </div>
    </header>
  );
}

export function RepNav({ sec, setSec }) {
  return <nav className="rph-nav" role="tablist" aria-label="Rep sections">{REP_SECTIONS.map(([k, label, Icon]) => <button key={k} type="button" role="tab" aria-selected={sec === k}
    className={sec === k ? 'active' : ''} onClick={() => setSec(k)} data-testid={`rep-sec-${k}`}><Icon size={14} aria-hidden="true" /><span>{label}</span></button>)}</nav>;
}
