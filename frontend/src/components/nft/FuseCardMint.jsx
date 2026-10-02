import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../../hooks/useWallet';
import { FuseCard } from '../FuseCard';
import { AuraPicker } from '../cards/MetaCard';

// HQ › NFTs › ⚛️ Fuse cards: each published Fuse can be minted ONCE as a 1/1 Metaplex Core card. Whoever holds the card
// (read on-chain at payout time) is paid that Fuse's creator cut — sell or gift the card and the income follows it.
const STEPS = [
  ['1', 'Create the collection', 'Once. Your owner wallet signs (~0.003 SOL rent). Holds every Fuse card.'],
  ['2', 'Mint a card', '1 of 1 per published Fuse, to its creator (or any wallet). ~0.003 SOL, you sign.'],
  ['3', 'Holder earns', 'Creator cut of every verified buy goes to the current holder. Paid in HQ › Published.'],
];

export function FuseCardMint({ call }) {
  const { wallet, provider, connect } = useWallet() || {};
  const [d, setD] = useState(null); const [busy, setBusy] = useState(''); const [to, setTo] = useState({});
  const load = () => call('/admin/fuses/cards').then(setD).catch(e => toast.error(e.message));
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const ready = wallet?.chain === 'solana' && provider;
  const createCol = async () => {
    if (!ready) { connect?.('solana'); return; }
    try {
      const { coreCreateCollection } = await import('../../lib/metaplexCore');
      const r = await coreCreateCollection({ provider, owner: wallet.address, name: 'FEELESS Fuse Cards', uri: `${d.site}/api/reputation/fuse-card/collection.json`, onStatus: setBusy });
      setBusy('Verifying on-chain…'); await call('/admin/fuses/card-collection', { method: 'POST', body: JSON.stringify({ signature: r.signature, collection: r.address }) });
      toast.success('Fuse Cards collection is live'); load();
    } catch (e) { toast.error(e.message); } finally { setBusy(''); }
  };
  const mint = async f => {
    if (!ready) { connect?.('solana'); return; }
    const owner = (to[f.id] || f.creator || wallet.address).trim();
    try {
      const { coreDrop } = await import('../../lib/metaplexCore');
      const [r] = await coreDrop({ provider, owner: wallet.address, collection: d.collection.address, name: `FUSE ${f.name}`.slice(0, 26), uriFor: () => `${d.site}/api/reputation/fuse-card/${f.id}.json`, recipients: [owner], start: 1, onStatus: setBusy });
      setBusy('Verifying on-chain…'); await call(`/admin/fuses/${f.id}/card`, { method: 'POST', body: JSON.stringify({ signature: r.signature, asset: r.assets[0].address }) });
      toast.success(`${f.name} card minted to ${owner.slice(0, 4)}…`); load();
    } catch (e) { toast.error(e.message); } finally { setBusy(''); }
  };
  const champ = f => ({ pools: f.legs.map(l => l.pairAddress), fitness: f.score.points, bornGen: 0, parts: { grade: f.score.grade, aprScore: Math.round(f.aprEst / 4), momentum24h: 0, calm: '—', feeDragPct: 0, impactLegs: 0 },
    legs: f.legs.map(l => ({ ...l, chainId: l.chainId || 'solana' })) });
  return <section className="m-card m-live fcm" data-testid="fuse-card-mint">
    <header><span className="m-label">⚛️ FUSE CARDS · NFT</span><h3>Mint the Fuse. Whoever holds it earns.</h3></header>
    <ol className="fx-flow">{STEPS.map(([n, t, s]) => <li key={n}><b>{n}</b><span>{t}<small>{s}</small></span></li>)}</ol>
    {busy && <div className="m-note"><b>WORKING</b><span>{busy}</span></div>}
    {!d ? <div className="fl-row is-ghost" /> : !d.collection ? <button type="button" className="m-btn primary m-go" disabled={Boolean(busy)} onClick={createCol} data-testid="fcm-collection">{ready ? '① Create Fuse Cards collection' : 'Connect owner wallet'}</button>
      : <p className="m-dim fcm-col">Collection <code>{d.collection.address.slice(0, 6)}…{d.collection.address.slice(-4)}</code> · live</p>}
    {d && <div className="fcm-grid">{d.rows.length ? d.rows.map(f => <article key={f.id} className="fcm-item">
      <FuseCard c={champ(f)} style="yield" rank={f.card ? 0 : 3} aura={f.aura || ''} />
      <details className="fcm-aura"><summary>✨ Aura: {f.aura || 'none'}</summary><AuraPicker value={f.aura} onChange={v => call(`/admin/fuses/${f.id}/aura`, { method: 'POST', body: JSON.stringify({ aura: v }) }).then(load).catch(e => toast.error(e.message))} /></details>
      <b className="fcm-name">{f.emoji} {f.name}</b>
      {f.card ? <small className="m-dim" data-tip="Read on-chain every 5 min — sell or gift the card and the cut follows it.">Holder <code>{String(f.payTo || '').slice(0, 4)}…{String(f.payTo || '').slice(-4)}</code> earns {(f.creatorBps || 0) / 100}% · owed ${f.stats?.creatorOwedUsd?.toFixed(2)}</small>
        : <><input className="m-input" placeholder={`Mint to (default creator ${String(f.creator || '').slice(0, 4)}…)`} value={to[f.id] || ''} onChange={e => setTo(x => ({ ...x, [f.id]: e.target.value }))} aria-label="Recipient wallet" />
          <button type="button" className="m-btn primary" disabled={!d.collection || Boolean(busy)} onClick={() => mint(f)} data-testid={`fcm-mint-${f.id}`}>② Mint 1/1 card</button></>}
    </article>) : <p className="m-dim">Publish a Fuse first (Fuse › Published), then mint its card here.</p>}</div>}
  </section>;
}
