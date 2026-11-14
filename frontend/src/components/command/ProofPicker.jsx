import React, { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'motion/react';
import { isCalm } from '../../lib/fxPause';
import '../../styles/proofPicker.css';

// 🎯 AGX-1 · THE PROOF PICKER (owner 2026-11-14): ⌘K (or the taskbar button) opens a wheel, one slice per proof type. A slice fans that type's
// filed proofs out as cards, newest first, each lit by the score it would carry into the pot (the same pool weights `AgentPot` scores with).
// Picking one opens THAT proof in its desk window — never a link-out. Keyboard: type to filter, ←/→ turn the wheel, ↑/↓ walk the cards,
// Enter opens, Esc closes. Touch: tap a slice, tap a card. All real: the agent's own folders + its pool weights.
export const KINDS = [
  { kind: 'PoW', key: 'powFolders', win: 'pow', ic: '⛏', name: 'Proof of Work' },
  { kind: 'PoP', key: 'popFolders', win: 'pop', ic: '📉', name: 'Proof of Perps' },
  { kind: 'PoB', key: 'pobFolders', win: 'bids', ic: '🎲', name: 'Proof of Bids' },
  { kind: 'PoC', key: 'pocFolders', win: 'poc', ic: '📣', name: 'Proof of Content' },
  { kind: 'PoStatic', key: 'psFolders', win: 'postatic', ic: '💻', name: 'Proof of Static' },
  { kind: 'PoEco', key: 'poeFolders', win: 'poe', ic: '📊', name: 'Proof of Economy' },
];
const RANKS = ['S', 'A', 'B', 'C', 'D'];

const titleOf = (f, kind) => { const t = String(f?.topic || f?.name || f?.title || f?.q || '').replace(/\s+/g, ' ').trim().replace(/^(PoW|PoP|PoB|PoC|PoStatic|PoEco)\s*#\d+\s*[·:-]\s*/i, ''); return (t || `${kind} #${f?.n || ''}`).slice(0, 80); };   // the eyebrow already says "PoW #16"

/** Pure: every proof type → its filed proofs, newest first, each with its pot score + rank (null when the pool has not scored it yet). */
export function pickerKinds(d, weights) {
  return KINDS.map(k => {
    const rows = (d?.[k.key] || []).filter(f => f && f.id && !f.ad && !/^ad\s|\sad$/i.test(String(f.topic || f.name || '').trim()));   // a Showcase ad build is not one of its proofs (same rule as the desk monitors)
    const seen = {}; rows.forEach(f => { if (f.n) seen[f.n] = (seen[f.n] || 0) + 1; });   // 43 old PoStatics share a stuck #61 (fixed 2026-11-11): a shared number is no name
    const files = rows.map(f => {
      const w = weights?.[f.id]; const scored = w && w.score != null;
      return { id: f.id, n: f.n && seen[f.n] === 1 ? f.n : null, title: titleOf(f, k.kind), at: Number(f.at) || 0, score: scored ? Math.round(Number(w.score) || 0) : null, top: scored ? Number(w.top) || 300 : null, rank: scored && RANKS.includes(w.rank) ? w.rank : null };
    }).sort((a, b) => b.at - a.at);
    return { ...k, files };
  });
}

/** Pure: the cards one slice shows for a typed filter (title, #n or rank). */
export function filterFiles(files, q) {
  const s = String(q || '').trim().toLowerCase(); if (!s) return files;
  return files.filter(f => f.title.toLowerCase().includes(s) || (f.n != null && `#${f.n}` === s.replace(/^#?/, '#')) || (f.rank && `rank ${f.rank}`.toLowerCase() === s));
}

const ago = at => { if (!at) return ''; const s = Math.max(0, Date.now() / 1000 - at); return s < 3600 ? `${Math.max(1, Math.round(s / 60))}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };

// one wheel slice as an SVG ring segment
function arc(i, n, r0, r1, gap = 0.035) {
  const a0 = (i / n) * Math.PI * 2 - Math.PI / 2 + gap; const a1 = ((i + 1) / n) * Math.PI * 2 - Math.PI / 2 - gap;
  const p = (r, a) => `${(150 + r * Math.cos(a)).toFixed(2)} ${(150 + r * Math.sin(a)).toFixed(2)}`;
  return `M ${p(r1, a0)} A ${r1} ${r1} 0 0 1 ${p(r1, a1)} L ${p(r0, a1)} A ${r0} ${r0} 0 0 0 ${p(r0, a0)} Z`;
}
const mid = (i, n, r) => { const a = ((i + 0.5) / n) * Math.PI * 2 - Math.PI / 2; return [150 + r * Math.cos(a), 150 + r * Math.sin(a)]; };

export default function ProofPicker({ d, weights, onPick, onClose, start = 0 }) {
  const kinds = useMemo(() => pickerKinds(d, weights), [d, weights]);
  const [at, setAt] = useState(() => { const s = Math.max(0, Math.min(KINDS.length - 1, start)); const first = kinds.findIndex(k => k.files.length); return kinds[s]?.files.length || first < 0 ? s : first; });
  const [q, setQ] = useState(''); const [hi, setHi] = useState(0); const input = useRef(null); const list = useRef(null); const calm = isCalm();
  const k = kinds[at]; const files = useMemo(() => filterFiles(k.files, q), [k, q]);
  useEffect(() => { setHi(0); }, [at, q]);
  useEffect(() => { input.current?.focus(); }, []);
  useEffect(() => { list.current?.querySelector(`[data-i="${hi}"]`)?.scrollIntoView?.({ block: 'nearest' }); }, [hi]);
  const turn = step => setAt(a => (a + step + KINDS.length) % KINDS.length);
  const pick = f => onPick?.({ win: k.win, kind: k.kind, id: f.id });
  const onKey = e => {
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); if (q) setQ(''); else onClose?.(); return; }
    if (e.key === 'ArrowRight' && !(e.target.tagName === 'INPUT' && q && e.target.selectionStart < q.length)) { e.preventDefault(); turn(1); return; }
    if (e.key === 'ArrowLeft' && !(e.target.tagName === 'INPUT' && q && e.target.selectionStart > 0)) { e.preventDefault(); turn(-1); return; }
    if (e.key === 'ArrowDown') { e.preventDefault(); setHi(h => Math.min(files.length - 1, h + 1)); return; }
    if (e.key === 'ArrowUp') { e.preventDefault(); setHi(h => Math.max(0, h - 1)); return; }
    if (e.key === 'Enter' && files[hi] && e.target.tagName === 'INPUT') { e.preventDefault(); pick(files[hi]); }
  };
  const total = kinds.reduce((s, x) => s + x.files.length, 0);
  return <div className="ppk" role="dialog" aria-modal="true" aria-label="Proof picker" data-testid="proof-picker" onKeyDown={onKey} onPointerDown={e => { if (e.target === e.currentTarget) onClose?.(); }}>
    <motion.div className="ppk-box" initial={calm ? false : { opacity: 0, scale: 0.96, y: 10 }} animate={{ opacity: 1, scale: 1, y: 0 }} transition={{ duration: 0.18 }}>
      <header className="ppk-h">
        <small>PROOF PICKER · {total} FILED</small>
        <label className="ppk-q"><span aria-hidden="true">⌕</span><input ref={input} className="m-input" value={q} onChange={e => setQ(e.target.value)} placeholder={`Find a ${k.kind} by topic, #number or "rank A"`} aria-label="Filter proofs" data-testid="ppk-q" /></label>
        <kbd className="ppk-kbd" data-tip="Open or close this picker from anywhere on the desktop">⌘K</kbd>
        <button type="button" className="m-btn ppk-x" onClick={onClose} aria-label="Close the picker" data-tip="Close (Esc)" data-testid="ppk-close">✕</button>
      </header>
      <div className="ppk-main">
        <svg className="ppk-wheel" viewBox="0 0 300 300" role="tablist" aria-label="Proof types" data-testid="ppk-wheel">
          <circle cx="150" cy="150" r="146" className="ppk-rim" />
          {kinds.map((x, i) => { const [lx, ly] = mid(i, kinds.length, 100); const on = i === at; const best = x.files.find(f => f.rank);
            return <g key={x.kind} role="tab" tabIndex={on ? 0 : -1} aria-selected={on} aria-label={`${x.name}, ${x.files.length} filed`} className={`ppk-slice${on ? ' is-on' : ''}${x.files.length ? '' : ' is-empty'}`} onClick={() => setAt(i)} data-testid={`ppk-slice-${x.kind}`} data-rank={best?.rank || ''}>
              <title>{`${x.name} · ${x.files.length} filed`}</title>
              <motion.path d={arc(i, kinds.length, 58, 140)} initial={calm ? false : { opacity: 0, scale: 0.7 }} animate={{ opacity: 1, scale: on ? 1.035 : 1 }} transition={{ delay: calm ? 0 : i * 0.04, type: 'spring', stiffness: 320, damping: 24 }} style={{ transformOrigin: '150px 150px' }} />
              <text x={lx} y={ly - 6} className="ppk-ic">{x.ic}</text>
              <text x={lx} y={ly + 12} className="ppk-kind">{x.kind}</text>
              <text x={lx} y={ly + 26} className="ppk-n">{x.files.length}</text>
            </g>; })}
          <circle cx="150" cy="150" r="52" className="ppk-hub" />
          <text x="150" y="144" className="ppk-hub-n">{k.files.length}</text>
          <text x="150" y="162" className="ppk-hub-k">{k.kind.toUpperCase()}</text>
        </svg>
        <section className="ppk-fan" aria-label={`${k.name} proofs`} data-testid="ppk-fan">
          <header><b>{k.ic} {k.name}</b><span>{files.length === k.files.length ? `${files.length} filed · newest first` : `${files.length} of ${k.files.length} match`}</span></header>
            <motion.ol key={`${k.kind}|${q}`} ref={list} className="ppk-cards" role="listbox" aria-label={`${k.kind} proofs`}>
              {files.length ? files.map((f, i) => <motion.li key={f.id} role="option" aria-selected={i === hi}
                initial={calm ? false : { opacity: 0, x: -60, rotate: -8 + Math.min(i, 6) * 2 }} animate={{ opacity: 1, x: 0, rotate: 0 }} transition={{ delay: calm ? 0 : Math.min(i, 10) * 0.035, type: 'spring', stiffness: 300, damping: 26 }}>
                <button type="button" data-i={i} className={`ppk-card r-${(f.rank || 'none').toLowerCase()}${i === hi ? ' is-hi' : ''}`} onClick={() => pick(f)} onPointerEnter={() => setHi(i)} data-tip={f.score == null ? 'Not scored by the pool yet. Opens it in its desk window' : `Would carry ${f.score} of ${f.top} into the pot. Opens it in its desk window`} data-testid="ppk-card">
                  <i className="ppk-edge" aria-hidden="true" />
                  <span className="ppk-card-t"><em>{k.kind}{f.n ? ` #${f.n}` : ''}</em><b>{f.title}</b></span>
                  <span className="ppk-card-s">{f.rank ? <><strong className="m-num">{f.score}</strong><small>RANK {f.rank}</small></> : <small>NOT SCORED</small>}<time>{ago(f.at)}</time></span>
                </button>
              </motion.li>) : <li className="ppk-none" data-testid="ppk-none">{k.files.length ? 'Nothing matches that. Clear the filter (Esc).' : `No ${k.kind} filed yet. File one from its desk window and it lands here.`}</li>}
            </motion.ol>
          <footer className="ppk-keys" aria-hidden="true"><span><kbd>←</kbd><kbd>→</kbd> type</span><span><kbd>↑</kbd><kbd>↓</kbd> proof</span><span><kbd>↵</kbd> open</span><span><kbd>esc</kbd> close</span></footer>
        </section>
      </div>
    </motion.div>
  </div>;
}
