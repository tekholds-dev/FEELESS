import React, { Suspense, lazy, useEffect, useMemo, useRef, useState } from 'react';
import { motion, useInView, useScroll, useSpring } from 'motion/react';
import { FeeBackFlow } from './FeeBack';
import { Tokenomics } from './FeeCommand';
import { StakeStory } from './KeepDeal';
import { useMarket } from '../../hooks/useMarket';
import { Ic3 } from '../../lib/icon3d';
import { isCalm } from '../../lib/fxPause';
import { identityOf, inkOf, part, fitBox } from '../../lib/proofprint';
import '../../styles/whitepaper.css';

const StakeFlow = lazy(() => import('./StakeFlow'));

// 📖 THE WHITEPAPER, READ AS A STORY (owner 2026-11-06: "full, with each section having a real true animated example"). Every chapter is open, every word stays, and beside it runs a live example of what that chapter says: real market data or the real rules, never a made up number. Examples play when they scroll into view.
const SHELVES = [
  ['start', 'Start', ['Executive Summary', 'The Problem With On-Chain Fees', 'What FEELESS Is', 'What FEELESS Is NOT', 'Conclusion']],
  ['money', '$FEE + Fee-Back', ['The $FEE Ecosystem Asset', '$FEE Tokenomics', 'Fee-Back Architecture', 'How Eligible Fees Are Tracked', 'How FeeCat Makes the Fee-Back Experience Work', 'FeeCat', 'Revenue Model']],
  ['agents', 'Agents', ['Agents and Two Minds', 'The Five Proofs', 'The Fingerprint', 'The Collective and the Stake']],
  ['product', 'Product', ['The FEELESS Terminal', 'The Global Ecosystem Globe', 'Trading & Routing Architecture', 'FUSE Cards', 'Runners, Arena and Prime Cards', 'Top-Tier Cards and the Vault', 'Automation and the FUSE Card Contract', 'Community / Trenches']],
  ['data', 'Data + trust', ['Reputation, Bot Shield and Rewards Integrity', 'Market Data Architecture', 'Supported Ecosystems', 'Security Principles', 'Wallet & Transaction Principles', 'Transparency Principles']],
  ['next', 'Roadmap', ['Roadmap', 'Future Development']],
  ['risk', 'Risks', ['Risk Factors', 'Disclosures']],
];

/** A chapter's text → its first sentence and its other sentences, every word kept. */
export function splitChapter(text) {
  const parts = String(text || '').split(/(?<=[.!?])\s+(?=[A-Z$0-9])/);
  return { lead: parts[0] || '', points: parts.slice(1) };
}

/** Which shelf holds a chapter. A new chapter nobody placed still shows, on the first shelf. */
export function shelfOf(title) {
  return (SHELVES.find(s => s[2].includes(title)) || SHELVES[0])[0];
}

// Steps through a list while it is on screen, and rests when it is not.
function useBeat(n, every = 1400) {
  const box = useRef(null); const seen = useInView(box, { margin: '-10% 0px' }); const [at, setAt] = useState(0);
  useEffect(() => { if (!seen || isCalm()) { if (isCalm()) setAt(n - 1); return undefined; } const t = setInterval(() => setAt(x => (x + 1) % (n + 1)), every); return () => clearInterval(t); }, [seen, n, every]);
  return [box, Math.min(at, n - 1)];
}
const Frame = ({ tag, children, foot }) => <figure className="wps-demo"><figcaption><i className="wps-dot" aria-hidden="true" />{tag}</figcaption><div className="wps-demo-b">{children}</div>{foot ? <small className="wps-foot">{foot}</small> : null}</figure>;

// Real coins, right now.
const usdShort = v => { const n = Number(v) || 0; return n >= 1e9 ? `$${(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(1)}K` : `$${n.toFixed(0)}`; };
function LiveTape() {
  const { data } = useMarket('/feed?kind=trending&chain=solana&page=1', 20000); const rows = (data?.items || data?.pairs || data?.rows || (Array.isArray(data) ? data : [])).slice(0, 6); const top = Math.max(1, ...rows.map(r => Number(r.volume24h ?? r.volume?.h24 ?? 0)));
  return <Frame tag="LIVE: WHAT IS TRADING RIGHT NOW" foot="Real pools, read a moment ago.">{rows.length ? <ul className="wps-tape" data-testid="wps-tape">{rows.map((r, i) => { const v = Number(r.volume24h ?? r.volume?.h24 ?? 0); const ch = Number(r.priceChange24h ?? r.priceChange?.h24 ?? 0); return <motion.li key={r.pairAddress || r.address || i} initial={{ opacity: 0, x: -14 }} whileInView={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }} viewport={{ once: true }}><b>{r.baseToken?.symbol || r.symbol || r.baseSymbol || 'Coin'}</b><span aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.03, v / top)})` }} /></span><em className="m-num">{usdShort(v)}</em><small className={`m-num ${ch >= 0 ? 'is-up' : 'is-dn'}`}>{ch >= 0 ? '+' : ''}{ch.toFixed(1)}%</small></motion.li>; })}</ul> : <p className="wps-wait">Reading the market…</p>}</Frame>;
}
// A row of steps, lit one at a time.
function Steps({ tag, rows, foot, testid }) {
  const [box, at] = useBeat(rows.length);
  return <div ref={box}><Frame tag={tag} foot={foot}><ol className="wps-steps" data-testid={testid}>{rows.map(([ic, t, s], i) => <li key={t} className={i < at ? 'is-done' : i === at ? 'is-on' : ''}><span className="wps-step-ic"><Ic3 e={ic} size="26px" /></span><span><b>{t}</b><small>{s}</small></span></li>)}</ol></Frame></div>;
}
const TOLLS = [['⛓', 'Network', 'What the chain charges'], ['💧', 'The pool', 'What the DEX takes'], ['🧭', 'The router', 'The aggregator'], ['⚡', 'Priority', 'To land it fast'], ['🧾', 'The app', 'Whatever the front end adds']];
const SWAP = [['🪙', 'You pick the coins', 'Nothing quotes until you ask'], ['🔎', 'You get a quote', 'The route is simulated first'], ['✍', 'Your wallet signs', 'FEELESS never holds your keys'], ['🛡', 'The message is checked', 'It must equal what was quoted'], ['🚀', 'It lands once', 'No resubmits']];
const TRACK = [['🧾', 'A fee is paid', 'The real amount, on chain'], ['📒', 'It joins the ledger', 'Totals rebuild from that ledger'], ['✅', 'It is checked', 'Is it eligible, and whose is it?'], ['🐱', 'FeeCat delivers it', 'Only under the published rules']];
const CARD = [['🧩', 'Coins join the card', 'Several coins, one approval'], ['⏱', 'A round runs', 'On its own clock'], ['✂', 'Winners get trimmed', 'By its rules, not by a mood'], ['🧯', 'A rug is sold', 'Guards run before every buy']];
const SHIELD = [['🕵', 'Bots get read', 'Eight engines, with evidence'], ['📈', 'Trust is scored', 'From what a wallet really did'], ['🎁', 'Rewards are guarded', 'Farming earns nothing'], ['🔓', 'You can see why', 'Every warning shows its proof']];
const MINDS = [['🧠', 'Mind A reads alone', 'Its own browser and its own sources'], ['🧠', 'Mind B reads alone', 'It cannot see what A said'], ['🤝', 'They compare', 'Agree, and it acts'], ['📁', 'It is filed', 'Won or lost, it is kept']];
const PROOFS = [['⛏', 'PoW', 'A real trade, chosen and managed'], ['📉', 'PoP', 'A perps call on true prices'], ['🎲', 'PoB', 'A call on a game or a market'], ['📣', 'PoC', 'What is trending, proposed blind'], ['💻', 'PoStatic', 'A real page, built and tested']];
const NOT = [['🏦', 'Not a bank'], ['📜', 'Not investment advice'], ['🔑', 'Not holding your keys'], ['🎰', 'Not a promised return']];
function Crossed() {
  const [box, at] = useBeat(NOT.length);
  return <div ref={box}><Frame tag="WHAT IT IS NOT"><ul className="wps-not">{NOT.map(([ic, t], i) => <li key={t} className={i <= at ? 'is-off' : ''}><Ic3 e={ic} size="24px" /><b>{t}</b></li>)}</ul></Frame></div>;
}
// A print draws itself, ridge by ridge: the same maths as every agent's real print.
function PrintDraw({ seed = 'feeless-collective' }) {
  const id = useMemo(() => identityOf(seed), [seed]); const [box, at] = useBeat(12, 450); const rings = useMemo(() => Array.from({ length: 12 }, (_, i) => ({ d: part(id, i * 2 + 2, 0.1, 6.18, 44), ink: inkOf([92, 40, 71, 85, 60, 95, 33, 77, 88, 58, 91, 69][i]) })), [id]);
  return <div ref={box}><Frame tag="A PRINT, DRAWING ITSELF" foot="Each ridge is a finished proof. Bright when it did well, dim when it did badly."><svg className="wps-print" viewBox={fitBox(28, id)} role="img" aria-label="A fingerprint drawing itself one ridge at a time" data-testid="wps-print">{rings.map((r, i) => <motion.path key={i} d={r.d} stroke={r.ink} fill="none" strokeWidth="4" strokeLinecap="round" initial={false} animate={{ pathLength: i <= at ? 1 : 0, opacity: i <= at ? 1 : 0.08 }} transition={{ duration: 0.45 }} />)}</svg></Frame></div>;
}
// What a pool really risks: the true maths of a whole range position when the price moves.
export const poolLoss = move => { const r = Math.max(0.01, 1 + move / 100); return (2 * Math.sqrt(r)) / (1 + r) - 1; };
function RiskSlider() {
  const [move, setMove] = useState(-50); const loss = poolLoss(move) * 100; const held = move; const pts = useMemo(() => Array.from({ length: 41 }, (_, i) => { const m = -90 + i * 5.5; return [m, poolLoss(m) * 100]; }), []); const x = m => ((m + 90) / 220) * 300; const y = v => 10 + (-v / 40) * 110;
  return <Frame tag="TRY IT: WHAT A PRICE MOVE COSTS A POOL" foot="The real maths of a whole range position, before fees. On top of this a coin can go to zero, and a venue can fail."><div className="wps-try"><svg viewBox="0 0 300 130" role="img" aria-label={`A ${move}% price move costs a pool position ${Math.abs(loss).toFixed(1)}%`}><path d={`M${pts.map(([m, v]) => `${x(m).toFixed(1)} ${y(v).toFixed(1)}`).join(' L')}`} fill="none" stroke="#ff8fa3" strokeWidth="2.5" /><line x1={x(move)} x2={x(move)} y1="4" y2="126" stroke="#ffffff40" strokeDasharray="3 3" /><motion.circle r="6" fill="#ff8fa3" stroke="#0a0f18" strokeWidth="2" initial={false} animate={{ cx: x(move), cy: y(loss) }} transition={{ type: 'spring', stiffness: 240, damping: 24 }} /></svg>
    <label><small>THE COIN MOVES</small><input type="range" min={-90} max={130} value={move} onChange={e => setMove(Number(e.target.value))} aria-label="How far the price moves" data-testid="wps-risk-move" /><b className="m-num">{move > 0 ? '+' : ''}{move}%</b></label>
    <div className="wps-try-n"><span><small>JUST HOLDING</small><b className={`m-num ${held < 0 ? 'is-dn' : 'is-up'}`}>{held > 0 ? '+' : ''}{held.toFixed(0)}%</b></span><span><small>EXTRA LOST IN A POOL</small><b className="m-num is-dn" data-testid="wps-risk-loss">{loss.toFixed(1)}%</b></span></div></div></Frame>;
}
const Stake = () => <div className="wps-stack"><StakeStory testid="wps-story" /><Suspense fallback={null}><StakeFlow usd={5} grade={300} x={3} points={15} seat={2.1} testid="wps-map" /></Suspense></div>;
const Visual = ({ node, tag }) => <Frame tag={tag}>{node}</Frame>;
const DEMO = {
  'Executive Summary': () => <LiveTape />, 'What FEELESS Is': () => <LiveTape />, 'What FEELESS Is NOT': () => <Crossed />, Conclusion: () => <PrintDraw seed="feeless" />,
  'The Problem With On-Chain Fees': () => <Steps tag="ONE SWAP, EVERY TOLL ON THE WAY" rows={TOLLS} foot="Which ones apply, and how much, changes with every route." testid="wps-tolls" />,
  'The $FEE Ecosystem Asset': () => <Visual tag="LIVE: $FEE" node={<Tokenomics compact />} />, '$FEE Tokenomics': () => <Visual tag="THE TOKENOMICS" node={<Tokenomics compact />} />, 'Fee-Back Architecture': () => <Visual tag="HOW A FEE COMES BACK" node={<FeeBackFlow />} />,
  'How Eligible Fees Are Tracked': () => <Steps tag="ONE FEE, FOLLOWED" rows={TRACK} />, 'How FeeCat Makes the Fee-Back Experience Work': () => <Steps tag="ONE FEE, FOLLOWED" rows={TRACK} />, FeeCat: () => <PrintDraw seed="feecat" />, 'Revenue Model': () => <Stake />,
  'Agents and Two Minds': () => <Steps tag="TWO MINDS, ONE CALL" rows={MINDS} testid="wps-minds" />, 'The Five Proofs': () => <Steps tag="THE FIVE PROOFS" rows={PROOFS} testid="wps-proofs" />, 'The Fingerprint': () => <PrintDraw seed="the-collective" />, 'The Collective and the Stake': () => <Stake />,
  'The FEELESS Terminal': () => <LiveTape />, 'The Global Ecosystem Globe': () => <LiveTape />, 'Trading & Routing Architecture': () => <Steps tag="ONE SWAP, START TO FINISH" rows={SWAP} testid="wps-swap" />, 'Wallet & Transaction Principles': () => <Steps tag="ONE SWAP, START TO FINISH" rows={SWAP} />,
  'FUSE Cards': () => <Steps tag="ONE CARD, ONE ROUND" rows={CARD} testid="wps-card" />, 'Runners, Arena and Prime Cards': () => <Steps tag="ONE CARD, ONE ROUND" rows={CARD} />, 'Top-Tier Cards and the Vault': () => <Steps tag="ONE CARD, ONE ROUND" rows={CARD} />, 'Automation and the FUSE Card Contract': () => <Steps tag="ONE CARD, ONE ROUND" rows={CARD} />, 'Community / Trenches': () => <LiveTape />,
  'Reputation, Bot Shield and Rewards Integrity': () => <Steps tag="HOW TRUST IS EARNED" rows={SHIELD} testid="wps-shield" />, 'Security Principles': () => <Steps tag="HOW TRUST IS EARNED" rows={SHIELD} />, 'Transparency Principles': () => <PrintDraw seed="transparency" />, 'Market Data Architecture': () => <LiveTape />, 'Supported Ecosystems': () => <LiveTape />,
  'Future Development': () => <PrintDraw seed="future" />, 'Risk Factors': () => <RiskSlider />, Disclosures: () => <RiskSlider />,
};

// 🛤 The road, one milestone at a time, each with its own live example.
const ROAD_DEMO = { '01': () => <LiveTape />, '02': () => <PrintDraw seed="intelligence" />, '03': () => <Steps tag="HOW TRUST IS EARNED" rows={SHIELD} />, '04': () => <Steps tag="ONE SWAP, START TO FINISH" rows={SWAP} />, '05': () => <Steps tag="ONE CARD, ONE ROUND" rows={CARD} />, '06': () => <Steps tag="ONE CARD, ONE ROUND" rows={CARD} />, '07': () => <PrintDraw seed="seasons" />, '08': () => <Steps tag="ONE CARD, ONE ROUND" rows={CARD} />, '09': () => <RiskSlider />, '10': () => <Steps tag="ONE FEE, FOLLOWED" rows={TRACK} />, '11': () => <PrintDraw seed="launch" /> };
export function MissionStory({ missions = [], filter = 'ALL' }) {
  const rows = missions.filter(m => filter === 'ALL' || m[2] === filter);
  return <div className="wps wps-road" data-testid="mission-story">{rows.map((m, i) => { const Demo = ROAD_DEMO[m[0]] || (() => <PrintDraw seed={m[1]} />); return <motion.section key={m[0]} className={`wps-ch${i % 2 ? ' is-flip' : ''}`} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: '-8% 0px' }} transition={{ duration: 0.35 }} data-testid={`mission-${m[0]}`}><div className="wps-text"><span className="wps-n m-num">{m[0]}</span><em className={`wps-st is-${String(m[2]).toLowerCase()}`}>{m[2]}</em><h2>{m[1]}</h2><p className="wps-lead">{m[3]}</p></div><div className="wps-side"><Demo /></div></motion.section>; })}</div>;
}

function Chapter({ c, i, roadmap, onSeen }) {
  const { lead, points } = splitChapter(c.text); const Demo = DEMO[c.title];
  return <motion.section id={c.id} className={`wps-ch${i % 2 ? ' is-flip' : ''}`} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ margin: '-40% 0px -50% 0px', amount: 'some' }} onViewportEnter={() => onSeen?.(c.shelf)} transition={{ duration: 0.35 }} data-testid={`whitepaper-chapter-${c.number}`}>
    <div className="wps-text"><span className="wps-n m-num">{String(c.number).padStart(2, '0')}</span><h2>{c.title}</h2><p className="wps-lead">{lead}</p>{points.length ? <ul>{points.map(p => <li key={p}>{p}</li>)}</ul> : null}</div>
    <div className="wps-side">{c.title === 'Roadmap' && roadmap ? roadmap : Demo ? <Demo /> : <PrintDraw seed={c.title} />}</div></motion.section>;
}

export function WhitepaperChapters({ chapters = [], roadmap = null }) {
  const { scrollYProgress } = useScroll(); const scale = useSpring(scrollYProgress, { stiffness: 120, damping: 30 }); const [now, setNow] = useState('start');
  const ordered = useMemo(() => SHELVES.flatMap(([k]) => chapters.filter(c => shelfOf(c.title) === k).map(c => ({ ...c, shelf: k }))), [chapters]);
  const go = k => { setNow(k); const first = ordered.find(c => c.shelf === k); document.getElementById(first?.id || '')?.scrollIntoView?.({ behavior: 'smooth', block: 'start' }); };
  return <div className="wps" data-testid="whitepaper-chapters"><motion.i className="wps-bar" style={{ scaleX: scale }} aria-hidden="true" />
    <nav className="wps-nav m-seg" aria-label="Whitepaper sections">{SHELVES.map(([k, l]) => <button key={k} type="button" className={now === k ? 'active' : ''} aria-pressed={now === k} onClick={() => go(k)} data-testid={`wpc-shelf-${k}`}>{l}</button>)}</nav>
    <p className="wps-risk m-glass" data-testid="wpc-risk-line"><b>Crypto can lose all its value. This is not financial advice.</b><button type="button" className="m-btn" onClick={() => go('risk')} data-tip="Risk factors and disclosures">Read the risks</button></p>
    {ordered.map((c, i) => <Chapter key={c.id} c={c} i={i} roadmap={roadmap} onSeen={setNow} />)}
  </div>;
}
