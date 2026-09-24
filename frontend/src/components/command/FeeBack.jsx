import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowDown, ArrowUpRight, Coins, Cat, Check, Play, Wallet, ShieldCheck, Activity, Shuffle, Sparkles, Copy, CheckCircle2 } from 'lucide-react';
import { useWallet } from '../../hooks/useWallet';
import { useMarket } from '../../hooks/useMarket';
import { formatUSD } from '../../lib/dexscreener';
import { FeelessMark } from '../FeelessLogo';
const STEPS = [
  ['TRADE', 'A user approves a transaction. Normal network, DEX and provider fees may apply.'],
  ['FEE DETECTED', 'Actual settled fee data is sourced from the transaction or eligible provider record. A quote is not a settled fee.'],
  ['ELIGIBILITY VERIFIED', 'Published program rules determine which fees qualify. These rules are not activated yet.'],
  ['USD VALUE RECORDED', 'The eligible fee value is recorded in USD, with its source and transaction reference.'],
  ['FEECAT EQUIVALENT CALCULATED', 'Eligible USD value is divided by the verified FEECAT reference price at the defined distribution point.'],
  ['FEECAT DISTRIBUTED', 'The qualifying wallet receives the calculated FEECAT amount. No distributions are currently activated.'],
  ['FEE-BACK COMPLETE', 'A verifiable distribution transaction completes the record. FEECAT value can change after receipt.'],
];

export const FeeBackFlow = () => {
  const [step, setStep] = useState(0);
  return <section className="fee-flow"><div className="command-section-title"><span><Activity size={16} />THE RETURN PATH</span><small>ARCHITECTURE EXPLORER / PLANNED</small></div><div className="flow-track">{STEPS.map(([label], i) => <button key={label} onClick={() => setStep(i)} data-testid={`feeback-flow-step-${i}`} className={`${i === step ? 'current' : ''} ${i < step ? 'visited' : ''}`}><span>{String(i + 1).padStart(2, '0')}</span><b>{label}</b>{i < STEPS.length - 1 && <i />}</button>)}</div><div className="flow-explanation" data-testid="feeback-flow-description"><span>0{step + 1}</span><p>{STEPS[step][1]}</p><button data-testid="feeback-flow-next" onClick={() => setStep(s => (s + 1) % STEPS.length)} title="Next architecture step"><ArrowUpRight size={18} /></button></div><small className="provider-note">This animation explains the intended mechanism. It does not represent a real transaction, eligibility decision or payout.</small></section>;
};

export const FeeBackCalculator = ({ feeCat, compact = false }) => {
  const [eligible, setEligible] = useState('60');
  const amount = Number(eligible); const valid = eligible !== '' && Number.isFinite(amount) && amount >= 0;
  const price = feeCat?.status === 'market_observed' && !feeCat.stale ? Number(feeCat.pair?.priceUsd) : null;
  return <section className={`feeback-calculator ${compact ? 'compact-calculator' : ''}`}><div className="command-section-title"><span><Coins size={16} />FEE-BACK VISION</span><small>ILLUSTRATIVE CALCULATOR / NOT A PAYOUT</small></div><div className="calculator-input"><label htmlFor={compact ? 'fee-illustration-compact' : 'fee-illustration'}>Eligible tracked fees · example USD</label><span>$<input id={compact ? 'fee-illustration-compact' : 'fee-illustration'} data-testid={compact ? 'feeback-example-input-compact' : 'feeback-example-input'} inputMode="decimal" type="number" min="0" step="0.01" value={eligible} onChange={e => setEligible(e.target.value)} /></span></div><div className="calculator-return"><span>100% ELIGIBLE FEE VALUE</span><strong data-testid={compact ? 'feeback-dollar-equivalent-compact' : 'feeback-dollar-equivalent'}>{valid ? formatUSD(amount) : '—'}</strong><small>equivalent in FEECAT at distribution</small></div><div className="calculator-detail"><span>FEECAT quantity</span><b data-testid={compact ? 'feeback-token-equivalent-compact' : 'feeback-token-equivalent'}>{valid && price > 0 ? `≈ ${(amount / price).toLocaleString('en-US', { maximumFractionDigits: 6 })}` : 'Awaiting verified reference price'}</b></div><p>Quantity = eligible USD ÷ verified FEECAT USD price. {price > 0 ? 'This current-market illustration is not a distribution quote.' : 'No FEECAT price is assumed.'} The official distribution point and rules are not activated.</p></section>;
};

export const FeeBackPreview = ({ quote, feeCat }) => <section className="fee-preview"><div className="command-section-title"><span><Cat size={15} />FEE-BACK PREVIEW</span><span className="state-tag amber">PLANNED</span></div><dl><div><dt>Trade value</dt><dd>{formatUSD(quote?.swapUsdValue ?? quote?.inputValue)}</dd></div><div><dt>Network signature fee · estimate</dt><dd>{quote?.signatureFeeLamports != null ? `${Number(quote.signatureFeeLamports) / 1e9} SOL` : 'Unavailable'}</dd></div><div><dt>DEX / route fee</dt><dd>{quote?.feeBps != null ? `${quote.feeBps} bps · ${quote.feeMint || 'provider fee mint'}` : 'Provider dependent'}</dd></div><div><dt>Eligible FEELESS fee</dt><dd>Not yet determined</dd></div><div><dt>Estimated FEECAT distribution</dt><dd>Not activated</dd></div></dl><p>100% of qualifying tracked fee value is intended to return in FEECAT. Normal fees still apply. Eligibility, reference pricing and distribution rules must be activated first.</p><Link data-testid="swap-feeback-rules" to="/terminal/feeback">View the economic model<ArrowUpRight size={12} /></Link></section>;

export const FeeBackCenter = ({ feeCat }) => {
  const { wallet } = useWallet();
  const { data: history } = useMarket(wallet?.chain === 'solana' ? `/api/trading/history/${wallet.address}` : null, 30000);
  return <div className="fee-back-center"><div className="command-page-title"><span className="eyebrow">THE ECONOMIC FEE-RETURN LAYER</span><h1>The fees come back.<br /><em>The story moves forward.</em></h1><p>100% of eligible tracked fees. Equivalent dollar value. Delivered through FeeCat under program rules.</p><span className="state-tag amber">PROGRAM PLANNED · NO PAYOUTS ACTIVATED</span></div><div className="fee-back-summary">{[['ELIGIBLE TRACKED FEES', 'Awaiting rules'], ['PENDING FEECAT', 'Not activated'], ['COMPLETED DISTRIBUTIONS', 'No verified records'], ['REFERENCE PRICE', feeCat?.status === 'market_observed' ? 'Distribution point undefined' : 'Awaiting verified market']].map(([label, value], i) => <div key={label}><small>{label}</small><strong data-testid={`feeback-summary-${i}`}>{value}</strong></div>)}</div><FeeBackFlow /><div className="feeback-two-col"><FeeBackCalculator feeCat={feeCat} /><section className="program-rules"><span className="eyebrow">THE IMPORTANT DISTINCTION</span><h2>Economically fee-less.<br />Not magically gas-free.</h2><p>Network, DEX and provider fees can still apply. Fee-Back records eligible USD value and returns its FEECAT equivalent at a defined distribution point.</p><ul><li>Eligibility is not automatic for every fee.</li><li>Quoted fees are not settled fee records.</li><li>FEECAT can change in value after distribution.</li><li>No guaranteed profit, yield or future value.</li></ul><Link data-testid="feeback-whitepaper-link" to="/terminal/whitepaper">Read the full architecture<ArrowUpRight size={14} /></Link></section></div><section className="distribution-history"><div className="command-section-title"><span>TRANSACTION REFERENCES</span><small>APPLICATION-SUBMITTED SWAPS / NOT REWARDS</small></div>{!wallet && <div className="truth-empty" data-testid="feeback-wallet-required"><Wallet size={24} /><span>Connect your wallet to view its application transaction references.</span></div>}{wallet && !history?.transactions?.length && <div className="truth-empty" data-testid="feeback-history-empty">No verified application transaction references for this wallet.</div>}{history?.transactions?.map(tx => <a data-testid={`feeback-transaction-${tx.order_id}`} key={tx.order_id} target="_blank" rel="noreferrer" href={`https://solscan.io/tx/${tx.signature}`}><span>{tx.state}</span><code>{tx.signature.slice(0, 20)}…</code><ArrowUpRight size={14} /></a>)}</section></div>;
};

export const CAT_VARIATIONS = [
  ['Mint Mackerel', '#b9f4d7', '#087a58', 'stripes'], ['Midnight Patch', '#1c2930', '#f7d36b', 'patch'], ['Solaris', '#ffbf69', '#d94e41', 'spots'],
  ['Cloud Nine', '#f5f0e8', '#a9b9c8', 'patch'], ['Berry Socks', '#e78aa8', '#5b2b55', 'spots'], ['Lime Sprout', '#c9ee68', '#3e8e52', 'stripes'],
  ['Copper Tabby', '#c87842', '#713d27', 'stripes'], ['Bluebell', '#99b8ef', '#4b54a8', 'spots'], ['Tux Bloom', '#f4f4ec', '#171c25', 'patch'],
  ['Peach Fizz', '#ffc7a4', '#e55c72', 'spots'], ['Mossy', '#849c75', '#314a36', 'patch'], ['Lavender Loop', '#cbb8ed', '#6b54a5', 'stripes'],
  ['Neon Paws', '#66f2d0', '#734cf2', 'spots'], ['Caramel Dot', '#d99d59', '#8a4b35', 'patch'], ['Moonstone', '#c7d2d9', '#54616e', 'stripes'],
  ['Rosewater', '#f4b4be', '#9c3d65', 'spots'], ['Golden Hour', '#f1d36b', '#b36a2e', 'patch'], ['Inkblot', '#41485a', '#10141c', 'spots'],
  ['Cactus Cat', '#a4d58c', '#2a6a5b', 'stripes'], ['Creamsicle', '#ffe0a3', '#f08042', 'patch'], ['Orchid', '#df9ce8', '#763e9a', 'spots'],
  ['Raincoat', '#89c6d8', '#284f72', 'stripes'], ['Pistachio', '#d7e8a4', '#718e47', 'patch'], ['Firefly', '#e9ed72', '#574278', 'spots'],
  ['Paper Tiger', '#eee5d0', '#b87952', 'stripes'],
];

export const CatAvatar = ({ cat, large = false }) => {
  const [name, fur, accent, pattern] = cat;
  const spots = pattern === 'spots' ? <><circle cx="38" cy="74" r="7" fill={accent} /><circle cx="76" cy="54" r="5" fill={accent} /><circle cx="81" cy="87" r="8" fill={accent} /><circle cx="49" cy="102" r="4" fill={accent} /></> : null;
  const stripes = pattern === 'stripes' ? <><path d="M38 52l10 18M52 47l10 19M68 47l9 17M82 52l7 13" stroke={accent} strokeWidth="5" strokeLinecap="round" /><path d="M42 106l-4 13M59 109v14M77 107l4 13" stroke={accent} strokeWidth="5" strokeLinecap="round" /></> : null;
  const patch = pattern === 'patch' ? <path d="M25 53c11-16 29-15 39-5 4 4 3 17-5 25-8 8-24 5-34-2z" fill={accent} opacity=".9" /> : null;
  return <svg className={`feeless-cat-art ${large ? 'large' : ''}`} viewBox="0 0 120 140" role="img" aria-label={`${name} Feeless Cat`}>
    <defs><linearGradient id={`fur-${name.replace(/\W/g, '')}`} x1="0" y1="0" x2="1" y2="1"><stop stopColor={fur} /><stop offset="1" stopColor={accent} stopOpacity=".7" /></linearGradient></defs>
    <path d="M24 58 22 23l24 19c8-3 19-3 28 0l24-19-2 36c6 8 7 20 2 31-8 17-25 28-49 28S30 106 22 89c-5-11-4-23 2-31Z" fill={`url(#fur-${name.replace(/\W/g, '')})`} stroke="#15211d" strokeWidth="4" strokeLinejoin="round" />
    {spots}{stripes}{patch}
    <path d="M40 77c4-5 10-5 14 0M66 77c4-5 10-5 14 0" fill="none" stroke="#15211d" strokeWidth="4" strokeLinecap="round" />
    <circle cx="49" cy="77" r="3" fill="#15211d" /><circle cx="73" cy="77" r="3" fill="#15211d" />
    <path d="M55 90q5 5 10 0M60 92v7M45 91 22 87M45 97 20 99M75 91l23-4M75 97l25 2" fill="none" stroke="#15211d" strokeWidth="2.5" strokeLinecap="round" />
    <path d="M32 126q28 9 56 0" fill="none" stroke="#00e9a0" strokeWidth="3" strokeLinecap="round" opacity=".9" />
  </svg>;
};

export const FeelessCats = () => {
  const [selected, setSelected] = useState(0);
  const [filter, setFilter] = useState('all');
  const [notice, setNotice] = useState('');
  const visibleCats = useMemo(() => filter === 'all' ? CAT_VARIATIONS : CAT_VARIATIONS.filter(([, , , pattern]) => pattern === filter), [filter]);
  const activeCat = CAT_VARIATIONS[selected] || CAT_VARIATIONS[0];
  const pickCat = cat => { const index = CAT_VARIATIONS.indexOf(cat); setSelected(index); setNotice(`${cat[0]} selected`); };
  const randomCat = () => {
    if (CAT_VARIATIONS.length < 2) return;
    const nextIndex = (selected + 1 + Math.floor(Math.random() * (CAT_VARIATIONS.length - 1))) % CAT_VARIATIONS.length;
    pickCat(CAT_VARIATIONS[nextIndex]);
  };
  const copyName = async () => { try { await navigator.clipboard.writeText(`FEECAT-${String(selected + 1).padStart(2, '0')}`); setNotice('Cat ID copied'); } catch { setNotice('Cat ID ready to copy'); } };
  return <div className="feeless-cats-page">
    <div className="cats-page-head"><div><span className="eyebrow"><Cat size={13} /> FEECAT COLLECTION / 25 VARIATIONS</span><h1>Find your <em>Feeless Cat.</em></h1><p>Pick a color, claim a mood, and make your corner of the FEELESS network recognizable.</p></div><Link to="/terminal/feecat" className="btn-outline" data-testid="feecats-back">FeeCat home <ArrowUpRight size={14} /></Link></div>
    <div className="cats-stat-row"><div><strong>25</strong><span>CAT VARIATIONS</span></div><div><strong>3</strong><span>FUR PATTERNS</span></div><div><strong className="positive">LIVE</strong><span>COLLECTION STATUS</span></div><button className="btn-primary" type="button" onClick={randomCat} data-testid="feecats-random"><Shuffle size={15} /> Surprise me</button></div>
    <div className="cats-workbench">
      <section className="cats-gallery"><div className="cats-section-head"><div><h2>Choose a coat</h2><small>Every cat is different. None are minted or owned yet.</small></div><div className="cats-filters" role="group" aria-label="Filter cats">{[['all', 'All'], ['spots', 'Spotted'], ['patch', 'Patchy'], ['stripes', 'Tabby']].map(([id, label]) => <button type="button" key={id} className={filter === id ? 'active' : ''} aria-pressed={filter === id} onClick={() => setFilter(id)} data-testid={`feecats-filter-${id}`}>{label}</button>)}</div></div><div className="cat-card-grid">{visibleCats.map(cat => <button type="button" className={`cat-card ${activeCat === cat ? 'selected' : ''}`} key={cat[0]} onClick={() => pickCat(cat)} data-testid={`feecat-card-${cat[0].toLowerCase().replaceAll(' ', '-')}`}><span className="cat-card-art"><CatAvatar cat={cat} /></span><span className="cat-card-info"><b>{cat[0]}</b><small>FEECAT #{String(CAT_VARIATIONS.indexOf(cat) + 1).padStart(2, '0')}</small></span><span className="cat-card-swatch" style={{ background: cat[1] }} /></button>)}</div></section>
      <aside className="cat-preview-panel"><div className="cat-preview-top"><span className="state-tag">AVAILABLE TO EXPLORE</span><button type="button" title="Copy cat ID" aria-label="Copy cat ID" onClick={copyName}><Copy size={15} /></button></div><div className="cat-preview-art"><span className="cat-preview-glow" /><CatAvatar cat={activeCat} large /></div><span className="eyebrow">YOUR CURRENT PICK</span><h2>{activeCat[0]}</h2><p>FEECAT #{String(selected + 1).padStart(2, '0')} · {activeCat[3]} coat · community edition</p><div className="cat-traits"><span><small>COAT</small><b>{activeCat[3].toUpperCase()}</b></span><span><small>STATUS</small><b className="positive">OPEN</b></span></div><button type="button" className="btn-primary cat-select-button" onClick={() => setNotice(`${activeCat[0]} is your featured cat`)} data-testid="feecats-select">Set as featured cat <Sparkles size={15} /></button>{notice && <p className="cat-action-notice" role="status"><CheckCircle2 size={14} />{notice}</p>}<small className="cat-preview-footnote">This is a visual collection experience. No wallet signature or purchase is requested.</small></aside>
    </div>
  </div>;
};

export const FeeCatCenter = ({ asset, community, onSelect }) => {
  const [mission, setMission] = useState(() => localStorage.getItem('feecat-learning-step') || 'culture');
  const choose = v => { setMission(v); localStorage.setItem('feecat-learning-step', v); };
  const text = { culture: 'The first cat of FEELESS. A shared identity built around curiosity, participation and on-chain culture.', community: 'The Trenches connect real participants. No purchased-looking activity, fabricated messages or imaginary users.', utility: 'The intended delivery asset for eligible USD-equivalent Fee-Back. Distribution infrastructure and rules remain planned.' };
  return <div className="feecat-command"><div className="feecat-banner" style={{ backgroundImage: "url('/assets/feecat-bg.png')" }}><div className="feecat-banner-copy"><span className="eyebrow">THE FIRST CAT OF FEELESS</span><h1>Fun. Culture.<br /><em>More for you.</em></h1><p>The community layer. The culture layer.<br />The Fee-Back delivery layer.</p><span className="state-tag amber" data-testid="feecat-launch-state">{asset?.status === 'market_observed' ? 'MARKET OBSERVED · DISTRIBUTIONS PLANNED' : 'AWAITING MARKET · DISTRIBUTIONS PLANNED'}</span><Link className="btn-primary feecat-collection-cta" to="/terminal/feecat/cats" data-testid="feecat-collection-link"><Cat size={15} />Explore Feeless Cats<ArrowUpRight size={15} /></Link></div><div className="feecat-insignia"><img src="/assets/feecat-mark.png" alt="FEECAT cat mark" /><span>FEECAT</span></div></div><div className="fee-back-summary">{[['FEECAT RECEIVED', 'No verified distributions'], ['TREASURY STATUS', 'Not published / unverified'], ['COMMUNITY / 7 DAYS', community?.messages != null ? `${community.messages} actual messages` : 'Connecting'], ['CURRENT MARKET', asset?.status === 'market_observed' ? formatUSD(asset.pair?.priceUsd) : 'Awaiting provider market']].map(([k, v], i) => <div key={k}><small>{k}</small><strong data-testid={`feecat-stat-${i}`}>{v}</strong></div>)}</div><div className="feecat-lore"><div className="lore-tabs">{Object.keys(text).map(k => <button data-testid={`feecat-lore-${k}`} key={k} onClick={() => choose(k)} className={mission === k ? 'active' : ''}>{k}</button>)}</div><h2>{mission === 'culture' ? 'A little mischief. A real purpose.' : mission === 'community' ? 'A community, not a counter.' : 'Culture meets the return path.'}</h2><p data-testid="feecat-lore-text">{text[mission]}</p><Link to={mission === 'community' ? '/terminal/chat' : mission === 'utility' ? '/terminal/feeback' : '/terminal/learn'} data-testid="feecat-mission-action">{mission === 'community' ? 'Join your ecosystem room' : mission === 'utility' ? 'Explore Fee-Back' : 'Understand FEELESS'}<ArrowUpRight size={16} /></Link><small>Learning missions are local navigation progress, not token entitlements.</small></div><FeeBackFlow /><FeeBackCalculator feeCat={asset} />{asset?.pair && <button className="btn-primary" data-testid="feecat-open-market" onClick={() => onSelect(asset.pair)}>Open FEECAT market<ArrowUpRight size={16} /></button>}</div>;
};