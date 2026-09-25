import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Clock3,
  Coins,
  Copy,
  Flame,
  Gauge,
  Image as ImageIcon,
  LoaderCircle,
  LockKeyhole,
  Rocket,
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
  Timer,
  Users,
  WalletCards,
  Waves,
  XCircle,
} from 'lucide-react';
import { useWallet } from '../../hooks/useWallet';
import { fetchCreator, BADGE_LABEL } from '../../lib/reputation';
import {
  executeMetaLaunchPlan,
  getLaunchMint,
  getLaunchProviderReadiness,
  getSolanaExplorerUrl,
  META_LAUNCH_PROVIDERS,
  META_LAUNCH_STEPS,
  recheckMetaLaunchSignature,
  requestMetaLaunchPlan,
} from '../../lib/launchpads';

export const DEFAULT_META_LAUNCH_FORM = {
  providerId: 'feeless',
  name: '',
  symbol: '',
  imageUrl: '',
  supply: '1000000000',
  openingMarketCap: '35',
  curveType: 'linear',
  graduationTarget: '85',
  liquidityPair: 'SOL',
  swapFee: '1',
  creatorFeeShare: '40',
  referralShare: '10',
  holderRewardShare: '0',
  buybackBurnShare: '50',
  antiSniperTax: '50',
  antiSniperWindow: '6',
  devBuyAmount: '0',
  migrationVenue: 'raydium-cpmm',
  liquidityLock: 'permanent',
  holderAllocation: '0',
  airdropRecipients: '',
  airdropAmount: '0',
  lockedLaunchEnabled: true,
  lockDurationMinutes: '30',
};

const OPENING_MARKET_CAPS = [
  ['10', '$10k · Spark', 'Fast, accessible opening curve'],
  ['35', '$35k · Orbit', 'Balanced default for community launches'],
  ['100', '$100k · Nova', 'More room before graduation'],
  ['500', '$500k · Supernova', 'High-cap launch for established communities'],
];

const numeric = value => Number(value);
const rounded = value => Math.round(value * 10) / 10;

const LAUNCH_BOX_GUIDE = [
  ['Identity', 'What traders recognize', 'Give the coin a name, ticker, image, and whole-token supply.'],
  ['Curve', 'How price discovery starts', 'Choose the opening cap and curve shape, then set the graduation target.'],
  ['Pool', 'Where liquidity graduates', 'Select SOL or USDC, a Raydium pool type, and permanent liquidity lock.'],
  ['Routing', 'Where fees go', 'Declare the swap fee split. Creator, holders, and buyback must equal 100%.'],
  ['Protection', 'How the opening is guarded', 'Use a visible anti-sniper tax and timed window instead of hidden rules.'],
  ['Community', 'Who gets the distribution', 'Reserve holder supply and list airdrop recipients before signing.'],
];

export function validateMetaLaunch(form) {
  const errors = {};
  const feeShares = [
    numeric(form.creatorFeeShare),
    numeric(form.referralShare),
    numeric(form.holderRewardShare),
    numeric(form.buybackBurnShare),
  ];
  const feeShareTotal = feeShares.reduce((sum, value) => sum + (Number.isFinite(value) ? value : 0), 0);
  const recipients = (form.airdropRecipients || '').split(/[\n,]+/).map(value => value.trim()).filter(Boolean);

  if (!form.name.trim()) errors.name = 'Enter a coin name.';
  if (!/^[A-Za-z0-9]{2,12}$/.test(form.symbol.trim())) errors.symbol = 'Use 2–12 letters or numbers.';
  if (!/^https?:\/\/[^\s]+$/i.test(form.imageUrl?.trim() || '')) errors.imageUrl = 'Add a public HTTP(S) token image URL.';
  if (!Number.isInteger(numeric(form.supply)) || numeric(form.supply) <= 0) errors.supply = 'Supply must be a whole number greater than zero.';
  if (!OPENING_MARKET_CAPS.some(([value]) => value === String(form.openingMarketCap))) errors.openingMarketCap = 'Choose an opening market-cap preset.';
  if (!['linear', 'exponential'].includes(form.curveType)) errors.curveType = 'Choose a supported curve.';
  if (!Number.isFinite(numeric(form.graduationTarget)) || numeric(form.graduationTarget) <= 0) errors.graduationTarget = 'Set a graduation target greater than zero.';
  if (!form.liquidityPair) errors.liquidityPair = 'Choose a quote asset.';
  if (!Number.isFinite(numeric(form.swapFee)) || numeric(form.swapFee) < 0 || numeric(form.swapFee) > 10) errors.swapFee = 'Swap fee must be between 0% and 10%.';
  feeShares.forEach((value, index) => {
    const key = ['creatorFeeShare', 'referralShare', 'holderRewardShare', 'buybackBurnShare'][index];
    if (!Number.isFinite(value) || value < 0 || value > 100) errors[key] = 'Share must be between 0% and 100%.';
  });
  if (!errors.creatorFeeShare && !errors.referralShare && !errors.holderRewardShare && !errors.buybackBurnShare && rounded(feeShareTotal) !== 100) {
    errors.feeShares = `Fee routing must total 100%. Current total: ${rounded(feeShareTotal)}%.`;
  }
  if (form.lockedLaunchEnabled) {
    if (!Number.isFinite(numeric(form.lockDurationMinutes)) || numeric(form.lockDurationMinutes) < 1 || numeric(form.lockDurationMinutes) > 1440) errors.lockDurationMinutes = 'Lock duration must be between 1 and 1440 minutes.';
  }
  if (!Number.isFinite(numeric(form.antiSniperTax)) || numeric(form.antiSniperTax) < 0 || numeric(form.antiSniperTax) > 100) errors.antiSniperTax = 'Protection tax must be between 0% and 100%.';
  if (!Number.isFinite(numeric(form.antiSniperWindow)) || numeric(form.antiSniperWindow) < 0 || numeric(form.antiSniperWindow) > 60) errors.antiSniperWindow = 'Protection window must be between 0 and 60 seconds.';
  if (numeric(form.antiSniperTax) > 0 && numeric(form.antiSniperWindow) <= 0) errors.antiSniperWindow = 'Add a protection window when anti-sniper tax is enabled.';
  if (!Number.isFinite(numeric(form.devBuyAmount)) || numeric(form.devBuyAmount) < 0) errors.devBuyAmount = 'Dev buy cannot be negative.';
  if (!['raydium-cpmm', 'raydium-clmm'].includes(form.migrationVenue)) errors.migrationVenue = 'Choose a supported graduation venue.';
  if (form.liquidityLock !== 'permanent') errors.liquidityLock = 'FEELESS launches use permanent liquidity locks.';
  if (!Number.isFinite(numeric(form.holderAllocation)) || numeric(form.holderAllocation) < 0 || numeric(form.holderAllocation) > 100) errors.holderAllocation = 'Holder allocation must be between 0% and 100%.';
  if (!Number.isFinite(numeric(form.airdropAmount)) || numeric(form.airdropAmount) < 0 || numeric(form.airdropAmount) > 100) errors.airdropAmount = 'Airdrop allocation must be between 0% and 100%.';
  if (numeric(form.airdropAmount) > 0 && !recipients.length) errors.airdropRecipients = 'Add at least one recipient for the airdrop.';
  if (numeric(form.holderAllocation) + numeric(form.airdropAmount) > 100) errors.allocations = 'Holder and airdrop allocations cannot exceed 100%.';
  return errors;
}

function Field({ label, name, value, onChange, error, hint, ...props }) {
  return <label className="meta-launch-field">
    <span>{label}{hint && <small>{hint}</small>}</span>
    <input name={name} value={value} onChange={event => onChange(name, event.target.value)} {...props} />
    {error && <small className="meta-launch-error">{error}</small>}
  </label>;
}

function SelectField({ label, name, value, onChange, error, children, hint, ...props }) {
  return <label className="meta-launch-field">
    <span>{label}{hint && <small>{hint}</small>}</span>
    <select name={name} value={value} onChange={event => onChange(name, event.target.value)} {...props}>{children}</select>
    {error && <small className="meta-launch-error">{error}</small>}
  </label>;
}

function StatusRow({ icon: Icon, title, detail, ready = false }) {
  return <div className={`meta-launch-status ${ready ? 'ready' : ''}`}><Icon size={16} /><span><b>{title}</b><small>{detail}</small></span></div>;
}

export function ReceiptCopyButton({ value, label, testId }) {
  const [copyState, setCopyState] = useState('idle');
  const copy = async () => {
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard access is unavailable.');
      await navigator.clipboard.writeText(value);
      setCopyState('copied');
    } catch {
      setCopyState('failed');
    }
  };

  return <span className="meta-launch-copy-control">
    <button className="meta-launch-copy-button" data-testid={testId} type="button" aria-label={`Copy full ${label.toLowerCase()}`} onClick={copy}><Copy size={12} />{copyState === 'copied' ? 'Copied' : label}</button>
    {copyState === 'copied' && <small className="meta-launch-copy-feedback" role="status">Copied to clipboard.</small>}
    {copyState === 'failed' && <small className="meta-launch-copy-feedback failed" role="alert">Copy failed. Clipboard access is unavailable.</small>}
  </span>;
}

export function StepStatus({ step, status }) {
  const Icon = status?.state === 'confirmed' ? CheckCircle2
    : status?.state === 'failed' ? XCircle
      : status?.state === 'pending' ? LoaderCircle
        : Clock3;
  const explorerUrl = status?.state === 'confirmed' && status.signature
    ? status.explorerUrl || getSolanaExplorerUrl(status.signature)
    : null;
  return <div className={`meta-launch-step-status ${status?.state || 'queued'}`} data-testid={`meta-launch-step-${step.id}`}>
    <Icon size={15} className={status?.state === 'pending' ? 'meta-launch-spinner' : ''} />
    <span><b>{step.label}</b><small>{status?.state === 'confirmed' ? <span className="meta-launch-receipt-line">Confirmed · {status.signature?.slice(0, 10)}… {status.signature && <ReceiptCopyButton value={status.signature} label="Copy signature" testId={`meta-launch-step-copy-${step.id}`} />} {explorerUrl && <a className="meta-launch-explorer-link" data-testid={`meta-launch-step-explorer-${step.id}`} href={explorerUrl} target="_blank" rel="noreferrer">View on Solana Explorer</a>}</span> : status?.detail || (status?.state === 'pending' ? 'Awaiting network confirmation.' : 'Waiting to submit.')}</small></span>
  </div>;
}

function FeeSplitSummary({ form }) {
  const total = rounded(numeric(form.creatorFeeShare) + numeric(form.referralShare) + numeric(form.holderRewardShare) + numeric(form.buybackBurnShare));
  return <div className={`meta-launch-fee-meter ${total === 100 ? 'complete' : ''}`} data-testid="meta-launch-fee-meter">
    <div><span>Creator</span><b>{form.creatorFeeShare}%</b></div>
    <div><span>Referral</span><b>{form.referralShare}%</b></div>
    <div><span>Holders</span><b>{form.holderRewardShare}%</b></div>
    <div><span>Buyback & burn</span><b>{form.buybackBurnShare}%</b></div>
    <strong>{total}% routed</strong>
  </div>;
}

function LockedLaunchPreview({ enabled, minutes }) {
  const buyers = useMemo(() => Array.from({ length: 10 }, (_, i) => ({ id: i, buyMinute: i === 0 ? 0 : rounded(i * (Number(minutes || 30) / 14)) })), [minutes]);
  if (!enabled) return <p className="provider-note">Locked Launch is off — buys settle immediately, same as a standard bonding-curve launch. Turn it on to make early sniping structurally unprofitable.</p>;
  const total = Number(minutes || 30);
  return <div className="lock-launch-preview" data-testid="lock-launch-preview">
    <div className="lock-launch-track">{buyers.map(b => <div key={b.id} className="lock-launch-buy" style={{ left: `${(b.buyMinute / total) * 88}%` }} title={`Buy at t+${b.buyMinute}m → unlocks at t+${total}m`}><span className="lock-launch-dot" /><small>t+{b.buyMinute}m</small></div>)}<div className="lock-launch-unlock-line" style={{ left: '92%' }}><span>ALL UNLOCK</span><small>t+{total}m</small></div></div>
    <p className="provider-note">Every buy is escrowed for {total} minutes from the moment it lands, then released in the order it bought — <b>earliest buyers first, snipers who bought in the first seconds unlock last</b> if they bought after the launch already ran up. Nobody can sell before their own lock clears, so there's no window where an early sniper can dump into buyers who arrived seconds later.</p>
  </div>;
}

function LaunchEligibilityPanel({ wallet, chain }) {
  const [state, setState] = useState({ loading: false, result: null, error: '' });
  useEffect(() => {
    if (!wallet?.address || wallet.chain !== chain) { setState({ loading: false, result: null, error: '' }); return; }
    let alive = true;
    setState({ loading: true, result: null, error: '' });
    fetchCreator(chain, wallet.address).then(result => { if (alive) setState({ loading: false, result, error: '' }); })
      .catch(err => { if (alive) setState({ loading: false, result: null, error: err.message }); });
    return () => { alive = false; };
  }, [wallet?.address, wallet?.chain, chain]);

  if (!wallet?.address) return <div className="launch-eligibility unknown"><ShieldQuestion size={16} /><span><b>Connect a wallet to check launch eligibility.</b><small>FEELESS checks your own reputation graph before letting a launch through.</small></span></div>;
  if (state.loading) return <div className="launch-eligibility unknown"><LoaderCircle size={16} className="meta-launch-spinner" /><span><b>Checking your reputation graph…</b></span></div>;
  if (state.error || !state.result) return <div className="launch-eligibility clear"><ShieldCheck size={16} /><span><b>No prior launches on record — clean slate.</b><small>First-time creators can launch freely. Your history starts compounding from this one.</small></span></div>;
  const { scoring } = state.result;
  if (scoring.ruggedCount > 0) return <div className="launch-eligibility blocked"><ShieldAlert size={16} /><span><b>Launch blocked — {scoring.ruggedCount} confirmed liquidity collapse{scoring.ruggedCount > 1 ? 's' : ''} on this wallet.</b><small>This is the reputation graph FEELESS itself keeps. Launch from a different, clean wallet, or wait — flags don't expire.</small></span></div>;
  return <div className="launch-eligibility clear"><ShieldCheck size={16} /><span><b>Eligible — {BADGE_LABEL[scoring.badge]}, score {scoring.score}/100.</b><small>{scoring.tokenCount} prior token{scoring.tokenCount === 1 ? '' : 's'} tracked, 0 flagged.</small></span></div>;
}

export default function MetaLaunchSetup({ initialValues }) {
  const { wallet, provider, connect } = useWallet();
  const [form, setForm] = useState({ ...DEFAULT_META_LAUNCH_FORM, ...initialValues });
  const [errors, setErrors] = useState({});
  const [step, setStep] = useState('setup');
  const [deployment, setDeployment] = useState({ state: 'idle', statuses: {} });
  const [deploying, setDeploying] = useState(false);
  const [checkingSignature, setCheckingSignature] = useState(false);
  const readiness = getLaunchProviderReadiness(form.providerId);
  const selectedProvider = META_LAUNCH_PROVIDERS.find(providerOption => providerOption.id === form.providerId) || META_LAUNCH_PROVIDERS[0];
  const recipients = useMemo(() => form.airdropRecipients.split(/[\n,]+/).map(value => value.trim()).filter(Boolean), [form.airdropRecipients]);
  const pendingStep = useMemo(() => META_LAUNCH_STEPS
    .map(stepItem => ({ step: stepItem, status: deployment.statuses[stepItem.id] }))
    .find(({ status }) => status?.state === 'pending' && status.signature), [deployment.statuses]);
  const update = (name, value) => setForm(current => ({ ...current, [name]: value }));
  const review = event => {
    event.preventDefault();
    const nextErrors = validateMetaLaunch(form);
    setErrors(nextErrors);
    if (!Object.keys(nextErrors).length) setStep('review');
  };
  const unavailableReason = !readiness.providerReady
    ? 'An approved launch provider is not configured.'
    : !readiness.rpcReady
      ? 'A Solana RPC endpoint is not configured.'
      : wallet?.chain && wallet.chain !== 'solana'
        ? 'A Solana wallet is required for this launch.'
        : 'Wallet approval is requested after this review.';
  const deploymentReady = readiness.ready && !deploying && deployment.state !== 'confirmed'
    && (deployment.state !== 'pending' || deployment.resumeReady);
  const deploy = async () => {
    if (!deploymentReady) return;
    setDeploying(true);
    const isResuming = Boolean(deployment.resumeReady && deployment.plan && deployment.results?.length);
    if (!isResuming) setDeployment({ state: 'pending', statuses: {} });
    try {
      let activeWallet = wallet;
      let activeProvider = provider;
      if (!activeWallet || activeWallet.chain !== 'solana') {
        const connected = await connect?.('solana');
        activeWallet = connected?.wallet;
        activeProvider = connected?.provider;
      }
      if (!activeWallet || !activeProvider) throw new Error('Connect Phantom to approve this launch.');
      if (activeWallet.chain === 'solana') {
        try {
          const reputation = await fetchCreator('solana', activeWallet.address);
          if (reputation?.scoring?.ruggedCount > 0) throw new Error(`Launch blocked: this wallet has ${reputation.scoring.ruggedCount} confirmed liquidity collapse${reputation.scoring.ruggedCount > 1 ? 's' : ''} on FEELESS's reputation graph. Use a different wallet.`);
        } catch (reputationError) {
          if (reputationError.message?.startsWith('Launch blocked')) throw reputationError;
          // No prior record (404) or the reputation service is unreachable — never block a launch on infra flakiness, only on a confirmed flag.
        }
      }
       const plan = deployment.plan || await requestMetaLaunchPlan(form, activeWallet, form.providerId);
      const result = await executeMetaLaunchPlan(plan, {
        provider: activeProvider,
        wallet: activeWallet,
        previousResults: isResuming ? deployment.results : [],
        onStep: (id, status) => setDeployment(current => ({ ...current, statuses: { ...current.statuses, [id]: status } })),
      });
      setDeployment(current => ({
        ...current,
        state: result.state,
        detail: result.detail,
        mint: result.mint || getLaunchMint(plan),
        plan,
        results: result.results,
        resumeReady: false,
      }));
    } catch (error) {
      setDeployment({ state: 'failed', statuses: {}, detail: error?.code === 4001 ? 'Wallet approval declined.' : error?.message || 'Deployment failed.' });
    } finally {
      setDeploying(false);
    }
  };
  const recheckPendingSignature = async () => {
    if (!pendingStep || checkingSignature) return;
    setCheckingSignature(true);
    try {
      const result = await recheckMetaLaunchSignature(pendingStep.status.signature, { label: pendingStep.step.label });
      setDeployment(current => {
        const statuses = { ...current.statuses, [pendingStep.step.id]: { ...result, label: pendingStep.step.label } };
        const results = (current.results || []).map(item => item.id === pendingStep.step.id ? { ...item, ...result, label: pendingStep.step.label } : item);
        const allConfirmed = META_LAUNCH_STEPS.every(stepItem => statuses[stepItem.id]?.state === 'confirmed');
        return {
          ...current,
          statuses,
          results,
          state: result.state === 'failed' ? 'failed' : allConfirmed ? 'confirmed' : 'pending',
          detail: result.state === 'confirmed'
            ? allConfirmed ? 'All launch phases are confirmed.' : `${pendingStep.step.label} is confirmed. Continue with the remaining launch phases.`
            : result.detail,
          mint: allConfirmed ? current.mint || getLaunchMint(current.plan) : current.mint,
          resumeReady: result.state === 'confirmed' && !allConfirmed,
        };
      });
    } catch (error) {
      setDeployment(current => ({ ...current, detail: error?.message || 'Could not check transaction confirmation.' }));
    } finally {
      setCheckingSignature(false);
    }
  };

  return <div className="meta-launch-page" data-testid="meta-launch-page">
    <div className="meta-launch-topline"><a href="/terminal/launch" className="meta-launch-back"><ArrowLeft size={14} />Launchpads</a><span className="eyebrow"><span className="live-dot" /> FEELESS META LAUNCH</span></div>
    <header className="meta-launch-header"><div><span className="eyebrow">CURVE → GRADUATION → COMMUNITY</span><h1>Launch with a living economy.</h1><p>Build the curve, define where every swap fee goes, protect the opening seconds, then graduate into permanent liquidity. This is a launch plan until an approved provider is connected.</p></div><div className="meta-launch-step"><span className={step === 'setup' ? 'active' : ''}>01 Mechanics</span><span className={step === 'review' ? 'active' : ''}>02 Review</span></div></header>
      <div className="meta-launch-mechanics-banner" data-testid="meta-launch-mechanics-banner"><div><span className="eyebrow"><Waves size={13} /> RAYDIUM-STYLE CURVE / INFINITY-STYLE ROUTING</span><h2>Every phase has a job.</h2><p>Buyers start on a deterministic bonding curve. When the target is reached, liquidity graduates to a Raydium pool. Fees can reward the creator, holders, or an automatic buyback-and-burn route.</p></div><div className="meta-launch-mechanics-flow"><span>CURVE</span><i>→</i><span>GRADUATE</span><i>→</i><span>POOL</span></div></div>
      <section className="meta-launch-box-guide" data-testid="meta-launch-box-guide"><div className="meta-launch-box-guide-heading"><div><span className="eyebrow">READ THE LAUNCH PLAN</span><h2>Know what each box controls.</h2></div><small>Nothing is hidden behind a wallet prompt.</small></div><div className="meta-launch-box-guide-grid">{LAUNCH_BOX_GUIDE.map(([title, label, detail], index) => <article key={title}><span>0{index + 1}</span><div><b>{title}</b><strong>{label}</strong><p>{detail}</p></div></article>)}</div></section>
     {step === 'setup' ? <form className="meta-launch-grid" onSubmit={review} noValidate>
       <section className="meta-launch-section meta-launch-provider-section"><div className="meta-launch-section-heading"><Rocket size={17} /><div><h2>Choose your launch rail</h2><p>FEELESS coordinates the launch review. A provider must be explicitly approved before it can prepare transactions.</p></div></div><div className="meta-launch-provider-picker" role="radiogroup" aria-label="Launch provider">{META_LAUNCH_PROVIDERS.map(providerOption => { const providerReadiness = getLaunchProviderReadiness(providerOption.id); return <button type="button" role="radio" aria-checked={form.providerId === providerOption.id} key={providerOption.id} className={`meta-launch-provider-option ${form.providerId === providerOption.id ? 'selected' : ''}`} data-testid={`meta-launch-provider-${providerOption.id}`} onClick={() => { update('providerId', providerOption.id); setDeployment({ state: 'idle', statuses: {} }); }}><span className="meta-launch-provider-option-top"><b>{providerOption.label}</b><span className={`provider-state ${providerReadiness.ready ? 'ready' : ''}`}>{providerReadiness.ready ? 'READY' : 'NOT CONFIGURED'}</span></span><small>{providerOption.note}</small></button>; })}</div><p className="meta-launch-provider-context"><span className="live-dot" />Selected: <b>{selectedProvider.label}</b> · {readiness.provider?.description || 'Provider status unavailable.'}</p></section>
        <section className="meta-launch-section"><div className="meta-launch-section-heading"><Rocket size={17} /><div><h2>Token identity</h2><p>Name, ticker, image, and whole-token supply. The public image is included in the launch metadata.</p></div></div><div className="meta-launch-fields two"><Field label="Coin name" name="name" placeholder="Meta Coin" value={form.name} onChange={update} error={errors.name} /><Field label="Symbol" name="symbol" placeholder="META" value={form.symbol} onChange={update} error={errors.symbol} autoCapitalize="characters" /><Field label="Total supply" name="supply" type="number" min="1" step="1" value={form.supply} onChange={update} error={errors.supply} hint="Whole tokens" /></div><div className="meta-launch-image-row"><Field label="Token image URL" name="imageUrl" type="url" placeholder="https://example.com/token.png" value={form.imageUrl} onChange={update} error={errors.imageUrl} hint="Public HTTPS image" /><div className="meta-launch-image-preview" data-testid="meta-launch-image-preview">{form.imageUrl ? <img src={form.imageUrl} alt={`${form.name || 'Token'} preview`} onError={event => { event.currentTarget.style.display = 'none'; }} /> : <><ImageIcon size={20} /><span>Image preview</span></>}</div></div></section>
      <section className="meta-launch-section"><div className="meta-launch-section-heading"><Gauge size={17} /><div><h2>Bonding curve</h2><p>Choose the opening market cap and the point where the curve graduates to a pool.</p></div></div><div className="meta-launch-fields two"><SelectField label="Opening market cap" name="openingMarketCap" value={form.openingMarketCap} onChange={update} error={errors.openingMarketCap}>{OPENING_MARKET_CAPS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</SelectField><SelectField label="Curve shape" name="curveType" value={form.curveType} onChange={update} error={errors.curveType}><option value="linear">Linear · predictable steps</option><option value="exponential">Exponential · faster price discovery</option></SelectField><Field label="Graduation target" name="graduationTarget" type="number" min="1" step="any" value={form.graduationTarget} onChange={update} error={errors.graduationTarget} hint="SOL / quote asset" /></div></section>
      <section className="meta-launch-section"><div className="meta-launch-section-heading"><Coins size={17} /><div><h2>Liquidity graduation</h2><p>Set the quote asset, destination pool, and a permanent lock for graduated liquidity.</p></div></div><div className="meta-launch-fields two"><SelectField label="Quote asset" name="liquidityPair" value={form.liquidityPair} onChange={update} error={errors.liquidityPair}><option value="SOL">SOL</option><option value="USDC">USDC</option></SelectField><SelectField label="Graduation venue" name="migrationVenue" value={form.migrationVenue} onChange={update} error={errors.migrationVenue}><option value="raydium-cpmm">Raydium CPMM</option><option value="raydium-clmm">Raydium CLMM</option></SelectField><SelectField label="Liquidity lock" name="liquidityLock" value={form.liquidityLock} onChange={update} error={errors.liquidityLock}><option value="permanent">Permanent · unruggable</option></SelectField></div></section>
      <section className="meta-launch-section"><div className="meta-launch-section-heading"><Flame size={17} /><div><h2>Fee routing</h2><p>One swap fee. Four visible destinations. The split must always equal 100%.</p></div></div><div className="meta-launch-fields two"><Field label="Swap fee (%)" name="swapFee" type="number" min="0" max="10" step="0.1" value={form.swapFee} onChange={update} error={errors.swapFee} hint="Applied on buys and sells" /><Field label="Creator share (%)" name="creatorFeeShare" type="number" min="0" max="100" step="0.1" value={form.creatorFeeShare} onChange={update} error={errors.creatorFeeShare} /><Field label="Referral share (%)" name="referralShare" type="number" min="0" max="100" step="0.1" value={form.referralShare} onChange={update} error={errors.referralShare} hint="Paid to whoever referred the buyer" /><Field label="Holder rewards share (%)" name="holderRewardShare" type="number" min="0" max="100" step="0.1" value={form.holderRewardShare} onChange={update} error={errors.holderRewardShare} /><Field label="Buyback & burn share (%)" name="buybackBurnShare" type="number" min="0" max="100" step="0.1" value={form.buybackBurnShare} onChange={update} error={errors.buybackBurnShare} /></div><FeeSplitSummary form={form} />{errors.feeShares && <p className="meta-launch-error" role="alert">{errors.feeShares}</p>}</section>
      <section className="meta-launch-section"><div className="meta-launch-section-heading"><Timer size={17} /><div><h2>Opening protection</h2><p>Give the first seconds a transparent anti-sniper rule. It routes to holders, not a hidden wallet.</p></div></div><div className="meta-launch-fields two"><Field label="Opening buy tax (%)" name="antiSniperTax" type="number" min="0" max="100" step="1" value={form.antiSniperTax} onChange={update} error={errors.antiSniperTax} hint="Falls away after the window" /><Field label="Protection window (seconds)" name="antiSniperWindow" type="number" min="0" max="60" step="1" value={form.antiSniperWindow} onChange={update} error={errors.antiSniperWindow} /><Field label="Optional dev buy" name="devBuyAmount" type="number" min="0" step="any" value={form.devBuyAmount} onChange={update} error={errors.devBuyAmount} hint="SOL / quote asset" /></div></section>
      <section className="meta-launch-section"><div className="meta-launch-section-heading"><LockKeyhole size={17} /><div><h2>Locked Launch <span className="state-tag amber">ANTI-RUG</span></h2><p>Every buy sits in escrow before it can be resold — chronological unlock means snipers can't dump into buyers who arrived seconds after them.</p></div></div><label className="meta-launch-toggle"><input type="checkbox" checked={form.lockedLaunchEnabled} onChange={event => update('lockedLaunchEnabled', event.target.checked)} /><span>Enable Locked Launch for this token</span></label>{form.lockedLaunchEnabled && <div className="meta-launch-fields two"><Field label="Lock duration (minutes)" name="lockDurationMinutes" type="number" min="1" max="1440" step="1" value={form.lockDurationMinutes} onChange={update} error={errors.lockDurationMinutes} hint="Every buy unlocks this long after it lands" /></div>}<LockedLaunchPreview enabled={form.lockedLaunchEnabled} minutes={form.lockDurationMinutes} /></section>
      <section className="meta-launch-section"><div className="meta-launch-section-heading"><Users size={17} /><div><h2>Community distribution</h2><p>Reserve supply for holders and list airdrop recipients before review.</p></div></div><div className="meta-launch-fields two"><Field label="Holder allocation (%)" name="holderAllocation" type="number" min="0" max="100" step="0.1" value={form.holderAllocation} onChange={update} error={errors.holderAllocation} /><Field label="Airdrop allocation (%)" name="airdropAmount" type="number" min="0" max="100" step="0.1" value={form.airdropAmount} onChange={update} error={errors.airdropAmount} /></div><label className="meta-launch-field"><span>Airdrop recipients<small>One wallet address per line</small></span><textarea name="airdropRecipients" rows="4" placeholder="Wallet address 1&#10;Wallet address 2" value={form.airdropRecipients} onChange={event => update('airdropRecipients', event.target.value)} />{errors.airdropRecipients && <small className="meta-launch-error">{errors.airdropRecipients}</small>}</label>{errors.allocations && <p className="meta-launch-error" role="alert">{errors.allocations}</p>}</section>
      <aside className="meta-launch-sidebar"><div className="meta-launch-readiness"><span className="eyebrow">LAUNCH READINESS</span><LaunchEligibilityPanel wallet={wallet} chain="solana" /><StatusRow icon={wallet ? CheckCircle2 : Clock3} title={wallet ? 'Wallet connected' : 'Wallet approval after review'} detail={wallet ? `${wallet.name} · ${wallet.address.slice(0, 6)}…` : 'No wallet request is made while editing mechanics.'} ready={Boolean(wallet)} /><StatusRow icon={readiness.providerReady ? CheckCircle2 : LockKeyhole} title={readiness.providerReady ? readiness.providerName : 'Provider unavailable'} detail={readiness.providerReady ? `${readiness.network} · approved provider` : 'Approved provider URL and approval status are required.'} ready={readiness.providerReady} /><StatusRow icon={readiness.rpcReady ? CheckCircle2 : LockKeyhole} title={readiness.rpcReady ? 'Solana RPC configured' : 'Solana RPC unavailable'} detail={readiness.rpcReady ? `${readiness.network} · ${readiness.rpcHost}` : 'No on-chain confirmation or submission will be attempted.'} ready={readiness.rpcReady} /><p className="meta-launch-safety">FEELESS never stores private keys. The provider prepares unsigned phases; your wallet signs them only after review.</p></div><div className="meta-launch-sidebar-note"><ShieldCheck size={15} /><span><b>Permanent liquidity. Visible routing.</b><small>Creator rewards, holder rewards, and buyback-and-burn shares are declared before launch.</small></span></div><button className="btn-primary meta-launch-review" data-testid="meta-launch-review" type="submit">Review launch mechanics<ArrowRight size={16} /></button></aside>
    </form> : <section className="meta-launch-review-page" data-testid="meta-launch-review-page">
       <div className="meta-launch-review-heading"><div className="meta-launch-review-identity">{form.imageUrl && <img src={form.imageUrl} alt="" onError={event => { event.currentTarget.style.display = 'none'; }} />}<div><span className="eyebrow">CHECK BEFORE SIGNING</span><h2>{form.name} <span>${form.symbol}</span></h2><p>Your launch mechanics and token identity are valid. Review the curve, routing, protection, and community allocations before any provider request.</p></div></div><button className="btn-outline" data-testid="meta-launch-edit" onClick={() => setStep('setup')}><ArrowLeft size={15} />Edit mechanics</button></div>
       <div className="meta-launch-review-cards"><div><span>Launch provider</span><b>{selectedProvider.label}</b><small>{readiness.ready ? 'Approved preparation rail' : 'Not configured for execution'}</small></div><div><span>Opening market cap</span><b>${form.openingMarketCap}k</b><small>{form.curveType} curve</small></div><div><span>Graduation target</span><b>{form.graduationTarget} {form.liquidityPair}</b><small>{form.migrationVenue === 'raydium-cpmm' ? 'Raydium CPMM' : 'Raydium CLMM'} · permanent lock</small></div><div><span>Fee routing</span><b>{form.swapFee}% swap fee</b><small>{form.creatorFeeShare}% creator · {form.holderRewardShare}% holders · {form.buybackBurnShare}% buyback & burn</small></div><div><span>Opening protection</span><b>{form.antiSniperTax}% → 0%</b><small>After {form.antiSniperWindow}s · optional dev buy {form.devBuyAmount} {form.liquidityPair}</small></div></div>
      <div className="meta-launch-summary"><dl><div><dt>Total supply</dt><dd>{form.supply}</dd></div><div><dt>Quote asset</dt><dd>{form.liquidityPair}</dd></div><div><dt>Holder allocation</dt><dd>{form.holderAllocation}%</dd></div><div><dt>Airdrop</dt><dd>{form.airdropAmount}% · {recipients.length} recipients</dd></div></dl></div>
      <div className={`meta-launch-review-actions ${deployment.state === 'failed' ? 'has-failure' : ''}`}><div className={`meta-launch-deployment-note ${deployment.state === 'failed' ? 'failed' : deployment.state === 'confirmed' ? 'confirmed' : ''}`} data-testid="meta-launch-provider-warning">{deployment.state === 'failed' ? <AlertTriangle size={17} /> : deployment.state === 'confirmed' ? <CheckCircle2 size={17} /> : <ShieldCheck size={17} />}<span><b>{deployment.state === 'confirmed' ? 'Launch confirmed.' : deployment.state === 'failed' ? 'Launch could not be completed.' : deployment.resumeReady ? 'Continue remaining launch phases.' : deployment.state === 'pending' ? 'Launch confirmation is pending.' : readiness.ready ? 'Ready for wallet approval.' : 'Deployment is not available yet.'}</b><small>{deployment.detail || (readiness.ready ? 'Your wallet will review each phase after you continue.' : unavailableReason)}</small></span></div>{pendingStep && <button className="btn-outline" data-testid="meta-launch-recheck" type="button" disabled={checkingSignature} onClick={recheckPendingSignature}>{checkingSignature ? <><LoaderCircle size={16} className="meta-launch-spinner" />Checking…</> : 'Check pending signature'}</button>}<button className="btn-primary" data-testid="meta-launch-deploy" type="button" disabled={!deploymentReady} title={deployment.resumeReady ? 'Continue the remaining launch phases' : readiness.ready ? 'Request wallet approval and deploy' : unavailableReason} onClick={deploy}>{deploying ? <><LoaderCircle size={16} className="meta-launch-spinner" />Deploying…</> : deployment.state === 'confirmed' ? 'Launch confirmed' : deployment.resumeReady ? 'Continue launch' : 'Approve & deploy'}</button></div>
       {deployment.state === 'confirmed' && deployment.mint && <div className="meta-launch-mint-receipt" data-testid="meta-launch-mint-receipt"><span><b>Created mint</b><small>{deployment.mint}</small></span><span className="meta-launch-mint-receipt-actions"><ReceiptCopyButton value={deployment.mint} label="Copy mint" testId="meta-launch-mint-copy" /><a className="meta-launch-explorer-link" data-testid="meta-launch-mint-explorer" href={getSolanaExplorerUrl(deployment.mint, 'address')} target="_blank" rel="noreferrer">View mint on Solana Explorer <ArrowRight size={13} /></a></span></div>}
      {(deployment.state !== 'idle' || deploying) && <div className="meta-launch-deployment-status" data-testid="meta-launch-deployment-status"><h3>Deployment phases</h3>{META_LAUNCH_STEPS.map(stepItem => <StepStatus key={stepItem.id} step={stepItem} status={deployment.statuses[stepItem.id]} />)}</div>}
    </section>}
  </div>;
}