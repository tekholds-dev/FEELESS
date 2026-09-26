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
  Globe,
  Send,
  MessageCircle,
  Sparkles,
  Link2,
  Flame as EmberIcon,
} from 'lucide-react';
import { useWallet } from '../../hooks/useWallet';
import { apiUrl } from '../../lib/api';
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
  launchStyle: 'feeless',
  description: '',
  website: '',
  twitter: '',
  telegram: '',
  discord: '',
  tradeBurn: '0',
  maxWalletPct: '0',
  devVestingDays: '0',
  blockKnownSnipers: true,
};

// Launch styles: one click sets every mechanic to a known, coherent configuration.
export const LAUNCH_STYLES = [
  { id: 'pump', name: 'Pump style', tag: 'CLASSIC', blurb: 'The pump.fun playbook: low open, fair curve, no taxes, graduate at 85 SOL.',
    values: { openingMarketCap: '10', curveType: 'exponential', graduationTarget: '85', swapFee: '1', creatorFeeShare: '50', referralShare: '0', holderRewardShare: '0', buybackBurnShare: '50', antiSniperTax: '0', antiSniperWindow: '0', tradeBurn: '0', maxWalletPct: '0', lockedLaunchEnabled: false, devVestingDays: '0' } },
  { id: 'ember', name: 'Ember', tag: 'DEFLATIONARY', blurb: 'Every trade burns supply and most fees buy back and burn — the token gets scarcer with volume.',
    values: { openingMarketCap: '35', curveType: 'linear', graduationTarget: '85', swapFee: '2', creatorFeeShare: '15', referralShare: '5', holderRewardShare: '0', buybackBurnShare: '80', antiSniperTax: '30', antiSniperWindow: '6', tradeBurn: '0.5', maxWalletPct: '0', lockedLaunchEnabled: false, devVestingDays: '7' } },
  { id: 'locked', name: 'Locked Launch', tag: 'ANTI-SNIPE', blurb: 'Buys escrow and unlock in order, max-wallet cap at open — snipers can\'t dump on the crowd.',
    values: { openingMarketCap: '35', curveType: 'linear', graduationTarget: '85', swapFee: '1', creatorFeeShare: '40', referralShare: '10', holderRewardShare: '0', buybackBurnShare: '50', antiSniperTax: '50', antiSniperWindow: '10', tradeBurn: '0', maxWalletPct: '2', lockedLaunchEnabled: true, lockDurationMinutes: '30', devVestingDays: '14' } },
  { id: 'rewards', name: 'Holder rewards', tag: 'REFLECTION', blurb: 'Most of every swap fee streams back to holders, pro-rata.',
    values: { openingMarketCap: '35', curveType: 'linear', graduationTarget: '85', swapFee: '2', creatorFeeShare: '20', referralShare: '5', holderRewardShare: '65', buybackBurnShare: '10', antiSniperTax: '30', antiSniperWindow: '6', tradeBurn: '0', maxWalletPct: '1', lockedLaunchEnabled: false, devVestingDays: '7' } },
  { id: 'fair', name: 'Fair launch', tag: 'NO DEV EDGE', blurb: 'No dev buy, 1% max wallet at open, zero creator fee — pure community.',
    values: { openingMarketCap: '10', curveType: 'linear', graduationTarget: '85', swapFee: '1', creatorFeeShare: '0', referralShare: '0', holderRewardShare: '50', buybackBurnShare: '50', antiSniperTax: '50', antiSniperWindow: '10', tradeBurn: '0', maxWalletPct: '1', devBuyAmount: '0', lockedLaunchEnabled: true, lockDurationMinutes: '15', devVestingDays: '0' } },
  { id: 'airdrop', name: 'Community drop', tag: 'AIRDROP', blurb: 'Reserve supply for an existing community and drop it at launch.',
    values: { openingMarketCap: '100', curveType: 'linear', graduationTarget: '85', swapFee: '1', creatorFeeShare: '30', referralShare: '10', holderRewardShare: '30', buybackBurnShare: '30', antiSniperTax: '30', antiSniperWindow: '6', tradeBurn: '0', maxWalletPct: '0', holderAllocation: '5', airdropAmount: '5', lockedLaunchEnabled: false, devVestingDays: '30' } },
];

const OPENING_MARKET_CAPS = [
  ['10', '$10k · Spark', 'Fast, accessible opening curve'],
  ['35', '$35k · Orbit', 'Balanced default for community launches'],
  ['100', '$100k · Nova', 'More room before graduation'],
  ['500', '$500k · Supernova', 'High-cap launch for established communities'],
];


const LAUNCH_STEPS = [[1, 'Identity', 'Name, image, socials'], [2, 'Economics', 'Supply, curve, pairing, fees'], [3, 'Protection', 'Anti-snipe, locks, launch rail']];
const STEP_ONE_KEYS = ['name', 'symbol', 'imageUrl', 'description', 'website', 'twitter', 'telegram', 'discord'];
const STEP_TWO_KEYS = ['supply', 'openingMarketCap', 'curveType', 'graduationTarget', 'liquidityPair', 'migrationVenue', 'liquidityLock', 'swapFee', 'creatorFeeShare', 'referralShare', 'holderRewardShare', 'buybackBurnShare', 'feeShares', 'tradeBurn'];

export const QUOTE_ASSETS = [
  ['SOL', 'SOL', 'Native Solana — deepest liquidity'], ['USDC', 'USDC', 'Circle dollar stablecoin'], ['USDT', 'USDT', 'Tether dollar stablecoin'],
  ['USD1', 'USD1', 'World Liberty dollar stablecoin'], ['PYUSD', 'PYUSD', 'PayPal dollar stablecoin'], ['JITOSOL', 'JitoSOL', 'Liquid-staked SOL (Jito)'],
  ['MSOL', 'mSOL', 'Liquid-staked SOL (Marinade)'], ['JUPSOL', 'JupSOL', 'Liquid-staked SOL (Jupiter)'], ['JUP', 'JUP', 'Jupiter'],
  ['BONK', 'BONK', 'Community meme pair'], ['WIF', 'WIF', 'Community meme pair'], ['RAY', 'RAY', 'Raydium'], ['FEE', '$FEE', 'FEELESS ecosystem pair'],
];
export const GRADUATION_VENUES = [
  ['raydium-cpmm', 'Raydium CPMM', 'Standard constant-product pool'], ['raydium-clmm', 'Raydium CLMM', 'Concentrated liquidity'],
  ['pumpswap', 'PumpSwap', 'pump.fun native AMM'], ['meteora-damm-v2', 'Meteora DAMM v2', 'Dynamic fees, anti-snipe'],
  ['meteora-dlmm', 'Meteora DLMM', 'Bin-based dynamic liquidity'], ['orca-whirlpool', 'Orca Whirlpool', 'Concentrated liquidity'],
];
const SUPPLY_PRESETS = [['1000000', '1M', 'Scarce'], ['10000000', '10M', 'Premium'], ['100000000', '100M', 'Balanced'], ['1000000000', '1B', 'pump.fun standard'], ['10000000000', '10B', 'Meme scale'], ['100000000000', '100B', 'Micro-price']];

function SupplyPicker({ value, onChange, error }) {
  const preset = SUPPLY_PRESETS.some(([v]) => v === String(value));
  const [custom, setCustom] = useState(!preset);
  return <div className="supply-picker"><span className="supply-picker-label">Total supply<small>Fixed at mint — can never be increased</small></span>
    <div className="supply-options" role="radiogroup" aria-label="Total supply">{SUPPLY_PRESETS.map(([v, label, note]) => <button type="button" role="radio" aria-checked={!custom && String(value) === v} key={v} className={!custom && String(value) === v ? 'selected' : ''} onClick={() => { setCustom(false); onChange(v); }}><b>{label}</b><small>{note}</small></button>)}
      <button type="button" role="radio" aria-checked={custom} className={custom ? 'selected' : ''} onClick={() => setCustom(true)}><b>Custom</b><small>Any whole number</small></button></div>
    {custom && <label className="meta-launch-field"><span>Custom supply<small>Whole tokens</small></span><input name="supply" type="number" min="1" step="1" value={value} onChange={e => onChange(e.target.value)} /></label>}
    {error && <small className="meta-launch-error">{error}</small>}</div>;
}

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
  if (!QUOTE_ASSETS.some(([v]) => v === form.liquidityPair)) errors.liquidityPair = 'Choose a supported quote asset.';
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
  if (!GRADUATION_VENUES.some(([v]) => v === form.migrationVenue)) errors.migrationVenue = 'Choose a supported graduation venue.';
  if (form.liquidityLock !== 'permanent') errors.liquidityLock = 'FEELESS launches use permanent liquidity locks.';
  if (!Number.isFinite(numeric(form.holderAllocation)) || numeric(form.holderAllocation) < 0 || numeric(form.holderAllocation) > 100) errors.holderAllocation = 'Holder allocation must be between 0% and 100%.';
  if (!Number.isFinite(numeric(form.airdropAmount)) || numeric(form.airdropAmount) < 0 || numeric(form.airdropAmount) > 100) errors.airdropAmount = 'Airdrop allocation must be between 0% and 100%.';
  if (numeric(form.airdropAmount) > 0 && !recipients.length) errors.airdropRecipients = 'Add at least one recipient for the airdrop.';
  const url = v => !v?.trim() || /^https:\/\/[^\s.]+\.[^\s]+$/i.test(v.trim());
  if (!url(form.website)) errors.website = 'Use a full https:// link.';
  if (form.twitter?.trim() && !/^(https:\/\/(x|twitter)\.com\/[A-Za-z0-9_]{1,15}\/?|@?[A-Za-z0-9_]{1,15})$/i.test(form.twitter.trim())) errors.twitter = 'Use @handle or an x.com link.';
  if (form.telegram?.trim() && !/^(https:\/\/t\.me\/[A-Za-z0-9_+]{3,}\/?|@?[A-Za-z0-9_]{5,32})$/i.test(form.telegram.trim())) errors.telegram = 'Use @group or a t.me link.';
  if (form.discord?.trim() && !/^https:\/\/(discord\.gg|discord\.com\/invite)\/[A-Za-z0-9-]+\/?$/i.test(form.discord.trim())) errors.discord = 'Use a discord.gg invite link.';
  if ((form.description || '').length > 280) errors.description = 'Keep the description under 280 characters.';
  if (!Number.isFinite(numeric(form.tradeBurn ?? 0)) || numeric(form.tradeBurn ?? 0) < 0 || numeric(form.tradeBurn ?? 0) > 5) errors.tradeBurn = 'Per-trade burn must be between 0% and 5%.';
  if (!Number.isFinite(numeric(form.maxWalletPct ?? 0)) || numeric(form.maxWalletPct ?? 0) < 0 || numeric(form.maxWalletPct ?? 0) > 100) errors.maxWalletPct = 'Max wallet must be between 0% (off) and 100%.';
  if (!Number.isFinite(numeric(form.devVestingDays ?? 0)) || numeric(form.devVestingDays ?? 0) < 0 || numeric(form.devVestingDays ?? 0) > 365) errors.devVestingDays = 'Vesting must be 0–365 days.';
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

function BlocklistToggle({ enabled, onChange }) {
  const [info, setInfo] = useState(null);
  useEffect(() => {
    if (typeof fetch !== 'function') return;
    fetch(apiUrl('/api/reputation/blocklist?limit=1')).then(r => (r.ok ? r.json() : null)).then(setInfo).catch(() => {});
  }, []);
  return <label className="meta-launch-toggle blocklist-toggle"><input type="checkbox" checked={enabled} onChange={e => onChange(e.target.checked)} /><span><b>Block FEELESS blocklist wallets at launch</b><small>{info ? `${info.total} proven snipers/bundlers currently blocklisted — they can't buy in your opening window.` : 'Known snipers and bundlers from FEELESS forensics are refused in the opening window.'}</small></span></label>;
}

function LockedLaunchPreview({ enabled, minutes }) {
  const lock = Math.max(1, Number(minutes) || 30);
  const buyers = useMemo(() => [
    ['Sniper', 0], ['Bot', 0.2], ['Early buyer', 2], ['Buyer', 5], ['Buyer', 9], ['Late buyer', 15],
  ].map(([who, at], i) => ({ id: i, who, at: rounded(at * lock / 30), until: rounded(at * lock / 30 + lock) })), [lock]);
  if (!enabled) return <p className="provider-note">Locked Launch is off — buys settle immediately, same as a standard bonding-curve launch.</p>;
  const end = buyers[buyers.length - 1].until;
  const pct = v => `${(v / end) * 100}%`;
  return <div className="lock-launch-preview" data-testid="lock-launch-preview">
    <div className="lock-gantt">
      <div className="lock-gantt-axis"><span>t+0</span><span>t+{rounded(end / 2)}m</span><span>t+{end}m</span></div>
      {buyers.map(b => <div key={b.id} className="lock-gantt-row">
        <span className="lock-gantt-who">{b.who}</span>
        <div className="lock-gantt-lane">
          <span className="lock-gantt-bar" style={{ left: pct(b.at), width: pct(b.until - b.at) }} title={`Bought t+${b.at}m · can sell from t+${b.until}m`}><i /></span>
          <span className="lock-gantt-free" style={{ left: pct(b.until) }} />
        </div>
        <span className="lock-gantt-time">sells ≥ t+{b.until}m</span>
      </div>)}
    </div>
    <div className="lock-gantt-legend"><span><i className="lg-lock" />Locked in escrow</span><span><i className="lg-free" />Free to sell</span></div>
    <p className="provider-note">Each buy is locked for <b>{lock} minutes from the moment it lands</b>. A sniper who buys at t+0 can't sell before t+{lock}m — by then every buyer who followed has had the same {lock} minutes of price action, so there's no instant dump into the crowd.</p>
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


const XIcon = ({ size = 14 }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.9 2H22l-7.6 8.7L23 22h-6.8l-5.3-6.9L4.8 22H1.7l8.1-9.3L1 2h7l4.8 6.3L18.9 2Zm-1.2 18h1.9L7.4 3.9H5.4L17.7 20Z" /></svg>;

export function socialHref(kind, value) {
  const v = (value || '').trim();
  if (!v) return null;
  if (/^https:\/\//i.test(v)) return v;
  const handle = v.replace(/^@/, '');
  if (kind === 'twitter') return `https://x.com/${handle}`;
  if (kind === 'telegram') return `https://t.me/${handle}`;
  return null;
}

async function resizeToDataUrl(file, max = 512) {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, max / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL(file.type === 'image/png' || file.type === 'image/gif' ? 'image/png' : 'image/webp', 0.9);
}

function ImageDrop({ value, name, onUploaded }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [over, setOver] = useState(false);
  const handle = async file => {
    if (!file) return;
    setErr('');
    if (!/^image\/(png|jpeg|webp|gif)$/.test(file.type)) { setErr('PNG, JPG, WEBP or GIF'); return; }
    if (file.size > 10_000_000) { setErr('Max 10 MB'); return; }
    setBusy(true);
    try {
      const dataUrl = await resizeToDataUrl(file);
      const res = await fetch(apiUrl('/api/reputation/uploads'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ dataUrl }) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Upload failed');
      onUploaded(`${window.location.origin}${data.url}`);
    } catch (e) { setErr(e.message || 'Upload failed'); } finally { setBusy(false); }
  };
  return <label className={`meta-launch-image-preview image-drop ${over ? 'is-over' : ''}`} data-testid="meta-launch-image-preview"
    onDragOver={e => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
    onDrop={e => { e.preventDefault(); setOver(false); handle(e.dataTransfer.files?.[0]); }}>
    <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" hidden onChange={e => handle(e.target.files?.[0])} />
    {value ? <img src={value} alt={`${name || 'Token'} preview`} onError={event => { event.currentTarget.style.display = 'none'; }} /> : <><ImageIcon size={20} /><span>{busy ? 'Uploading…' : 'Click or drop image'}</span></>}
    {value && <span className="image-drop-change">{busy ? 'Uploading…' : 'Change'}</span>}
    {err && <small className="meta-launch-error">{err}</small>}
  </label>;
}

function StylePicker({ value, onPick }) {
  return <div className="launch-style-grid" role="radiogroup" aria-label="Launch style">{LAUNCH_STYLES.map(style => <button type="button" role="radio" aria-checked={value === style.id} key={style.id} data-testid={`launch-style-${style.id}`} className={`launch-style-card style-${style.id} ${value === style.id ? 'selected' : ''}`} onClick={() => onPick(style)}>
    <span className="launch-style-tag">{style.tag}</span>
    <b>{style.id === 'ember' && <EmberIcon size={14} />}{style.name}</b>
    <small>{style.blurb}</small>
  </button>)}</div>;
}

function mechanicChips(form) {
  const chips = [];
  if (form.blockKnownSnipers !== false) chips.push(['block', 'Blocklist enforced']);
  if (numeric(form.tradeBurn) > 0) chips.push(['ember', `${form.tradeBurn}% burn / trade`]);
  if (numeric(form.buybackBurnShare) > 0) chips.push(['burn', `${form.buybackBurnShare}% fees → buyback & burn`]);
  if (numeric(form.holderRewardShare) > 0) chips.push(['rewards', `${form.holderRewardShare}% fees → holders`]);
  if (form.lockedLaunchEnabled) chips.push(['lock', `Locked Launch · ${form.lockDurationMinutes}m`]);
  if (numeric(form.maxWalletPct) > 0) chips.push(['cap', `Max wallet ${form.maxWalletPct}% at open`]);
  if (numeric(form.antiSniperTax) > 0) chips.push(['snipe', `${form.antiSniperTax}% → 0% over ${form.antiSniperWindow}s`]);
  if (numeric(form.devVestingDays) > 0) chips.push(['vest', `Dev buy vests ${form.devVestingDays}d`]);
  chips.push(['lp', 'LP locked forever']);
  return chips;
}

function LaunchPreviewCard({ form }) {
  const links = [['website', Globe, form.website], ['twitter', XIcon, form.twitter], ['telegram', Send, form.telegram], ['discord', MessageCircle, form.discord]]
    .map(([k, Icon, v]) => [k, Icon, socialHref(k, v)]).filter(([, , href]) => href);
  const style = LAUNCH_STYLES.find(x => x.id === form.launchStyle);
  return <div className="launch-preview-card" data-testid="launch-preview-card">
    <span className="eyebrow">LIVE PREVIEW · HOW BUYERS SEE IT</span>
    <div className="launch-preview-id">
      <div className="launch-preview-img">{form.imageUrl ? <img src={form.imageUrl} alt="" onError={e => { e.currentTarget.style.display = 'none'; }} /> : <span>{(form.symbol || '?').slice(0, 2).toUpperCase()}</span>}</div>
      <div><b>{form.name || 'Your coin'}</b><small>${(form.symbol || 'TICKER').toUpperCase()}{style ? ` · ${style.name}` : ''}</small></div>
    </div>
    {form.description && <p className="launch-preview-desc">{form.description}</p>}
    {links.length > 0 && <div className="launch-preview-links">{links.map(([k, Icon, href]) => <a key={k} href={href} target="_blank" rel="noreferrer" title={href}><Icon size={13} /></a>)}</div>}
    <div className="launch-preview-stats"><span><small>OPEN MC</small><b>${form.openingMarketCap}k</b></span><span><small>GRADUATES</small><b>{form.graduationTarget} {form.liquidityPair}</b></span><span><small>SWAP FEE</small><b>{form.swapFee}%</b></span></div>
    <div className="launch-preview-chips">{mechanicChips(form).map(([k, text]) => <span key={k} className={`chip-${k}`}>{text}</span>)}</div>
  </div>;
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
  const MECHANIC_KEYS = ['openingMarketCap', 'curveType', 'graduationTarget', 'swapFee', 'creatorFeeShare', 'referralShare', 'holderRewardShare', 'buybackBurnShare', 'antiSniperTax', 'antiSniperWindow', 'tradeBurn', 'maxWalletPct', 'lockedLaunchEnabled', 'lockDurationMinutes', 'devVestingDays'];
  const update = (name, value) => setForm(current => ({ ...current, [name]: value, ...(MECHANIC_KEYS.includes(name) && current.launchStyle !== 'feeless' ? { launchStyle: 'custom' } : {}) }));
  const pickStyle = style => { setForm(current => ({ ...current, ...style.values, launchStyle: style.id })); setErrors({}); };
  const [launchStep, setLaunchStep] = useState(1);
  const registered = React.useRef(false);
  useEffect(() => {
    if (deployment.state !== 'confirmed' || !deployment.mint || !wallet?.address || registered.current) return;
    registered.current = true;
    fetch(apiUrl('/api/reputation/feeless-launch'), { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chain: 'solana', wallet: wallet.address, mint: deployment.mint, symbol: form.symbol }) }).catch(() => {});
  }, [deployment.state, deployment.mint, wallet?.address, form.symbol]);
  const goStep = n => { setLaunchStep(n); if (typeof window !== 'undefined') window.scrollTo?.({ top: 0, behavior: 'smooth' }); };
  const stepOf = key => STEP_ONE_KEYS.includes(key) ? 1 : STEP_TWO_KEYS.includes(key) ? 2 : 3;
  const nextStep = () => {
    const all = validateMetaLaunch(form);
    const mine = Object.fromEntries(Object.entries(all).filter(([k]) => stepOf(k) === launchStep));
    setErrors(mine);
    if (!Object.keys(mine).length) goStep(launchStep + 1);
  };
  const review = event => {
    event.preventDefault();
    const nextErrors = validateMetaLaunch(form);
    setErrors(nextErrors);
    const keys = Object.keys(nextErrors);
    if (!keys.length) setStep('review');
    else goStep(Math.min(...keys.map(stepOf)));
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
    <header className="meta-launch-header"><div><span className="eyebrow">CURVE → GRADUATION → COMMUNITY</span><h1>Launch with a living economy.</h1><p>Build the curve, define where every swap fee goes, protect the opening seconds, then graduate into permanent liquidity. This is a launch plan until an approved provider is connected.</p></div></header>
      {step === 'setup' && <details className="meta-launch-howto"><summary><Sparkles size={14} />How FEELESS launches work — curve, graduation, and what each box controls</summary>      <div className="meta-launch-mechanics-banner" data-testid="meta-launch-mechanics-banner"><div><span className="eyebrow"><Waves size={13} /> RAYDIUM-STYLE CURVE / INFINITY-STYLE ROUTING</span><h2>Every phase has a job.</h2><p>Buyers start on a deterministic bonding curve. When the target is reached, liquidity graduates to a Raydium pool. Fees can reward the creator, holders, or an automatic buyback-and-burn route.</p></div><div className="meta-launch-mechanics-flow"><span>CURVE</span><i>→</i><span>GRADUATE</span><i>→</i><span>POOL</span></div></div>
      <section className="meta-launch-box-guide" data-testid="meta-launch-box-guide"><div className="meta-launch-box-guide-heading"><div><span className="eyebrow">READ THE LAUNCH PLAN</span><h2>Know what each box controls.</h2></div><small>Nothing is hidden behind a wallet prompt.</small></div><div className="meta-launch-box-guide-grid">{LAUNCH_BOX_GUIDE.map(([title, label, detail], index) => <article key={title}><span>0{index + 1}</span><div><b>{title}</b><strong>{label}</strong><p>{detail}</p></div></article>)}</div></section></details>}
     {step === 'setup' ? <form className="meta-launch-grid" onSubmit={review} noValidate>
       <nav className="launch-stepper" aria-label="Launch steps">{LAUNCH_STEPS.map(([n, title, sub]) => <button type="button" key={n} className={`${launchStep === n ? 'active' : ''} ${launchStep > n ? 'done' : ''}`} aria-current={launchStep === n ? 'step' : undefined} data-testid={`launch-step-${n}`} onClick={() => goStep(n)}><i>{launchStep > n ? '✓' : n}</i><span><b>{title}</b><small>{sub}</small></span></button>)}</nav>
        <section hidden={launchStep !== 1} className="meta-launch-section"><div className="meta-launch-section-heading"><Rocket size={17} /><div><h2>Token identity</h2><p>Name, ticker, image, and whole-token supply. The public image is included in the launch metadata.</p></div></div><div className="meta-launch-fields two"><Field label="Coin name" name="name" placeholder="Meta Coin" value={form.name} onChange={update} error={errors.name} /><Field label="Symbol" name="symbol" placeholder="META" value={form.symbol} onChange={update} error={errors.symbol} autoCapitalize="characters" /></div><div className="meta-launch-image-row"><Field label="Token image URL" name="imageUrl" type="url" placeholder="https://example.com/token.png" value={form.imageUrl} onChange={update} error={errors.imageUrl} hint="Public HTTPS image" /><ImageDrop value={form.imageUrl} name={form.name} onUploaded={url => update('imageUrl', url)} /></div><label className="meta-launch-field meta-launch-desc"><span>Description<small>{(form.description || '').length}/280</small></span><textarea name="description" rows="3" maxLength={280} placeholder="What is this coin about? One or two lines buyers will see." value={form.description} onChange={event => update('description', event.target.value)} />{errors.description && <small className="meta-launch-error">{errors.description}</small>}</label></section>
      <section hidden={launchStep !== 1} className="meta-launch-section" id="launch-links"><div className="meta-launch-section-heading"><Link2 size={17} /><div><h2>Links & socials</h2><p>Shown on the coin page and preview so buyers can verify the project. All optional.</p></div></div><div className="meta-launch-fields two"><Field label="Website" name="website" type="url" placeholder="https://yourcoin.xyz" value={form.website} onChange={update} error={errors.website} /><Field label="X (Twitter)" name="twitter" placeholder="@yourcoin or https://x.com/yourcoin" value={form.twitter} onChange={update} error={errors.twitter} /><Field label="Telegram" name="telegram" placeholder="@yourcoin or https://t.me/yourcoin" value={form.telegram} onChange={update} error={errors.telegram} /><Field label="Discord" name="discord" placeholder="https://discord.gg/invite" value={form.discord} onChange={update} error={errors.discord} /></div></section>
       <section hidden={launchStep !== 2} className="meta-launch-section meta-launch-style-section" id="launch-style"><div className="meta-launch-section-heading"><Sparkles size={17} /><div><h2>Launch style</h2><p>Start from a proven mechanic set, then fine-tune anything below.</p></div></div><StylePicker value={form.launchStyle} onPick={pickStyle} /></section>
      <section hidden={launchStep !== 2} className="meta-launch-section"><div className="meta-launch-section-heading"><Gauge size={17} /><div><h2>Supply & bonding curve</h2><p>Pick a supply, the opening market cap, and the point where the curve graduates to a pool.</p></div></div><SupplyPicker value={form.supply} onChange={v => update('supply', v)} error={errors.supply} /><div className="meta-launch-fields two"><SelectField label="Opening market cap" name="openingMarketCap" value={form.openingMarketCap} onChange={update} error={errors.openingMarketCap}>{OPENING_MARKET_CAPS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</SelectField><SelectField label="Curve shape" name="curveType" value={form.curveType} onChange={update} error={errors.curveType}><option value="linear">Linear · predictable steps</option><option value="exponential">Exponential · faster price discovery</option></SelectField><Field label="Graduation target" name="graduationTarget" type="number" min="1" step="any" value={form.graduationTarget} onChange={update} error={errors.graduationTarget} hint="SOL / quote asset" /></div></section>
      <section hidden={launchStep !== 2} className="meta-launch-section"><div className="meta-launch-section-heading"><Coins size={17} /><div><h2>Liquidity graduation</h2><p>Set the quote asset, destination pool, and a permanent lock for graduated liquidity.</p></div></div><div className="meta-launch-fields two"><SelectField label="Quote asset" name="liquidityPair" value={form.liquidityPair} onChange={update} error={errors.liquidityPair}>{QUOTE_ASSETS.map(([v, label, note]) => <option key={v} value={v}>{`${label} · ${note}`}</option>)}</SelectField><SelectField label="Graduation venue" name="migrationVenue" value={form.migrationVenue} onChange={update} error={errors.migrationVenue}>{GRADUATION_VENUES.map(([v, label, note]) => <option key={v} value={v}>{`${label} · ${note}`}</option>)}</SelectField><SelectField label="Liquidity lock" name="liquidityLock" value={form.liquidityLock} onChange={update} error={errors.liquidityLock}><option value="permanent">Permanent · unruggable</option></SelectField></div></section>
      <section hidden={launchStep !== 2} className="meta-launch-section"><div className="meta-launch-section-heading"><Flame size={17} /><div><h2>Fee routing</h2><p>One swap fee. Four visible destinations. The split must always equal 100%.</p></div></div><div className="meta-launch-fields two"><Field label="Swap fee (%)" name="swapFee" type="number" min="0" max="10" step="0.1" value={form.swapFee} onChange={update} error={errors.swapFee} hint="Applied on buys and sells" /><Field label="Creator share (%)" name="creatorFeeShare" type="number" min="0" max="100" step="0.1" value={form.creatorFeeShare} onChange={update} error={errors.creatorFeeShare} /><Field label="Referral share (%)" name="referralShare" type="number" min="0" max="100" step="0.1" value={form.referralShare} onChange={update} error={errors.referralShare} hint="Paid to whoever referred the buyer" /><Field label="Holder rewards share (%)" name="holderRewardShare" type="number" min="0" max="100" step="0.1" value={form.holderRewardShare} onChange={update} error={errors.holderRewardShare} /><Field label="Buyback & burn share (%)" name="buybackBurnShare" type="number" min="0" max="100" step="0.1" value={form.buybackBurnShare} onChange={update} error={errors.buybackBurnShare} /><Field label="Ember burn per trade (%)" name="tradeBurn" type="number" min="0" max="5" step="0.1" value={form.tradeBurn} onChange={update} error={errors.tradeBurn} hint="Tokens burned on every buy & sell" /></div><FeeSplitSummary form={form} />{errors.feeShares && <p className="meta-launch-error" role="alert">{errors.feeShares}</p>}</section>
      <section hidden={launchStep !== 3} className="meta-launch-section"><div className="meta-launch-section-heading"><Timer size={17} /><div><h2>Opening protection</h2><p>Give the first seconds a transparent anti-sniper rule. It routes to holders, not a hidden wallet.</p></div></div><div className="meta-launch-fields two"><Field label="Opening buy tax (%)" name="antiSniperTax" type="number" min="0" max="100" step="1" value={form.antiSniperTax} onChange={update} error={errors.antiSniperTax} hint="Falls away after the window" /><Field label="Protection window (seconds)" name="antiSniperWindow" type="number" min="0" max="60" step="1" value={form.antiSniperWindow} onChange={update} error={errors.antiSniperWindow} /><Field label="Optional dev buy" name="devBuyAmount" type="number" min="0" step="any" value={form.devBuyAmount} onChange={update} error={errors.devBuyAmount} hint="SOL / quote asset" /><Field label="Dev buy vesting (days)" name="devVestingDays" type="number" min="0" max="365" step="1" value={form.devVestingDays} onChange={update} error={errors.devVestingDays} hint="0 = unlocked" /><Field label="Max wallet at open (%)" name="maxWalletPct" type="number" min="0" max="100" step="0.1" value={form.maxWalletPct} onChange={update} error={errors.maxWalletPct} hint="0 = off · lifts after the window" /></div><BlocklistToggle enabled={form.blockKnownSnipers !== false} onChange={v => update('blockKnownSnipers', v)} /></section>
      <section hidden={launchStep !== 3} className="meta-launch-section"><div className="meta-launch-section-heading"><LockKeyhole size={17} /><div><h2>Locked Launch <span className="state-tag amber">ANTI-RUG</span></h2><p>Every buy sits in escrow before it can be resold — chronological unlock means snipers can't dump into buyers who arrived seconds after them.</p></div></div><label className="meta-launch-toggle"><input type="checkbox" checked={form.lockedLaunchEnabled} onChange={event => update('lockedLaunchEnabled', event.target.checked)} /><span>Enable Locked Launch for this token</span></label>{form.lockedLaunchEnabled && <div className="meta-launch-fields two"><Field label="Lock duration (minutes)" name="lockDurationMinutes" type="number" min="1" max="1440" step="1" value={form.lockDurationMinutes} onChange={update} error={errors.lockDurationMinutes} hint="Every buy unlocks this long after it lands" /></div>}<LockedLaunchPreview enabled={form.lockedLaunchEnabled} minutes={form.lockDurationMinutes} /></section>
      <section hidden={launchStep !== 3} className="meta-launch-section"><div className="meta-launch-section-heading"><Users size={17} /><div><h2>Community distribution</h2><p>Reserve supply for holders and list airdrop recipients before review.</p></div></div><div className="meta-launch-fields two"><Field label="Holder allocation (%)" name="holderAllocation" type="number" min="0" max="100" step="0.1" value={form.holderAllocation} onChange={update} error={errors.holderAllocation} /><Field label="Airdrop allocation (%)" name="airdropAmount" type="number" min="0" max="100" step="0.1" value={form.airdropAmount} onChange={update} error={errors.airdropAmount} /></div><label className="meta-launch-field"><span>Airdrop recipients<small>One wallet address per line</small></span><textarea name="airdropRecipients" rows="4" placeholder="Wallet address 1&#10;Wallet address 2" value={form.airdropRecipients} onChange={event => update('airdropRecipients', event.target.value)} />{errors.airdropRecipients && <small className="meta-launch-error">{errors.airdropRecipients}</small>}</label>{errors.allocations && <p className="meta-launch-error" role="alert">{errors.allocations}</p>}</section>
       <section hidden={launchStep !== 3} className="meta-launch-section meta-launch-provider-section"><div className="meta-launch-section-heading"><Rocket size={17} /><div><h2>Choose your launch rail</h2><p>FEELESS coordinates the launch review. A provider must be explicitly approved before it can prepare transactions.</p></div></div><div className="meta-launch-provider-picker" role="radiogroup" aria-label="Launch provider">{META_LAUNCH_PROVIDERS.map(providerOption => { const providerReadiness = getLaunchProviderReadiness(providerOption.id); return <button type="button" role="radio" aria-checked={form.providerId === providerOption.id} key={providerOption.id} className={`meta-launch-provider-option ${form.providerId === providerOption.id ? 'selected' : ''}`} data-testid={`meta-launch-provider-${providerOption.id}`} onClick={() => { update('providerId', providerOption.id); setDeployment({ state: 'idle', statuses: {} }); }}><span className="meta-launch-provider-option-top"><b>{providerOption.label}</b><span className={`provider-state ${providerReadiness.ready ? 'ready' : ''}`}>{providerReadiness.ready ? 'READY' : 'NOT CONFIGURED'}</span></span><small>{providerOption.note}</small></button>; })}</div><p className="meta-launch-provider-context"><span className="live-dot" />Selected: <b>{selectedProvider.label}</b> · {readiness.provider?.description || 'Provider status unavailable.'}</p></section>
       <div className="launch-step-footer">{launchStep > 1 ? <button type="button" className="btn-outline" onClick={() => goStep(launchStep - 1)}><ArrowLeft size={15} />Back</button> : <span />}{launchStep < 3 ? <button type="button" className="btn-primary" data-testid="launch-step-next" onClick={nextStep}>Continue to {LAUNCH_STEPS[launchStep][1]}<ArrowRight size={15} /></button> : <button type="submit" className="btn-primary">Review launch<ArrowRight size={15} /></button>}</div>
      <aside className="meta-launch-sidebar"><LaunchPreviewCard form={form} /><div className="meta-launch-readiness"><span className="eyebrow">LAUNCH READINESS</span><LaunchEligibilityPanel wallet={wallet} chain="solana" /><StatusRow icon={wallet ? CheckCircle2 : Clock3} title={wallet ? 'Wallet connected' : 'Wallet approval after review'} detail={wallet ? `${wallet.name} · ${wallet.address.slice(0, 6)}…` : 'No wallet request is made while editing mechanics.'} ready={Boolean(wallet)} /><StatusRow icon={readiness.providerReady ? CheckCircle2 : LockKeyhole} title={readiness.providerReady ? readiness.providerName : 'Provider unavailable'} detail={readiness.providerReady ? `${readiness.network} · approved provider` : 'Approved provider URL and approval status are required.'} ready={readiness.providerReady} /><StatusRow icon={readiness.rpcReady ? CheckCircle2 : LockKeyhole} title={readiness.rpcReady ? 'Solana RPC configured' : 'Solana RPC unavailable'} detail={readiness.rpcReady ? `${readiness.network} · ${readiness.rpcHost}` : 'No on-chain confirmation or submission will be attempted.'} ready={readiness.rpcReady} /><p className="meta-launch-safety">FEELESS never stores private keys. The provider prepares unsigned phases; your wallet signs them only after review.</p></div><div className="meta-launch-sidebar-note"><ShieldCheck size={15} /><span><b>Permanent liquidity. Visible routing.</b><small>Creator rewards, holder rewards, and buyback-and-burn shares are declared before launch.</small></span></div><button className="btn-primary meta-launch-review" data-testid="meta-launch-review" type="submit">Review launch mechanics<ArrowRight size={16} /></button></aside>
    </form> : <section className="meta-launch-review-page" data-testid="meta-launch-review-page">
       <div className="meta-launch-review-heading"><div className="meta-launch-review-identity">{form.imageUrl && <img src={form.imageUrl} alt="" onError={event => { event.currentTarget.style.display = 'none'; }} />}<div><span className="eyebrow">CHECK BEFORE SIGNING</span><h2>{form.name} <span>${form.symbol}</span></h2><p>Your launch mechanics and token identity are valid. Review the curve, routing, protection, and community allocations before any provider request.</p></div></div><button className="btn-outline" data-testid="meta-launch-edit" onClick={() => setStep('setup')}><ArrowLeft size={15} />Edit mechanics</button></div>
       <div className="meta-launch-review-cards"><div><span>Launch provider</span><b>{selectedProvider.label}</b><small>{readiness.ready ? 'Approved preparation rail' : 'Not configured for execution'}</small></div><div><span>Opening market cap</span><b>${form.openingMarketCap}k</b><small>{form.curveType} curve</small></div><div><span>Graduation target</span><b>{form.graduationTarget} {form.liquidityPair}</b><small>{GRADUATION_VENUES.find(([v]) => v === form.migrationVenue)?.[1] || form.migrationVenue} · permanent lock</small></div><div><span>Fee routing</span><b>{form.swapFee}% swap fee</b><small>{form.creatorFeeShare}% creator · {form.holderRewardShare}% holders · {form.buybackBurnShare}% buyback & burn</small></div><div><span>Launch style</span><b>{LAUNCH_STYLES.find(x => x.id === form.launchStyle)?.name || 'Custom'}</b><small>{mechanicChips(form).map(([, t]) => t).join(' · ')}</small></div><div><span>Opening protection</span><b>{form.antiSniperTax}% → 0%</b><small>After {form.antiSniperWindow}s · optional dev buy {form.devBuyAmount} {form.liquidityPair}</small></div></div>
      <div className="meta-launch-summary"><dl><div><dt>Total supply</dt><dd>{form.supply}</dd></div><div><dt>Quote asset</dt><dd>{form.liquidityPair}</dd></div><div><dt>Holder allocation</dt><dd>{form.holderAllocation}%</dd></div><div><dt>Airdrop</dt><dd>{form.airdropAmount}% · {recipients.length} recipients</dd></div>{['website', 'twitter', 'telegram', 'discord'].map(k => socialHref(k, form[k]) && <div key={k}><dt>{k === 'twitter' ? 'X' : k[0].toUpperCase() + k.slice(1)}</dt><dd><a href={socialHref(k, form[k])} target="_blank" rel="noreferrer">{socialHref(k, form[k]).replace(/^https:\/\//, '')}</a></dd></div>)}</dl></div>
      <div className={`meta-launch-review-actions ${deployment.state === 'failed' ? 'has-failure' : ''}`}><div className={`meta-launch-deployment-note ${deployment.state === 'failed' ? 'failed' : deployment.state === 'confirmed' ? 'confirmed' : ''}`} data-testid="meta-launch-provider-warning">{deployment.state === 'failed' ? <AlertTriangle size={17} /> : deployment.state === 'confirmed' ? <CheckCircle2 size={17} /> : <ShieldCheck size={17} />}<span><b>{deployment.state === 'confirmed' ? 'Launch confirmed.' : deployment.state === 'failed' ? 'Launch could not be completed.' : deployment.resumeReady ? 'Continue remaining launch phases.' : deployment.state === 'pending' ? 'Launch confirmation is pending.' : readiness.ready ? 'Ready for wallet approval.' : 'Deployment is not available yet.'}</b><small>{deployment.detail || (readiness.ready ? 'Your wallet will review each phase after you continue.' : unavailableReason)}</small></span></div>{pendingStep && <button className="btn-outline" data-testid="meta-launch-recheck" type="button" disabled={checkingSignature} onClick={recheckPendingSignature}>{checkingSignature ? <><LoaderCircle size={16} className="meta-launch-spinner" />Checking…</> : 'Check pending signature'}</button>}<button className="btn-primary" data-testid="meta-launch-deploy" type="button" disabled={!deploymentReady} title={deployment.resumeReady ? 'Continue the remaining launch phases' : readiness.ready ? 'Request wallet approval and deploy' : unavailableReason} onClick={deploy}>{deploying ? <><LoaderCircle size={16} className="meta-launch-spinner" />Deploying…</> : deployment.state === 'confirmed' ? 'Launch confirmed' : deployment.resumeReady ? 'Continue launch' : 'Approve & deploy'}</button></div>
       {deployment.state === 'confirmed' && deployment.mint && <div className="meta-launch-mint-receipt" data-testid="meta-launch-mint-receipt"><span><b>Created mint</b><small>{deployment.mint}</small></span><span className="meta-launch-mint-receipt-actions"><ReceiptCopyButton value={deployment.mint} label="Copy mint" testId="meta-launch-mint-copy" /><a className="meta-launch-explorer-link" data-testid="meta-launch-mint-explorer" href={getSolanaExplorerUrl(deployment.mint, 'address')} target="_blank" rel="noreferrer">View mint on Solana Explorer <ArrowRight size={13} /></a></span></div>}
      {(deployment.state !== 'idle' || deploying) && <div className="meta-launch-deployment-status" data-testid="meta-launch-deployment-status"><h3>Deployment phases</h3>{META_LAUNCH_STEPS.map(stepItem => <StepStatus key={stepItem.id} step={stepItem} status={deployment.statuses[stepItem.id]} />)}</div>}
    </section>}
  </div>;
}