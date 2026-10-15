import React, { useCallback, useEffect, useState } from 'react';
import NumInput from '../NumInput';
import { toast } from 'sonner';
import { CopyBtn } from '../CopyBtn';
import { TokenAvatar } from '../terminal/MarketPrimitives';
import '../../styles/circleCoins.css';

// Circle ties networks to the key: TEST keys only reach testnets, LIVE keys only mainnets.
const CHAINS = { test: [['SOL-DEVNET', 'Solana devnet'], ['BASE-SEPOLIA', 'Base Sepolia'], ['ETH-SEPOLIA', 'Ethereum Sepolia'], ['ARB-SEPOLIA', 'Arbitrum Sepolia']], live: [['SOL', 'Solana mainnet'], ['BASE', 'Base mainnet'], ['ETH', 'Ethereum mainnet'], ['ARB', 'Arbitrum mainnet'], ['MATIC', 'Polygon mainnet']] };

// Creator-only: wallets created and held by Circle (keys never touch FEELESS), listed with balances.
export function CircleWallets({ call }) {
  const [status, setStatus] = useState(null);
  const [wallets, setWallets] = useState([]);
  const [f, setF] = useState({ blockchain: '', name: '' });
  const [meta, setMeta] = useState({});
  const [dests, setDests] = useState([]);
  const chains = CHAINS[status?.testnet ? 'test' : 'live'];
  const blockchain = chains.some(([k]) => k === f.blockchain) ? f.blockchain : chains[0][0];
  const [busy, setBusy] = useState(false);
  const [fuseAddr, setFuseAddr] = useState(null);
  useEffect(() => { call('/admin/fuse-wallet').then(d => setFuseAddr(d?.cfg?.address || null)).catch(() => {}); }, [call]);   // which Circle wallet the keeper trades from
  const load = useCallback(() => {
    call('/admin/circle/status').then(setStatus).catch(e => setStatus({ configured: false, reason: e.message }));
    call('/admin/circle/wallets').then(d => setWallets(d.wallets || [])).catch(() => {});
    call('/admin/circle/meta').then(setMeta).catch(() => {});
    call('/admin/circle/destinations').then(d => setDests(d.destinations || [])).catch(() => {});
  }, [call]);
  useEffect(() => { load(); }, [load]);
  const create = async () => {
    const main = !blockchain.includes('-');
    if (main && !window.confirm(`Create a MAINNET ${blockchain} wallet? Real funds sent to it are real.`)) return;
    setBusy(true);
    try { await call('/admin/circle/wallets', { method: 'POST', body: JSON.stringify({ blockchain, name: f.name || 'Creator wallet' }) }); toast.success('Wallet created'); setF(x => ({ ...x, name: '' })); load(); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  return <div className="cc-block circle-wallets"><h4>Creator wallets <small className="chain-tag">Circle · {status?.testnet ? 'TESTNET' : 'LIVE'}</small></h4>
    <p className="cc-note"><b>Gas funding:</b> Circle holds the keys, but these are normal on-chain wallets. Before an outbound transfer or contract call, fund each wallet with that network's native gas token (SOL on Solana, ETH on Base/Ethereum/Arbitrum, POL on Polygon). Receiving assets does not require the wallet to hold gas. Gas is separate from FEELESS/Jupiter platform fees.</p>
    {!status?.configured ? <div className="cc-empty"><p><b>Not active yet:</b> {status?.reason || 'checking…'}</p>
      <ol><li>Get an API key at <code>console.circle.com</code> (API &amp; Client Keys; a <code>TEST_</code> key = testnet) and add <code>CIRCLE_API_KEY=…</code> to <code>backend/.env</code>.</li><li>In the project folder run <code>cd circle &amp;&amp; npm install &amp;&amp; node setup.mjs</code> (once). It saves the secret to <code>backend/.env</code> for you.</li><li>Back up the recovery file in <code>~/.circle</code> (password manager). Without it a lost secret can't be recovered.</li><li>Run <code>bash scripts/start-backend.sh</code> (starts the wallet service too), then Re-check.</li></ol>
      <button type="button" className="btn-outline" onClick={load}>Re-check</button></div> : <>
      <div className="cc-toolbar"><select value={blockchain} onChange={e => setF(x => ({ ...x, blockchain: e.target.value }))}>{chains.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select><input placeholder="Wallet name (e.g. Treasury ops)" value={f.name} maxLength={40} onChange={e => setF(x => ({ ...x, name: e.target.value }))} /><button type="button" className="btn-primary" disabled={busy} onClick={create}>{busy ? 'Creating…' : 'Create wallet'}</button></div>
      <div className="cw-list">{!wallets.length ? <small className="cc-empty">No wallets yet.</small> : wallets.map(w => <CircleRow key={w.id} w={w} meta={meta[w.id]} call={call} onSaved={load} dests={dests} fuse={!!fuseAddr && w.address === fuseAddr} />)}</div>
      <small className="cc-empty">Keys are held by Circle and never touch FEELESS. Recovery lives in your ~/.circle recovery file. Check the estimated network fee and native-token balance before every outbound transaction.</small>
    </>}
  </div>;
}

// One Circle wallet: rename + describe it, and open its mini HQ to move funds.
function CircleRow({ w, meta, call, onSaved, dests, fuse }) {
  const [mode, setMode] = useState('');
  const [m, setM] = useState({ name: meta?.name || w.name || '', description: meta?.description || '' });
  const [busy, setBusy] = useState(false);
  const save = async () => { setBusy(true); try { await call(`/admin/circle/wallets/${w.id}`, { method: 'PUT', body: JSON.stringify(m) }); toast.success('Saved.'); setMode(''); onSaved?.(); } catch (e) { toast.error(e.message); } finally { setBusy(false); } };
  return <div className={`cw-row cw-row-x ${mode === 'move' ? 'is-open' : ''}`}>
    <div className="cw-top"><b>{meta?.name || w.name || 'Wallet'}</b><span className="chain-tag">{w.blockchain}</span><code>{w.address?.slice(0, 6)}…{w.address?.slice(-4)}</code><CopyBtn value={w.address} /><CoinChips w={w} />
      <button type="button" className="m-btn" onClick={() => setMode(mode === 'edit' ? '' : 'edit')}>✎ Edit</button>
      <button type="button" className={`m-btn ${mode === 'move' ? 'primary' : ''}`} aria-expanded={mode === 'move'} onClick={() => setMode(mode === 'move' ? '' : 'move')} data-testid={`circle-move-${w.id}`}>⇄ Move {mode === 'move' ? '▴' : '▾'}</button></div>
    {meta?.description && mode !== 'edit' && <small className="cw-desc">{meta.description}</small>}
    {mode === 'edit' && <div className="m-row m-pop"><input className="m-input" style={{ flex: 1 }} maxLength={40} placeholder="Name" value={m.name} onChange={e => setM(x => ({ ...x, name: e.target.value }))} /><input className="m-input" style={{ flex: 2 }} maxLength={200} placeholder="What this wallet is for" value={m.description} onChange={e => setM(x => ({ ...x, description: e.target.value }))} /><button type="button" className="m-btn primary" disabled={busy || m.name.length < 2} onClick={save}>{busy ? 'Saving…' : 'Save'}</button></div>}
    {fuse ? <FuseClean call={call} onDone={onSaved} /> : null}
    {mode === 'move' && <CircleMove w={w} call={call} dests={dests} onDone={() => { setMode(''); onSaved?.(); }} />}
  </div>;
}

// 🪙 every coin in the wallet with its REAL logo (DexScreener → CDN → FEELESS cache, TokenAvatar) and what it is worth now
const money = v => (v == null ? '—' : v >= 1 ? `$${v.toFixed(2)}` : v >= 0.01 ? `$${v.toFixed(3)}` : '<$0.01');
export function CoinChips({ w }) {
  const bs = (w.balances || []).filter(b => Number(b.amount) > 0);
  if (!bs.length) return <em className="cwc-none">{w.balanceError ? 'balance unavailable' : 'empty'}</em>;
  const total = bs.reduce((a, b) => a + (Number(b.usd) || 0), 0);
  return <span className="cwc" data-testid="circle-coins">{bs.map(b => <span key={`${b.mint || b.symbol}`} className={`cwc-c ${b.usd != null && b.usd < 0.05 ? 'is-dust' : ''}`} data-tip={`${Number(b.amount).toLocaleString()} ${b.symbol}${b.usd != null ? ` · ${money(b.usd)}` : ' · no price'}${b.mint ? ` · ${b.mint}` : ''}`}>
    {b.mint ? <TokenAvatar pair={{ chainId: 'solana', baseToken: { address: b.mint, symbol: b.symbol } }} size={18} /> : <i className="cwc-sol" aria-hidden>◎</i>}
    <b>{b.symbol}</b><small>{money(b.usd)}</small></span>)}
    {total > 0 ? <em className="cwc-total">≈ {money(total)}</em> : null}</span>;
}

// 🧹 ONE CLICK FOR THE FUSE WALLET'S LEFTOVERS (owner, 2026-10-15: "a way to burn / sell dead tokens"): 🔍 Check reads both lists — coins worth
// under 5¢ (or written off) = BURN + CLOSE (rent back, one transaction) and coins the cards no longer hold = SELL back to SOL (the keeper
// sells them into card cash). 🧹 Clean runs the burn first, then queues the sales. Nothing a card holds is ever touched; nothing moves before you click.
export function FuseClean({ call, onDone }) {
  const [plan, setPlan] = useState(null); const [busy, setBusy] = useState(false);
  const check = async () => {
    setBusy(true);
    try {
      const [dust, fw] = await Promise.all([call('/admin/fuse-wallet/close-dust', { method: 'POST', body: JSON.stringify({ confirm: false }) }), call('/admin/fuse-wallet')]);
      const burn = new Set((dust?.accounts || []).map(a => a.mint));
      setPlan({ dust, sell: (fw?.recoverable || []).filter(r => !burn.has(r.mint)) });
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const clean = async () => {
    setBusy(true); const done = [];
    try {
      if (plan.dust?.accounts?.length) { const r = await call('/admin/fuse-wallet/close-dust', { method: 'POST', body: JSON.stringify({ confirm: true }) }); done.push(`🔥 ${r.accounts.length} burned + closed (${money(r.rentUsd)} rent back)`); }
      for (const tpl of [...new Set(plan.sell.map(r => r.card))]) {
        try { const r = await call('/admin/fuse-wallet/recover-sell-all', { method: 'POST', body: JSON.stringify({ tpl }) }); done.push(`↩ ${r.queued} queued to sell`); }
        catch (e) { done.push(`↩ ${e.message}`); }
      }
      toast.success(done.join(' · ') || 'Nothing to clean.'); setPlan(null); onDone?.();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const nb = plan?.dust?.accounts?.length || 0; const ns = plan?.sell?.length || 0;
  return <div className="cwc-clean" data-testid="fuse-clean">
    {!plan ? <><span>🧹 Leftover coins in the keeper wallet — sell what is worth something, burn + close the dust for its rent.</span>
      <button type="button" className="m-btn" disabled={busy} onClick={check} data-testid="fuse-clean-check">{busy ? 'Checking…' : '🔍 Check'}</button></>
      : <><span data-testid="fuse-clean-plan">{ns ? `↩ sell ${ns}: ${plan.sell.map(r => `$${r.symbol}`).join(' ')}` : 'nothing to sell'} · {nb ? `🔥 burn + close ${nb} (${money(plan.dust.dustUsd)} of dust → ${money(plan.dust.rentUsd)} rent back)` : 'no dust to burn'}</span>
        {ns || nb ? <button type="button" className="m-btn m-go" disabled={busy} onClick={clean} data-testid="fuse-clean-go">{busy ? 'Cleaning…' : '🧹 Clean'}</button> : null}
        <button type="button" className="m-btn" disabled={busy} onClick={() => setPlan(null)}>✕</button></>}
  </div>;
}

// Mini HQ for one Circle wallet: moves funds ONLY to HQ wallets or wallets you saved
// (the server enforces the same list). Pick coin → destination → amount → type the last 4 → Circle signs.
export function CircleMove({ w, call, dests, onDone }) {
  const bals = (w.balances || []).filter(b => Number(b.amount) > 0 && b.tokenId); // chain fallback proves funds, but only Circle's token id may be sent
  const [tokenId, setTokenId] = useState(bals[0]?.tokenId || '');
  const [to, setTo] = useState('');
  const [amount, setAmount] = useState('');
  const [confirm, setConfirm] = useState('');
  const [add, setAdd] = useState(null);
  const [list, setList] = useState(dests || []);
  const [busy, setBusy] = useState(false);
  useEffect(() => { setList(dests || []); }, [dests]);
  const sol = String(w.blockchain || '').toUpperCase().startsWith('SOL');
  const options = list.filter(d => d.address !== w.address && (d.address.startsWith('0x') ? !sol : sol));
  const bal = bals.find(b => b.tokenId === tokenId);
  const dest = options.find(d => d.address === to);
  const amt = Number(amount) || 0;
  const over = bal && amt > Number(bal.amount);
  const saveDest = async () => {
    try { const r = await call('/admin/circle/destinations', { method: 'POST', body: JSON.stringify(add) }); const saved = r.saved.find(x => x.address === add.address); setList(l => [...l.filter(x => x.address !== add.address), { ...saved, kind: 'saved' }]); setTo(add.address); setAdd(null); toast.success('Wallet saved to this list.'); }
    catch (e) { toast.error(e.message); }
  };
  const send = async () => {
    setBusy(true);
    try { const r = await call('/admin/circle/transfer', { method: 'POST', body: JSON.stringify({ walletId: w.id, tokenId, to, amount: String(amount), confirm }) }); toast.success(`Circle is sending ${amount} ${bal?.symbol} to ${dest?.label || 'wallet'} (${r.state || 'submitted'}).`); onDone?.(); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  if (!bals.length) return <div className="m-note warn m-pop"><b>Empty wallet</b>Fund it first: send {sol ? 'SOL' : 'the network’s gas token'} to <code>{w.address}</code>.</div>;
  const groups = ['owner', 'admin', 'fees', 'reserve', 'pool', 'route', 'circle', 'saved'];
  const GROUP = { owner: '👑 Owner', admin: '🛡 Admin', fees: '💸 Fees', reserve: '🏆 Reserve', pool: '🎖 Pool', route: '🏦 Treasury', circle: '◎ Circle', saved: '📌 Saved' };
  return <div className="m-card is-hot m-pop circle-move" data-testid="circle-move">
    <div className="m-label">MOVE FROM {String(w.name || 'CIRCLE').toUpperCase()} <em>HQ wallets + saved only</em></div>
    <div className="m-row"><span className="m-dim">Coin</span><div className="m-seg">{bals.map(b => <button key={b.tokenId} type="button" className={tokenId === b.tokenId ? 'active' : ''} onClick={() => setTokenId(b.tokenId)}>{b.symbol} · {Number(b.amount).toLocaleString(undefined, { maximumFractionDigits: 4 })}</button>)}</div></div>
    <div className="cm-dests m-scroll" role="listbox" aria-label="Destination">{groups.map(g => options.filter(d => d.kind === g)).filter(x => x.length).map(ds => <div key={ds[0].kind} className="cm-group"><small>{GROUP[ds[0].kind]}</small>
      {ds.map(d => <button key={d.address} type="button" role="option" aria-selected={to === d.address} className={to === d.address ? 'active' : ''} onClick={() => { setTo(d.address); setConfirm(''); }}><b>{d.label}</b><code>{d.address.slice(0, 4)}…{d.address.slice(-4)}</code></button>)}</div>)}
      {!options.length && <p className="m-dim">No HQ wallets on this network yet. Save one below.</p>}</div>
    {add ? <div className="m-row"><input className="m-input" style={{ flex: 2 }} placeholder="Wallet address" value={add.address} onChange={e => setAdd(a => ({ ...a, address: e.target.value.trim() }))} /><input className="m-input" style={{ flex: 1 }} placeholder="Label (e.g. Cold wallet)" maxLength={40} value={add.label} onChange={e => setAdd(a => ({ ...a, label: e.target.value }))} /><button type="button" className="m-btn primary" disabled={add.address.length < 32} onClick={saveDest}>Save</button><button type="button" className="m-btn" onClick={() => setAdd(null)}>Cancel</button></div>
      : <button type="button" className="m-btn" onClick={() => setAdd({ address: '', label: '' })}>+ Save another wallet</button>}
    {to && <div className="m-stack">
      <div className="m-row"><NumInput className="m-input" style={{ flex: 1 }} inputMode="decimal" placeholder={`Amount (${bal?.symbol})`} value={amount} onChange={e => setAmount(e.target.value.replace(/[^0-9.]/g, ''))} />
        <div className="m-seg">{[25, 50, 100].map(p => <button key={p} type="button" onClick={() => setAmount(String(Math.floor(Number(bal?.amount || 0) * p / 100 * 1e6) / 1e6))}>{p === 100 ? 'MAX' : `${p}%`}</button>)}</div></div>
      {sol && bal?.symbol === 'SOL' && amt > 0 && Number(bal.amount) - amt < 0.003 && <small className="m-neg">Leave ~0.003 SOL for Circle's network fee, or the send fails.</small>}
      <div className="m-note row"><span><b>Review</b>{amount || 0} {bal?.symbol} → {dest?.label} <code>{to}</code></span>
        <input className="m-input" style={{ width: 120 }} maxLength={4} placeholder={`type ${to.slice(-4)}`} value={confirm} onChange={e => setConfirm(e.target.value)} aria-label="Type the last 4 characters of the destination" /></div>
      <button type="button" className="m-btn primary wide" disabled={busy || !amt || over || confirm !== to.slice(-4)} onClick={send} data-testid="circle-move-send">{busy ? 'Circle is signing…' : over ? 'More than the balance' : `Move ${amount || 0} ${bal?.symbol}`}</button></div>}
  </div>;
}
