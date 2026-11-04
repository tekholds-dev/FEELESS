import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useGlide } from '../../lib/useGlide';
import '../../styles/feeCatLore.css';
import { FeeCatBrainPage, ThinkFlow } from './FeeCatBrainPage';
import { Ic3 } from '../../lib/icon3d';

// 📜 THE LEGEND OF FEE (owner P2: "FeeCat lore + other tabs — only the top was redone"; FeeCat = violet night). A drawn rooftop at night: Fee's
// silhouette with eyes that blink, the moon, and NINE LANTERNS = her nine lives, lit from her live discipline (feecat_brain: a loss −1, a win +1,
// 0 = she naps). Under it the legend as five chapter cards, each carrying a LIVE number (her record, lives, balance vs start, Fee-Back state,
// the cats), then the Fee-Back return path + calculator as segmented tabs. Honest: distributions stay "planned" until they are real.
export const CHAPTERS = [
  ['born', 'I · BORN IN THE TRENCHES', 'Fee is FEELESS\'s first cat: a trading cat that lives on-chain and trades in the open.',
    ['she scans the FEELESS intake every few seconds', 'two minds read each coin; only what passes every gate is bought', 'every move lands on her wall — nothing hidden']],
  ['lives', 'II · NINE LIVES', 'Every loss costs a life, a win in 24h earns one back. At zero she naps — she can only ever trade LESS.',
    ['a losing exit blows out one lantern', 'a win inside 24 h lights one again', 'at 0 lives she naps: no new buys until a lantern is lit', 'tilt or a cold streak shrinks her size first']],
  ['record', 'III · HER RECORD', 'Every trade she closes is on her wall — wins, losses, the SOL she made or lost. No edits.',
    ['P/L is what reached the pool — fees never counted', 'every exit filed with its reason', 'open her wall to replay any trade']],
  ['feeback', 'IV · THE FEE-BACK', 'FEECAT is the delivery asset for Fee-Back: part of FEELESS fees returned to holders — distributions are planned, not live.',
    ['part of FEELESS fees routes back to FEECAT holders', 'nothing is paid until a FEECAT market exists', 'the calculator shows what a holder would get']],
  ['cats', 'V · THE CATS', 'Fee is the first. Every FEELESS cat after her trades on the same discipline.',
    ['build a trader or a general agent with 2 minds', 'give it its own wallet — it pays for its own thinking', 'type "file a PoW" in its chat to put it to work']],
];
// 📖 the manual's tutorial (owner 2026-11-02: "anything under the header should look like a manual with more tutorial details")
export const SYNOPSIS = [['🐱', 'Meet the cats', 'every agent with its two live windows, its honey and its last call', '/terminal/feecat/cats'],
  ['🛠', 'Build an agent', 'trader or general · pick 2 minds · fund its OWN wallet (it pays for its own thinking)', '/terminal/feecat/new'],
  ['⛏', 'file a PoW', 'type it in its chat: a pool of buyable coins → each mind proposes 3 → takes 2 + a plan → researches → decides → buys', null],
  ['🐝', 'Colonize', 'share a part of each win with the colony pot — the pot airdrops back by what you shared', null],
  ['💸', 'colony --flow', 'watch every SOL: trades in, P/L, shares, the pot, the ledger with each tx', null]];
export const COMMANDS = [['file a PoW', 'both minds work a new PoW folder and buy the one they agree on'], ['A: file a PoW', 'mind A alone (B: for mind B)'],
  ['propose a PoW', 'the same work, filed as a card — nothing bought'], ['file a PoP', 'both minds call a perp; a paper trade runs if they agree'], ['propose a PoP', 'the same call as a card; nothing opens until you press Run'], ['stop PoW', 'ends the folder — sells if it bought'], ['/', 'every command, as you type']];
const sol = v => `${(Number(v) || 0) >= 0 ? '+' : ''}${(Number(v) || 0).toFixed(2)} SOL`;
// pure: a chapter's live number from the cat profile (+ the FEECAT asset)
export function chapterStat(key, p, asset) {
  const c = p?.cat || {}; const d = p?.discipline || {}; const s = p?.stats || {};
  if (key === 'born') return [`LEVEL ${c.level || 1}`, `${(Number(c.balanceSol) || 0).toFixed(2)} SOL in her bag`];
  if (key === 'lives') return [`${d.lives ?? '—'} / ${d.maxLives ?? 9}`, d.pause ? 'napping — no new trades' : d.why || 'normal size'];
  if (key === 'record') return [`${c.wins || 0}W · ${c.losses || 0}L`, s.trades ? `${sol(c.realizedPnlSol)} · ROI ${s.roiPct}%` : 'first trade still to come'];
  if (key === 'feeback') return ['PLANNED', asset?.status === 'market_observed' ? 'FEECAT market observed' : 'awaiting a FEECAT market'];
  return ['COLLECTION', 'meet every FEELESS cat'];
}

function Rooftop({ lives = 9, max = 9, nap }) {
  return <div className={`fcl-roof ${nap ? 'is-nap' : ''}`} aria-hidden="true">
    <span className="fcl-moon" /><span className="fcl-stars">{Array.from({ length: 16 }, (_, i) => <i key={i} style={{ '--i': i }} />)}</span>
    <svg className="fcl-city" viewBox="0 0 400 120" preserveAspectRatio="xMidYMax slice">{Array.from({ length: 12 }, (_, i) => { const h = 40 + ((i * 41) % 60); return <g key={i}>
      <rect x={i * 34} y={120 - h} width="30" height={h} className="fcl-bld" />{Array.from({ length: Math.floor(h / 14) }, (_, r) => <rect key={r} x={i * 34 + 6 + (r % 2) * 10} y={120 - h + 8 + r * 14} width="4" height="5" className={(r + i) % 3 ? 'fcl-win' : 'fcl-win is-on'} />)}</g>; })}</svg>
    <svg className="fcl-cat" viewBox="0 0 120 110"><path d="M20 108 C 18 70, 30 52, 52 50 L 46 22 L 62 40 C 70 38, 78 38, 86 40 L 100 22 L 96 52 C 110 60, 112 84, 104 108 Z" className="fcl-body" />
      <path d="M104 100 C 120 96, 122 74, 112 66" className="fcl-tail" /><ellipse cx="66" cy="62" rx="5" ry="6" className="fcl-eye" /><ellipse cx="84" cy="62" rx="5" ry="6" className="fcl-eye e2" /></svg>
    <span className="fcl-ledge" />
    <span className="fcl-lanterns" data-tip={`${lives} of ${max} lives left — a loss blows one out, a win in 24h lights one`}>{Array.from({ length: max }, (_, i) => <i key={i} className={i < lives ? 'is-lit' : ''} style={{ '--i': i }}><b /></i>)}</span>
    {nap ? <span className="fcl-zz">z z Z</span> : null}
  </div>;
}

// 📜 LORE = her legend + 🧠 HER BRAIN (owner 2026-10-31: "put her brain inside the Lore tab") + ↻ Fee-Back, as three sections of one page
export const LORE_TABS = [['legend', '📜 Legend', 'Who Fee is — five chapters, each with a live number'], ['brain', '🧠 Her brain', 'How she thinks: the whole loop, then her gates, ladder, lessons and lives'], ['feeback', '↻ Fee-Back', 'The return path and the calculator']];
export function FeeCatLore({ asset, community, onSelect, children, start = 'legend' }) {
  const [p, setP] = useState(null); const [tab, setTab] = useState('path'); const [sec, setSec] = useState(start);
  useEffect(() => { let on = true; const go = () => fetch('/api/cats/leader/profile').then(r => (r.ok ? r.json() : null)).then(x => { if (on && x) setP(x); }).catch(() => {});
    go(); const t = setInterval(() => { if (!document.hidden) go(); }, 60000); return () => { on = false; clearInterval(t); }; }, []);
  const d = p?.discipline || {}; const lives = useGlide(d.lives ?? 9);
  return <section className="fcl" data-testid="feecat-lore">
    <header className="fcl-hero">
      <Rooftop lives={Math.round(lives)} max={d.maxLives || 9} nap={d.pause} />
      <div className="fcl-copy"><span className="fcl-eyebrow"><Ic3 e="📜" /> THE LEGEND OF FEE</span><h1>The first cat of FEELESS.</h1>
        <p className="fcl-tag" data-testid="feecat-launch-state">{asset?.status === 'market_observed' ? 'MARKET OBSERVED · DISTRIBUTIONS PLANNED' : 'AWAITING MARKET · DISTRIBUTIONS PLANNED'}</p>
        <div className="fcl-ctas"><Link className="m-btn m-go" to="/terminal/feecat/cats" data-testid="feecat-collection-link">🐱 Meet the cats</Link>
          {asset?.pair ? <button type="button" className="m-btn" onClick={() => onSelect?.(asset.pair)} data-testid="feecat-open-market">Open FEECAT market ↗</button> : null}</div></div>
    </header>
    <div className="fcl-man"><p className="fcl-man-h"><b>~/feeless <i>›</i> man fee{sec === 'legend' ? '' : ` --${sec}`}</b><small># her legend, how every cat works, and how to put your own to work</small></p>
    <nav className="m-seg fcl-secs" role="tablist" aria-label="Lore">{LORE_TABS.map(([k, l, tip]) => <button key={k} type="button" role="tab" aria-selected={sec === k} className={sec === k ? 'active' : ''} onClick={() => setSec(k)} data-tip={tip} data-testid={`lore-${k}`}>{l}</button>)}</nav>
    {sec === 'brain' ? <><ThinkFlow /><FeeCatBrainPage /></> : null}
    {sec === 'legend' ? <div className="fcl-mp" data-testid="lore-manual">
      <section className="fcl-mp-sec"><h3>NAME</h3><div><p><b>fee</b> — the first trading cat of FEELESS. <span className="m-num">{chapterStat('born', p, asset).join(' · ')}</span></p></div></section>
      <section className="fcl-mp-sec"><h3>SYNOPSIS</h3><div><ol className="fcl-mp-steps">{SYNOPSIS.map(([ic, k, what, to], i) => <li key={k} style={{ '--i': i }}><span className="fcl-mp-n">{i + 1}</span>
        {to ? <Link to={to} className="fcl-mp-cmd" data-tip={what}><Ic3 e={ic} /> {k}</Link> : <code className="fcl-mp-cmd"><Ic3 e={ic} /> {k}</code>}<small>{what}</small></li>)}</ol></div></section>
      {CHAPTERS.map(([k, title, line, how], i) => { const [big, small] = chapterStat(k, p, asset); const lv = Math.round(lives); const mx = d.maxLives || 9;
        const w = Number(p?.cat?.wins) || 0, l = Number(p?.cat?.losses) || 0;
        return <section key={k} className={`fcl-mp-sec k-${k}`} style={{ '--i': i + 2 }} data-testid={`feecat-ch-${k}`}><h3>{title}</h3><div>
          <p className="fcl-mp-big"><b className="m-num">{big}</b><small>{small}</small></p>
          {k === 'lives' ? <span className="fcl-mp-meter" aria-label={`${lv} of ${mx} lives`}>{Array.from({ length: mx }, (_, j) => <i key={j} className={j < lv ? 'is-on' : ''} />)}</span> : null}
          {k === 'record' && w + l ? <span className="fcl-mp-wl" aria-label={`${w} wins, ${l} losses`}><s style={{ transform: `scaleX(${w / (w + l)})` }} /></span> : null}
          <p>{line}</p><ul className="fcl-mp-how">{how.map(x => <li key={x}>{x}</li>)}</ul>
          {k === 'cats' ? <Link to="/terminal/feecat/cats" className="fcl-go">open the cats ›</Link> : k === 'feeback' ? <Link to="/terminal/feeback" className="fcl-go">Fee-Back ›</Link>
            : k === 'record' ? <Link to="/terminal/feecat" className="fcl-go" onClick={e => { e.preventDefault(); onSelect?.('wall'); }}>her wall ›</Link> : null}</div></section>; })}
      <section className="fcl-mp-sec"><h3>COMMANDS</h3><div><dl className="fcl-mp-cmds">{COMMANDS.map(([c, w]) => <React.Fragment key={c}><dt><code>{c}</code></dt><dd>{w}</dd></React.Fragment>)}</dl></div></section>
      <section className="fcl-mp-sec"><h3>STATUS</h3><div><dl className="fcl-mp-kv">{[['FEECAT RECEIVED', 'No verified distributions'], ['TREASURY', 'Not published / unverified'], ['TRENCHES · 7D', community?.messages != null ? `${community.messages} real messages` : 'connecting'],
        ['FEECAT MARKET', asset?.status === 'market_observed' && asset?.pair?.priceUsd ? `$${Number(asset.pair.priceUsd).toPrecision(3)}` : 'awaiting a market']].map(([k, v], i) => <React.Fragment key={k}><dt>{k}</dt><dd data-testid={`feecat-stat-${i}`}>{v}</dd></React.Fragment>)}</dl></div></section>
    </div> : null}
    {sec === 'feeback' ? <>
    <div className="m-seg fcl-tabs" role="tablist" aria-label="Fee-Back">{[['path', '↻ The return path'], ['calc', '🧮 Fee-Back calculator']].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`feecat-tab-${k}`}>{l}</button>)}</div>
    <div className="fcl-pane">{children ? children(tab) : null}</div></> : null}
    </div>
  </section>;
}
