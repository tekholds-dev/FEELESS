import React from 'react';
import '../styles/familyOps.css';

// 🏙 SITE-4 · FAMILIA OPS: the family's own ops room, from the block's real reads only (familia-block → _fblock_reads: marginfi, Save,
// Phoenix, PumpSwap LP, Meteora, Kamino, LSTs, LP NFTs). Net in markets, what the family owes, how close the worst loan is to its liquidation
// line, and every built position as one row with its proof. Nothing is estimated: a building with no read shows no number.
const PROOF = { chain: 'on-chain account', api: "protocol's own API", token: 'token balance', nft: 'position NFT' };
const k$ = v => { const a = Math.abs(Number(v) || 0); return `${Number(v) < 0 ? '-' : ''}$${a >= 1e6 ? `${(a / 1e6).toFixed(2)}M` : a >= 1e3 ? `${(a / 1e3).toFixed(1)}K` : a.toFixed(2)}`; };

export function opsSums(bl) {
  const rows = (bl?.buildings || []).filter(b => b.state === 'built');
  const debt = rows.reduce((a, b) => a + (Number(b.debt) || 0), 0); const net = rows.reduce((a, b) => a + (Number(b.usd) || 0), 0);
  const worst = rows.filter(b => b.risk != null && b.debt > 0).sort((a, b) => b.risk - a.risk)[0] || null;
  return { rows, net, debt, worst, errands: rows.reduce((a, b) => a + (b.errands || []).length, 0) };
}

export function FamilyOps({ bl, onPick }) {
  if (!bl) return null;
  const s = opsSums(bl);
  if (!s.rows.length) return <section className="fop" data-testid="family-ops"><h4>FAMILIA OPS</h4><p className="fop-none">No building stands on a real position yet. Build one: it is read from the chain, never typed in.</p></section>;
  const r = s.worst?.risk; const tone = r == null ? '' : r >= 0.8 ? 'is-bad' : r >= 0.5 ? 'is-warn' : 'is-ok';
  return <section className="fop" data-testid="family-ops">
    <h4>FAMILIA OPS <small>your wallets' real positions, read live</small></h4>
    <div className="fop-kpis">
      <span style={{ '--i': 0 }} data-tip="What the positions are worth after their debt (live prices)"><em>NET</em><b className="m-num">{k$(s.net)}</b></span>
      <span style={{ '--i': 1 }} className={s.debt > 0 ? 'is-owe' : ''} data-tip="What the family has borrowed across its lending buildings"><em>OWED</em><b className="m-num">{k$(s.debt)}</b></span>
      <span style={{ '--i': 2 }} className={tone} data-tip={s.worst ? `${s.worst.name}: ${Math.round(r * 100)}% of the way to its liquidation line` : 'No loan with a liquidation line on the block'}><em>WORST LOAN</em><b className="m-num">{r == null ? '—' : `${Math.round(r * 100)}%`}</b>
        <i className="fop-meter"><u style={{ transform: `scaleX(${Math.min(1, r || 0)})` }} /></i></span>
      <span style={{ '--i': 3 }} className={s.errands ? 'is-warn' : ''} data-tip="Real-money errands waiting (re-center, claim, top up)"><em>ERRANDS</em><b className="m-num">{s.errands}</b></span>
    </div>
    <ul className="fop-rows">{s.rows.map((b, i) => <li key={b.key} style={{ '--i': i }}>
      <button type="button" onClick={() => onPick && onPick({ blk: b.key })} data-testid={`fop-${b.key}`}>
        <b>{b.name}</b>
        <span className="m-num">{b.usd != null ? k$(b.usd) : `${b.n || 1} pos`}</span>
        <span className={`m-num${b.debt > 0 ? ' is-owe' : ''}`}>{b.debt > 0 ? `owes ${k$(b.debt)}` : ''}</span>
        <small>{(b.errands || []).length ? `${b.errands.length} errand${b.errands.length > 1 ? 's' : ''} · ` : ''}{PROOF[b.proof] || b.proof || ''}</small>
      </button></li>)}</ul>
  </section>;
}
