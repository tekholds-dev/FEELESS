import React, { useMemo, useState } from 'react';
import { ArrowLeft, ArrowRight, CheckCircle2, LockKeyhole, Rocket, ShieldCheck, WalletCards } from 'lucide-react';
import { useWallet } from '../../hooks/useWallet';

export const DEFAULT_META_LAUNCH_FORM = {
  name: '',
  symbol: '',
  supply: '1000000000',
  decimals: '9',
  liquidityPair: 'SOL',
  liquidityAmount: '',
  buyTax: '0',
  sellTax: '0',
  holderAllocation: '0',
  airdropRecipients: '',
  airdropAmount: '0',
};

const numeric = value => Number(value);

export function validateMetaLaunch(form) {
  const errors = {};
  if (!form.name.trim()) errors.name = 'Enter a coin name.';
  if (!/^[A-Za-z0-9]{2,12}$/.test(form.symbol.trim())) errors.symbol = 'Use 2–12 letters or numbers.';
  if (!Number.isFinite(numeric(form.supply)) || numeric(form.supply) <= 0) errors.supply = 'Supply must be greater than zero.';
  if (!Number.isInteger(numeric(form.decimals)) || numeric(form.decimals) < 0 || numeric(form.decimals) > 18) errors.decimals = 'Decimals must be between 0 and 18.';
  if (!form.liquidityPair) errors.liquidityPair = 'Choose a liquidity pair.';
  if (!Number.isFinite(numeric(form.liquidityAmount)) || numeric(form.liquidityAmount) <= 0) errors.liquidityAmount = 'Add an initial liquidity amount.';
  if (!Number.isFinite(numeric(form.buyTax)) || numeric(form.buyTax) < 0 || numeric(form.buyTax) > 10) errors.buyTax = 'Buy tax must be between 0% and 10%.';
  if (!Number.isFinite(numeric(form.sellTax)) || numeric(form.sellTax) < 0 || numeric(form.sellTax) > 10) errors.sellTax = 'Sell tax must be between 0% and 10%.';
  if (!Number.isFinite(numeric(form.holderAllocation)) || numeric(form.holderAllocation) < 0 || numeric(form.holderAllocation) > 100) errors.holderAllocation = 'Holder allocation must be between 0% and 100%.';
  if (!Number.isFinite(numeric(form.airdropAmount)) || numeric(form.airdropAmount) < 0 || numeric(form.airdropAmount) > 100) errors.airdropAmount = 'Airdrop allocation must be between 0% and 100%.';
  const recipients = form.airdropRecipients.split(/[\n,]+/).map(value => value.trim()).filter(Boolean);
  if (numeric(form.airdropAmount) > 0 && !recipients.length) errors.airdropRecipients = 'Add at least one recipient for the airdrop.';
  if (numeric(form.holderAllocation) + numeric(form.airdropAmount) > 100) errors.allocations = 'Holder and airdrop allocations cannot exceed 100%.';
  return errors;
}

function Field({ label, name, value, onChange, error, ...props }) {
  return <label className="meta-launch-field"><span>{label}</span><input name={name} value={value} onChange={event => onChange(name, event.target.value)} {...props} />{error && <small className="meta-launch-error">{error}</small>}</label>;
}

function StatusRow({ icon: Icon, title, detail, ready = false }) {
  return <div className={`meta-launch-status ${ready ? 'ready' : ''}`}><Icon size={16} /><span><b>{title}</b><small>{detail}</small></span></div>;
}

export default function MetaLaunchSetup({ onWallet, initialValues }) {
  const { wallet } = useWallet();
  const [form, setForm] = useState({ ...DEFAULT_META_LAUNCH_FORM, ...initialValues });
  const [errors, setErrors] = useState({});
  const [step, setStep] = useState('setup');
  const launchProviderConfigured = Boolean(process.env.REACT_APP_LAUNCH_API_URL);
  const recipients = useMemo(() => form.airdropRecipients.split(/[\n,]+/).map(value => value.trim()).filter(Boolean), [form.airdropRecipients]);
  const update = (name, value) => setForm(current => ({ ...current, [name]: value }));
  const review = event => {
    event.preventDefault();
    const nextErrors = validateMetaLaunch(form);
    setErrors(nextErrors);
    if (!Object.keys(nextErrors).length) setStep('review');
  };
  const unavailableReason = !wallet
    ? 'Connect a wallet to prepare deployment.'
    : !launchProviderConfigured
      ? 'An approved launch provider is not configured.'
      : 'Deployment adapter is not enabled in this environment.';

  return <div className="meta-launch-page" data-testid="meta-launch-page">
    <div className="meta-launch-topline"><a href="/terminal/launch" className="meta-launch-back"><ArrowLeft size={14} />Launchpads</a><span className="eyebrow"><span className="live-dot" /> FEELESS META LAUNCH</span></div>
    <header className="meta-launch-header"><div><span className="eyebrow">BUILD WITH CONTROL</span><h1>Meta Launch setup.</h1><p>Configure the coin, liquidity policy, allocations, and launch safeguards before any wallet approval is requested.</p></div><div className="meta-launch-step"><span className={step === 'setup' ? 'active' : ''}>01 Setup</span><span className={step === 'review' ? 'active' : ''}>02 Review</span></div></header>
    {step === 'setup' ? <form className="meta-launch-grid" onSubmit={review} noValidate>
      <section className="meta-launch-section"><div className="meta-launch-section-heading"><Rocket size={17} /><div><h2>Coin identity</h2><p>Set the public details for the new coin.</p></div></div><div className="meta-launch-fields two"><Field label="Coin name" name="name" placeholder="Meta Coin" value={form.name} onChange={update} error={errors.name} /><Field label="Symbol" name="symbol" placeholder="META" value={form.symbol} onChange={update} error={errors.symbol} autoCapitalize="characters" /><Field label="Total supply" name="supply" type="number" min="1" value={form.supply} onChange={update} error={errors.supply} /><Field label="Decimals" name="decimals" type="number" min="0" max="18" value={form.decimals} onChange={update} error={errors.decimals} /></div></section>
      <section className="meta-launch-section"><div className="meta-launch-section-heading"><ArrowRight size={17} /><div><h2>Liquidity</h2><p>Choose the pair and initial liquidity amount.</p></div></div><div className="meta-launch-fields two"><label className="meta-launch-field"><span>Liquidity pair</span><select name="liquidityPair" value={form.liquidityPair} onChange={event => update('liquidityPair', event.target.value)}><option value="SOL">SOL</option><option value="USDC">USDC</option></select>{errors.liquidityPair && <small className="meta-launch-error">{errors.liquidityPair}</small>}</label><Field label="Initial liquidity" name="liquidityAmount" type="number" min="0" step="any" placeholder="1.0" value={form.liquidityAmount} onChange={update} error={errors.liquidityAmount} /></div></section>
      <section className="meta-launch-section"><div className="meta-launch-section-heading"><ShieldCheck size={17} /><div><h2>Fee and tax policy</h2><p>Keep buy and sell fees bounded and visible.</p></div></div><div className="meta-launch-fields two"><Field label="Buy tax (%)" name="buyTax" type="number" min="0" max="10" step="0.1" value={form.buyTax} onChange={update} error={errors.buyTax} /><Field label="Sell tax (%)" name="sellTax" type="number" min="0" max="10" step="0.1" value={form.sellTax} onChange={update} error={errors.sellTax} /></div></section>
      <section className="meta-launch-section"><div className="meta-launch-section-heading"><WalletCards size={17} /><div><h2>Holders and airdrops</h2><p>Reserve supply deliberately; never hide allocations.</p></div></div><div className="meta-launch-fields two"><Field label="Holder allocation (%)" name="holderAllocation" type="number" min="0" max="100" step="0.1" value={form.holderAllocation} onChange={update} error={errors.holderAllocation} /><Field label="Airdrop allocation (%)" name="airdropAmount" type="number" min="0" max="100" step="0.1" value={form.airdropAmount} onChange={update} error={errors.airdropAmount} /></div><label className="meta-launch-field"><span>Airdrop recipients</span><textarea name="airdropRecipients" rows="4" placeholder="One wallet address per line" value={form.airdropRecipients} onChange={event => update('airdropRecipients', event.target.value)} />{errors.airdropRecipients && <small className="meta-launch-error">{errors.airdropRecipients}</small>}</label>{errors.allocations && <p className="meta-launch-error" role="alert">{errors.allocations}</p>}</section>
      <aside className="meta-launch-sidebar"><div className="meta-launch-readiness"><span className="eyebrow">LAUNCH READINESS</span><StatusRow icon={wallet ? CheckCircle2 : WalletCards} title={wallet ? 'Wallet connected' : 'Wallet required'} detail={wallet ? `${wallet.name} · ${wallet.address.slice(0, 6)}…` : 'Connect only when you are ready to review.'} ready={Boolean(wallet)} />{!wallet && <button type="button" className="btn-outline meta-launch-wallet" data-testid="meta-launch-connect-wallet" onClick={onWallet}><WalletCards size={15} />Connect wallet</button>}<StatusRow icon={launchProviderConfigured ? CheckCircle2 : LockKeyhole} title={launchProviderConfigured ? 'Provider configured' : 'Provider unavailable'} detail={launchProviderConfigured ? 'Ready for an approved deployment adapter.' : 'No launch transaction will be attempted.'} ready={launchProviderConfigured} /><p className="meta-launch-safety">FEELESS never stores private keys. Review is local until an approved provider and wallet signature are available.</p></div><button className="btn-primary meta-launch-review" data-testid="meta-launch-review" type="submit">Review launch setup<ArrowRight size={16} /></button></aside>
    </form> : <section className="meta-launch-review-page" data-testid="meta-launch-review-page">
      <div className="meta-launch-review-heading"><div><span className="eyebrow">CHECK BEFORE SIGNING</span><h2>{form.name} <span>${form.symbol}</span></h2><p>Your configuration is valid and ready for a final provider check.</p></div><button className="btn-outline" data-testid="meta-launch-edit" onClick={() => setStep('setup')}><ArrowLeft size={15} />Edit setup</button></div>
      <div className="meta-launch-summary"><dl><div><dt>Total supply</dt><dd>{form.supply}</dd></div><div><dt>Decimals</dt><dd>{form.decimals}</dd></div><div><dt>Liquidity</dt><dd>{form.liquidityAmount} {form.liquidityPair}</dd></div><div><dt>Buy / sell tax</dt><dd>{form.buyTax}% / {form.sellTax}%</dd></div><div><dt>Holder allocation</dt><dd>{form.holderAllocation}%</dd></div><div><dt>Airdrop</dt><dd>{form.airdropAmount}% · {recipients.length} recipients</dd></div></dl></div>
      <div className="meta-launch-review-actions"><div className="meta-launch-unavailable" data-testid="meta-launch-provider-warning"><LockKeyhole size={17} /><span><b>Deployment is not available yet.</b><small>{unavailableReason} This review does not submit transactions.</small></span></div><button className="btn-primary" data-testid="meta-launch-deploy" type="button" disabled title={unavailableReason}>Deployment unavailable</button></div>
    </section>}
  </div>;
}