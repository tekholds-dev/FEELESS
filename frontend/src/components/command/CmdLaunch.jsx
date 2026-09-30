import React, { useMemo, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../../hooks/useWallet';
import { apiUrl, errorText } from '../../lib/api';
import { getChatSession } from '../../lib/chatSession';
import { CROP, uploadCropped } from '../../lib/cropImage';
import { launchCoin, launchOnPump } from '../../lib/launchRail';
import { launchTerms, receiptLinks, coinErrors, socialLink } from '../../lib/cmdLaunch';
import { CopyBtn } from '../CopyBtn';

// Command Center launcher: pick the rail (house / FEELESS / pump.fun), pick the config for THIS coin, fill the coin,
// review every term, sign once, get the full receipt (CA, links, tx, metadata) right after.
const EMPTY = { name: '', symbol: '', description: '', imageUrl: '', bannerUrl: '', website: '', twitter: '', telegram: '', devBuy: '0' };
const HISTORY = 'feeless:cmd-launches';
const readHistory = () => { try { return JSON.parse(localStorage.getItem(HISTORY) || '[]'); } catch { return []; } };
const src = u => (u && u.startsWith('/') ? apiUrl(u) : u);

function Upload({ label, value, shape, wide, onDone }) {
  const [busy, setBusy] = useState(false);
  const pick = async file => {
    if (!file) return;
    setBusy(true);
    try { const url = await uploadCropped(file, shape, wide ? 1500 : 512); if (url) onDone(url); } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  return <label className={`cl-drop ${wide ? 'wide' : ''} ${value ? 'has' : ''}`}>
    <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" hidden onChange={e => pick(e.target.files?.[0])} />
    {value ? <img src={src(value)} alt="" /> : <span>{busy ? 'Uploading…' : label}</span>}
    {value && <em>{busy ? 'Uploading…' : 'Change'}</em>}
  </label>;
}

export function CmdLaunch({ rail }) {
  const { wallet, provider, connect, signMessage } = useWallet() || {};
  const house = rail?.house || [];
  const [kind, setKind] = useState(house.length ? 'house' : 'feeless');
  const [houseId, setHouseId] = useState(house[0]?.config || '');
  const [f, setF] = useState(EMPTY);
  const [step, setStep] = useState('coin');   // coin → review → receipt
  const [busy, setBusy] = useState('');
  const [receipt, setReceipt] = useState(null);
  const [history, setHistory] = useState(readHistory);
  const cfg = kind === 'house' ? house.find(h => h.config === houseId) : kind === 'feeless' ? rail : null;
  const errors = useMemo(() => coinErrors(f), [f]);
  const set = (k, v) => setF(x => ({ ...x, [k]: v }));
  const unit = cfg?.params?.quote === 'USDC' ? 'USDC' : 'SOL';
  const railOk = kind === 'pump' || Boolean(cfg?.config);

  const launch = async () => {
    try {
      if (wallet?.chain !== 'solana') { await connect?.('solana'); return; }
      setBusy('Signing in…');
      const session = await getChatSession(wallet.address, signMessage);
      const form = { ...f, name: f.name.trim(), symbol: f.symbol.trim().toUpperCase(), imageUrl: f.imageUrl, twitter: socialLink('twitter', f.twitter), telegram: socialLink('telegram', f.telegram), devBuyAmount: f.devBuy };
      let res;
      if (kind === 'pump') {
        res = await launchOnPump({ provider, creator: wallet.address, session, form, onStatus: setBusy });
      } else {
        setBusy('Publishing coin metadata…');
        const m = await fetch(apiUrl('/api/reputation/token-meta'), { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ address: wallet.address, session, name: form.name, symbol: form.symbol, description: form.description, image: form.imageUrl, banner: form.bannerUrl, website: form.website, twitter: form.twitter, telegram: form.telegram }) });
        const meta = await m.json().catch(() => ({}));
        if (!m.ok) throw new Error(meta.detail || 'Could not publish coin metadata.');
        const out = await launchCoin({ provider, creator: wallet.address, config: cfg.config, name: form.name, symbol: form.symbol, uri: meta.uri, firstBuySol: Number(f.devBuy) || 0, quoteDecimals: unit === 'USDC' ? 6 : 9, onStatus: setBusy });
        res = { ...out, uri: meta.uri };
      }
      const rec = { at: Date.now(), kind, mint: res.mint, signature: res.signature, uri: res.uri || '', wallet: wallet.address, name: form.name, symbol: form.symbol,
        imageUrl: form.imageUrl, devBuy: Number(f.devBuy) || 0, unit: kind === 'pump' ? 'SOL' : unit, config: cfg?.config || '', terms: launchTerms(kind, cfg) };
      setReceipt(rec); setStep('receipt');
      const next = [rec, ...readHistory()].slice(0, 20); setHistory(next);
      try { localStorage.setItem(HISTORY, JSON.stringify(next)); } catch { /* storage full: receipt still on screen */ }
      toast.success(`$${form.symbol} is live.`);
      // Tag it as a FEELESS launch + save banner/links to its coin profile (retries while the chain catches up).
      const body = JSON.stringify({ chain: 'solana', wallet: wallet.address, mint: res.mint, symbol: form.symbol, signature: res.signature, rail: kind === 'pump' ? 'pump' : 'feeless',
        profile: { description: form.description, bannerUrl: form.bannerUrl, website: form.website, twitter: form.twitter, telegram: form.telegram } });
      (async () => { for (let i = 0; i < 8; i++) { try { const r = await fetch(apiUrl('/api/reputation/feeless-launch'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body }); if (r.ok || (r.status !== 409 && r.status < 500)) return; } catch { /* retry */ } await new Promise(ok => setTimeout(ok, 4000)); } })();
    } catch (e) { toast.error(e.code === 4001 ? 'Declined in your wallet. Nothing was launched.' : errorText(e)); } finally { setBusy(''); }
  };

  if (step === 'receipt' && receipt) return <LaunchReceipt r={receipt} onNew={() => { setF(EMPTY); setReceipt(null); setStep('coin'); }} />;
  return <div className="cmd-launch m-stack" data-testid="cmd-launch">
    <div className="m-row cl-head"><span className="m-label">1 · RAIL</span>
      <div className="m-seg" role="radiogroup" aria-label="Launch rail">{[['house', '🏠 House', house.length > 0], ['feeless', '🌐 FEELESS', rail?.ready], ['pump', '💊 Pump.fun', true]].map(([k, l, ok]) =>
        <button key={k} type="button" role="radio" aria-checked={kind === k} disabled={!ok} title={ok ? '' : k === 'house' ? 'Create a house config in Step 1 first' : 'Create the public config first'} onClick={() => { setKind(k); setStep('coin'); }}>{l}</button>)}</div></div>
    {kind === 'house' && <div className="m-row"><span className="m-label">2 · CONFIG</span>
      <div className="m-seg" role="radiogroup" aria-label="House config">{house.map(h => <button key={h.config} type="button" role="radio" aria-checked={houseId === h.config} onClick={() => setHouseId(h.config)}>{h.label}</button>)}</div></div>}
    <div className="m-card cl-terms"><div className="m-label">{kind === 'pump' ? 'PUMP.FUN TERMS' : 'TERMS FOR THIS COIN'} <em>{cfg?.config ? `${cfg.config.slice(0, 4)}…${cfg.config.slice(-4)}` : ''}</em></div>
      <dl className="m-kv">{launchTerms(kind, cfg).map(([k, v]) => <React.Fragment key={k}><dt>{k}</dt><dd>{v}</dd></React.Fragment>)}</dl></div>

    {step === 'coin' && <div className="m-card m-stack m-pop"><div className="m-label">3 · COIN</div>
      <div className="cl-id"><Upload label="Coin image" value={f.imageUrl} shape={CROP.token} onDone={u => set('imageUrl', u)} />
        <div className="m-stack"><label className="m-field"><span>Name</span><input className="m-input" maxLength={32} value={f.name} onChange={e => set('name', e.target.value)} placeholder="Fee Cat" /></label>
          <label className="m-field"><span>Ticker</span><input className="m-input" maxLength={10} value={f.symbol} onChange={e => set('symbol', e.target.value.toUpperCase())} placeholder="FEECAT" /></label></div></div>
      <Upload label="Banner (3:1, optional)" value={f.bannerUrl} shape={CROP.banner} wide onDone={u => set('bannerUrl', u)} />
      <label className="m-field"><span>Description</span><textarea className="m-input" rows={2} maxLength={280} value={f.description} onChange={e => set('description', e.target.value)} placeholder="One or two lines buyers will see." /></label>
      <div className="m-grid">{[['website', 'Website', 'https://…'], ['twitter', 'X', '@handle'], ['telegram', 'Telegram', '@group']].map(([k, l, ph]) =>
        <label key={k} className="m-field"><span>{l}</span><input className="m-input" value={f[k]} onChange={e => set(k, e.target.value)} placeholder={ph} />{errors[k] && <small className="m-neg">{errors[k]}</small>}</label>)}
        <label className="m-field"><span>First buy ({kind === 'pump' ? 'SOL' : unit})</span><input className="m-input" inputMode="decimal" value={f.devBuy} onChange={e => set('devBuy', e.target.value.replace(/[^0-9.]/g, ''))} />{errors.devBuy && <small className="m-neg">{errors.devBuy}</small>}</label></div>
      <button type="button" className="m-btn primary wide" disabled={!railOk || Object.keys(errors).length > 0} onClick={() => setStep('review')} data-testid="cmd-launch-review">{Object.values(errors)[0] || 'Review launch →'}</button></div>}

    {step === 'review' && <div className="m-card is-hot m-stack m-pop" data-testid="cmd-launch-confirm"><div className="m-label">4 · REVIEW & SIGN</div>
      <div className="cl-sum">{f.imageUrl && <img src={src(f.imageUrl)} alt="" />}<div><b>{f.name}</b> <span className="m-chip ok">${f.symbol.toUpperCase()}</span><p className="m-dim">{f.description || 'No description.'}</p></div></div>
      <dl className="m-kv"><dt>Rail</dt><dd>{kind === 'house' ? `🏠 House · ${cfg?.label}` : kind === 'feeless' ? '🌐 FEELESS public config' : '💊 Pump.fun'}</dd>
        <dt>Creator wallet</dt><dd><code>{wallet?.address || 'connect a Solana wallet'}</code></dd>
        <dt>First buy</dt><dd>{Number(f.devBuy) || 0} {kind === 'pump' ? 'SOL' : unit} (same transaction, before anyone else)</dd>
        <dt>Links</dt><dd>{[socialLink('website', f.website), socialLink('twitter', f.twitter), socialLink('telegram', f.telegram)].filter(Boolean).join(' · ') || 'none'}</dd>
        <dt>Banner</dt><dd>{f.bannerUrl ? (kind === 'pump' ? 'FEELESS coin page (add it on pump.fun after launch)' : 'in metadata + FEELESS coin page') : 'none'}</dd>
        <dt>Network cost</dt><dd>≈ 0.02 SOL rent + fees{Number(cfg?.params?.poolCreationFeeSol) > 0 ? ` + ${cfg.params.poolCreationFeeSol} SOL toll` : ''}</dd></dl>
      <div className="m-row"><button type="button" className="m-btn" disabled={!!busy} onClick={() => setStep('coin')}>← Edit</button>
        <button type="button" className="m-btn primary" disabled={!!busy} onClick={launch} data-testid="cmd-launch-sign">{busy || (wallet?.chain === 'solana' ? `Sign & launch $${f.symbol.toUpperCase()}` : 'Connect Solana wallet')}</button></div>
      <small className="m-dim">Simulated first. Your wallet signs; FEELESS never holds a key. Nothing is sent until you approve.</small></div>}

    {history.length > 0 && <div className="m-card"><div className="m-label">RECENT LAUNCHES <em>this browser</em></div>
      <div className="cl-hist m-scroll">{history.map(h => <button key={h.mint} type="button" className="cl-hist-row" onClick={() => { setReceipt(h); setStep('receipt'); }}>
        <b>${h.symbol}</b><span>{h.kind === 'pump' ? '💊 pump' : h.kind === 'house' ? '🏠 house' : '🌐 feeless'}</span><code>{h.mint.slice(0, 4)}…{h.mint.slice(-4)}</code><em>{new Date(h.at).toLocaleDateString()}</em></button>)}</div></div>}
  </div>;
}

export function LaunchReceipt({ r, onNew }) {
  return <div className="m-card is-hot m-stack m-pop cl-receipt" data-testid="cmd-launch-receipt">
    <div className="m-row"><span className="m-label">LAUNCH RECEIPT</span><span className="m-chip ok">✓ confirmed on-chain</span></div>
    <div className="cl-sum">{r.imageUrl && <img src={src(r.imageUrl)} alt="" />}<div><b>{r.name}</b> <span className="m-chip ok">${r.symbol}</span><p className="m-dim">{new Date(r.at).toLocaleString()}</p></div></div>
    <div className="cl-ca"><small className="m-label">CONTRACT ADDRESS</small><code data-testid="cmd-launch-ca">{r.mint}</code><CopyBtn value={r.mint} /></div>
    <div className="m-row cl-links">{receiptLinks(r.kind, r.mint, r.signature).map(([l, u]) => <a key={l} className={`m-btn ${l === 'pump.fun' ? 'primary' : ''}`} href={u} target={u.startsWith('/') ? undefined : '_blank'} rel="noopener noreferrer">{l} ↗</a>)}</div>
    <dl className="m-kv"><dt>Rail</dt><dd>{r.kind === 'pump' ? 'Pump.fun' : r.kind === 'house' ? 'House config' : 'FEELESS public config'}</dd>
      {r.config && <><dt>Config</dt><dd><code>{r.config}</code></dd></>}
      <dt>Creator</dt><dd><code>{r.wallet}</code></dd>
      <dt>First buy</dt><dd>{r.devBuy} {r.unit}</dd>
      <dt>Transaction</dt><dd><code>{r.signature}</code></dd>
      {r.uri && <><dt>Metadata</dt><dd><a href={r.uri} target="_blank" rel="noopener noreferrer">{r.uri}</a></dd></>}
      {(r.terms || []).map(([k, v]) => <React.Fragment key={k}><dt>{k}</dt><dd>{v}</dd></React.Fragment>)}</dl>
    {onNew && <button type="button" className="m-btn wide" onClick={onNew}>🚀 Launch another coin</button>}
  </div>;
}
