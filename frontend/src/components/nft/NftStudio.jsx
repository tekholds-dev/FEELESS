import React, { useCallback, useEffect, useMemo, useState } from 'react';
import NumInput from '../NumInput';
import { toast } from 'sonner';
import { useWallet } from '../../hooks/useWallet';
import { apiUrl, errorText } from '../../lib/api';
import { MetaCard } from '../cards/MetaCard';

// HQ › NFTs: turn any FEELESS card into an NFT collection on Solana and drop it to wallets.
//   Metaplex Core — on-chain, your wallet signs (no key)      Crossmint — API minting (CROSSMINT_API_KEY)
//   Underdog — compressed NFTs via API (UNDERDOG_API_KEY)    Magic Eden / Tensor index Core collections on their own.
const PLATFORMS = [
  ['metaplex', 'Metaplex Core', 'On-chain standard. Your wallet signs; you own the collection outright. ~0.003 SOL per NFT.', 'Best for: the real thing, marketplaces'],
  ['crossmint', 'Crossmint', 'Minting API: FEELESS mints straight to wallets, no approvals per NFT. Paid with Crossmint credits.', 'Best for: big airdrops, no gas juggling'],
  ['underdog', 'Underdog', 'Compressed NFTs via API: fractions of a cent each at scale.', 'Best for: thousands of holders'],
];
const PNAME = Object.fromEntries(PLATFORMS.map(p => [p[0], p[1]]));

function links(c) {
  if (!c.address) return [];
  if (c.platform === 'metaplex') return [['Solscan', `https://solscan.io/account/${c.address}`], ['Metaplex explorer', `https://core.metaplex.com/explorer/collection/${c.address}`]];
  if (c.platform === 'crossmint') return [['Crossmint console', 'https://www.crossmint.com/console/collections']];
  return [['Underdog app', 'https://app.underdogprotocol.com']];
}
const minted = c => (c.drops || []).reduce((a, d) => a + (d.ok || []).length, 0);

export function NftStudio({ call }) {
  const { wallet, provider, connect } = useWallet() || {};
  const [home, setHome] = useState(null);
  const [cards, setCards] = useState([]);
  const [open, setOpen] = useState(null);      // collection id
  const [make, setMake] = useState(null);      // wizard state
  const load = useCallback(() => call('/admin/nft').then(setHome).catch(e => toast.error(errorText(e))), [call]);
  useEffect(() => { load(); fetch(apiUrl('/api/reputation/cards')).then(r => r.json()).then(d => setCards(d.cards || [])).catch(() => {}); }, [load]);
  const cardOf = key => cards.find(c => c.key === key);
  if (!home) return <p className="cc-empty">Opening the studio…</p>;
  const col = home.collections.find(c => c.id === open);
  return <section className="nft-studio m-stack" data-testid="nft-studio">
    <div className="m-card is-hot m-row cs-bar">
      <div className="m-stack"><span className="m-label">NFT STUDIO <em>your cards → Solana collections</em></span>
        <span className="m-dim">Pick a card, choose a platform, create the collection, then drop it to any wallets or to everyone who holds that card.</span></div>
      <div className="m-row">{PLATFORMS.map(([k, n]) => <span key={k} className={`m-chip ${home.platforms[k]?.ready ? 'ok' : 'warn'}`}>{home.platforms[k]?.ready ? '●' : '○'} {n}</span>)}</div>
      <button type="button" className="m-btn primary" onClick={() => { setMake({ step: 1 }); setOpen(null); }} data-testid="nft-new">+ New collection</button>
    </div>

    {make && <Wizard call={call} cards={cards} platforms={home.platforms} wallet={wallet} provider={provider} connect={connect} state={make} setState={setMake}
      onDone={c => { setMake(null); load(); setOpen(c.id); }} />}

    {!make && !home.collections.length && <p className="m-dim">No collections yet. Your badge and season cards are ready to become NFTs.</p>}
    {!make && home.collections.length > 0 && <div className="nft-grid">{home.collections.map(c => <button key={c.id} type="button" className={`m-card nft-tile ${open === c.id ? 'active' : ''}`} onClick={() => setOpen(open === c.id ? null : c.id)}>
      {cardOf(c.cardKey) ? <MetaCard card={cardOf(c.cardKey)} size="sm" /> : <img src={apiUrl(c.image)} alt="" />}
      <span className="m-stack"><b>{c.name}</b><span className="m-chip">{PNAME[c.platform]}</span><small className="m-dim">{c.status === 'live' ? `${minted(c)} minted${c.supply ? ` / ${c.supply}` : ''}` : 'draft: not on-chain yet'}</small></span></button>)}</div>}

    {!make && col && <Collection c={col} card={cardOf(col.cardKey)} call={call} wallet={wallet} provider={provider} connect={connect} onChange={load} />}
  </section>;
}

function Wizard({ call, cards, platforms, wallet, provider, connect, state, setState, onDone }) {
  const [busy, setBusy] = useState('');
  const [f, setF] = useState({ name: '', symbol: '', description: '', supply: '', royaltyPct: '5', platform: 'metaplex' });
  const card = cards.find(c => c.key === state.cardKey);
  const pick = c => { setState(s => ({ ...s, cardKey: c.key, step: 2 })); setF(x => ({ ...x, name: c.title, symbol: c.title.replace(/[^A-Za-z0-9]/g, '').slice(0, 6).toUpperCase(), description: c.lore || '' })); };
  const create = async () => {
    try {
      setBusy('Rendering the card image…');
      const { uploadCardImage } = await import('../../lib/cardImage');
      const image = await uploadCardImage(card);
      setBusy('Creating the collection…');
      let c = await call('/admin/nft/collections', { method: 'POST', body: JSON.stringify({ ...f, image, cardKey: card.key }) });
      if (c.platform === 'metaplex') {
        if (wallet?.chain !== 'solana') { await connect?.('solana'); throw new Error('Connect your Solana wallet, then press Create again.'); }
        const { coreCreateCollection } = await import('../../lib/metaplexCore');
        const r = await coreCreateCollection({ provider, owner: wallet.address, name: c.name, uri: c.uri, royaltyBps: c.royaltyBps, onStatus: setBusy });
        c = await call(`/admin/nft/collections/${c.id}/onchain`, { method: 'POST', body: JSON.stringify({ address: r.address, signature: r.signature }) });
      }
      toast.success(`${c.name} is live on ${PNAME[c.platform]}.`); onDone(c);
    } catch (e) { toast.error(e.code === 4001 ? 'Declined in your wallet. Nothing was created on-chain.' : errorText(e)); } finally { setBusy(''); }
  };
  return <div className="m-card m-stack m-pop" data-testid="nft-wizard">
    <ol className="cl-steps">{['Card', 'Details', 'Platform', 'Create'].map((t, i) => <li key={t} className={i + 1 < state.step ? 'done' : i + 1 === state.step ? 'now' : ''}><b>{i + 1}</b>{t}</li>)}</ol>
    {state.step === 1 && <><span className="m-label">1 · WHICH CARD BECOMES THE NFT?</span>
      <div className="cs-grid m-scroll">{cards.map(c => <button key={c.key} type="button" className="mc-pick" onClick={() => pick(c)} title={c.title}><MetaCard card={c} size="sm" /></button>)}</div></>}
    {state.step >= 2 && card && <div className="nft-wiz">
      <MetaCard card={{ ...card, title: f.name || card.title, motion: 'alive' }} size="md" />
      <div className="m-stack">
        {state.step === 2 && <><span className="m-label">2 · DETAILS</span>
          <div className="m-grid"><label className="m-field"><span>Collection name</span><input className="m-input" maxLength={32} value={f.name} onChange={e => setF(x => ({ ...x, name: e.target.value }))} /></label>
            <label className="m-field"><span>Symbol</span><input className="m-input" maxLength={10} value={f.symbol} onChange={e => setF(x => ({ ...x, symbol: e.target.value.toUpperCase() }))} /></label>
            <label className="m-field"><span>Max supply (0 = open)</span><NumInput className="m-input" inputMode="numeric" value={f.supply} onChange={e => setF(x => ({ ...x, supply: e.target.value.replace(/\D/g, '') }))} placeholder="0" /></label>
            <label className="m-field"><span>Royalties %</span><NumInput className="m-input" inputMode="decimal" value={f.royaltyPct} onChange={e => setF(x => ({ ...x, royaltyPct: e.target.value.replace(/[^0-9.]/g, '') }))} /></label></div>
          <label className="m-field"><span>Description</span><textarea className="m-input" rows={3} maxLength={500} value={f.description} onChange={e => setF(x => ({ ...x, description: e.target.value }))} /></label>
          <div className="m-row"><button type="button" className="m-btn" onClick={() => setState(s => ({ ...s, step: 1 }))}>← Card</button><button type="button" className="m-btn primary" disabled={f.name.trim().length < 2 || !f.symbol} onClick={() => setState(s => ({ ...s, step: 3 }))}>Platform →</button></div></>}
        {state.step === 3 && <><span className="m-label">3 · WHERE DOES IT LIVE?</span>
          <div className="cl-rails">{PLATFORMS.map(([k, n, what, best]) => { const ok = platforms[k]?.ready;
            return <button key={k} type="button" role="radio" aria-checked={f.platform === k} disabled={!ok} className={`cl-rail ${f.platform === k ? 'active' : ''}`} onClick={() => setF(x => ({ ...x, platform: k }))} data-testid={`nft-platform-${k}`}>
              <span className="cl-rail-top"><b>{n}</b><em>{ok ? (platforms[k].env ? `ready · ${platforms[k].env}` : 'ready') : 'not connected'}</em></span><span>{what}</span><small>{ok ? best : platforms[k]?.how}</small></button>; })}</div>
          <div className="m-row"><button type="button" className="m-btn" onClick={() => setState(s => ({ ...s, step: 2 }))}>← Details</button><button type="button" className="m-btn primary" onClick={() => setState(s => ({ ...s, step: 4 }))}>Review →</button></div></>}
        {state.step === 4 && <><span className="m-label">4 · CREATE</span>
          <dl className="m-kv"><dt>Card</dt><dd>{card.title}</dd><dt>Collection</dt><dd>{f.name} (${f.symbol})</dd><dt>Platform</dt><dd>{PNAME[f.platform]}</dd>
            <dt>Supply</dt><dd>{Number(f.supply) || 'open'}</dd><dt>Royalties</dt><dd>{Number(f.royaltyPct) || 0}%</dd>
            <dt>Cost</dt><dd>{f.platform === 'metaplex' ? '≈ 0.003 SOL rent + network fee, signed by your wallet' : `Billed by ${PNAME[f.platform]} (API credits)`}</dd></dl>
          <div className="m-note"><b>What happens</b>The card is rendered to an image, its metadata is hosted on your site, then the collection is created on {PNAME[f.platform]}.{f.platform === 'metaplex' ? ' Your wallet signs once.' : ''}</div>
          <div className="m-row"><button type="button" className="m-btn" disabled={!!busy} onClick={() => setState(s => ({ ...s, step: 3 }))}>← Platform</button>
            <button type="button" className="m-btn primary" disabled={!!busy} onClick={create} data-testid="nft-create">{busy || `Create on ${PNAME[f.platform]}`}</button></div></>}
        <button type="button" className="m-btn" onClick={() => setState(null)}>Cancel</button>
      </div></div>}
  </div>;
}

function Collection({ c, card, call, wallet, provider, connect, onChange }) {
  const [to, setTo] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState('');
  const list = useMemo(() => [...new Set(to.split(/[\s,;]+/).filter(a => /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(a)))], [to]);
  const phrase = `DROP ${list.length}`;
  const holders = async () => { try { const d = await call(`/admin/nft/holders/${c.cardKey}`); setTo(d.wallets.join('\n')); toast.success(`${d.wallets.length} holders of this card loaded.`); } catch (e) { toast.error(errorText(e)); } };
  const drop = async () => {
    setBusy('Dropping…');
    try {
      if (c.platform === 'metaplex') {
        if (wallet?.chain !== 'solana') { await connect?.('solana'); throw new Error('Connect your Solana wallet, then drop again.'); }
        const { coreDrop } = await import('../../lib/metaplexCore');
        const base = c.uri.replace(/\.json$/, '');
        const out = await coreDrop({ provider, owner: wallet.address, collection: c.address, name: c.name, uriFor: n => `${base}-${n}.json`, recipients: list, start: minted(c) + 1, onStatus: setBusy });
        for (const r of out) await call(`/admin/nft/collections/${c.id}/onchain`, { method: 'POST', body: JSON.stringify({ address: c.address, signature: r.signature, assets: r.assets }) });
        toast.success(`Minted ${list.length} NFTs on-chain.`);
      } else {
        const r = await call(`/admin/nft/collections/${c.id}/drop`, { method: 'POST', body: JSON.stringify({ to: list, confirm: confirm.trim() }) });
        if (r.failed?.length) toast.error(`${r.minted} minted, ${r.failed.length} failed.`); else toast.success(`${PNAME[c.platform]} minted ${r.minted} NFTs.`);
      }
      setTo(''); setConfirm(''); onChange();
    } catch (e) { toast.error(e.code === 4001 ? 'Declined in your wallet.' : errorText(e)); } finally { setBusy(''); }
  };
  return <div className="m-card is-hot nft-detail m-pop" data-testid="nft-collection">
    <div className="cs-preview">{card ? <MetaCard card={{ ...card, title: c.name, motion: 'alive' }} size="lg" interactive /> : <img src={apiUrl(c.image)} alt="" className="nft-img" />}</div>
    <div className="m-stack">
      <div className="m-row"><span className="m-label">{c.name} <em>${c.symbol}</em></span><span className={`m-chip ${c.status === 'live' ? 'ok' : 'warn'}`}>{c.status === 'live' ? '● live' : 'draft'}</span><span className="m-chip">{PNAME[c.platform]}</span></div>
      <dl className="m-kv"><dt>Address</dt><dd><code>{c.address || 'not created yet'}</code></dd><dt>Minted</dt><dd>{minted(c)}{c.supply ? ` / ${c.supply}` : ''}</dd><dt>Royalties</dt><dd>{c.royaltyBps / 100}%</dd><dt>Metadata</dt><dd><a href={c.uri} target="_blank" rel="noopener noreferrer">{c.uri}</a></dd></dl>
      <div className="m-row">{links(c).map(([l, u]) => <a key={l} className="m-btn" href={u} target="_blank" rel="noopener noreferrer">{l} ↗</a>)}</div>
      {c.platform === 'metaplex' && c.status === 'live' && <small className="m-dim">Magic Eden and Tensor index Metaplex Core collections automatically once NFTs exist; to get a verified collection page, submit it on their creator forms.</small>}
      {c.status === 'live' && <div className="m-card m-stack"><span className="m-label">DROP <em>one NFT per wallet</em></span>
        <textarea className="m-input" rows={4} value={to} onChange={e => setTo(e.target.value)} placeholder="Wallet addresses, one per line" aria-label="Wallets to drop to" />
        <div className="m-row"><button type="button" className="m-btn" onClick={holders} disabled={!c.cardKey}>Load everyone holding this card</button><span className="m-dim">{list.length} wallet{list.length === 1 ? '' : 's'}</span></div>
        {c.platform !== 'metaplex' && list.length > 0 && <label className="m-field"><span>Type {phrase} to confirm</span><input className="m-input" value={confirm} onChange={e => setConfirm(e.target.value)} placeholder={phrase} /></label>}
        <button type="button" className="m-btn primary" disabled={!!busy || !list.length || (c.platform !== 'metaplex' && confirm.trim() !== phrase)} onClick={drop} data-testid="nft-drop">{busy || (c.platform === 'metaplex' ? `Mint ${list.length} · ${Math.ceil(list.length / 3)} wallet approval${Math.ceil(list.length / 3) === 1 ? '' : 's'}` : `Drop ${list.length} via ${PNAME[c.platform]}`)}</button></div>}
    </div>
  </div>;
}
