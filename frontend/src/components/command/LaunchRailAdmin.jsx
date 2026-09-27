import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../../hooks/useWallet';
import { RAIL_DEFAULTS, createLaunchRail, fetchLaunchRail } from '../../lib/launchRail';
import { CopyBtn } from '../CopyBtn';

const FIELDS = [
  ['initialMarketCap', 'Opening market cap (SOL)', 'Where the curve starts. 30 SOL ≈ pump.fun-style low open.'],
  ['migrationMarketCap', 'Graduation market cap (SOL)', 'When reached, liquidity moves to a Meteora DAMM v2 pool automatically.'],
  ['startingFeeBps', 'Launch fee (bps)', 'Anti-snipe: first-block buyers pay this (5000 = 50%). Decays fast.'],
  ['endingFeeBps', 'Normal fee (bps)', 'Fee after the decay window (100 = 1%).'],
  ['feeDecayMin', 'Anti-snipe window (min)', 'How long the launch fee takes to fall to normal.'],
  ['creatorFeePct', 'Creator share of fees (%)', 'The rest goes to the FEELESS fee claimer below.'],
  ['lockedLpPct', 'Liquidity locked forever (%)', 'Share of graduated LP nobody can withdraw. 100 = unruggable.'],
  ['supply', 'Token supply', 'Fixed; mint authority is revoked at creation.'],
];

// The order the site owner hooks things up in. Status comes from the server (presence only).
function SetupGuide({ keys, rail, routes }) {
  const has = k => keys?.find(x => x.key === k)?.set;
  const steps = [
    ['Solana RPC', has('SOLANA_RPC_URL'), 'Helius key in backend/.env as SOLANA_RPC_URL. Powers reads, forensics and the wallet relay.'],
    ['Price + chart data', has('CODEX_API_KEY') && has('JUPITER_API_KEY'), 'CODEX_API_KEY and JUPITER_API_KEY in backend/.env.'],
    ['Public site URL', has('PUBLIC_SITE_URL'), 'PUBLIC_SITE_URL=https://your-domain in backend/.env. New coins\' name + image are served from here.'],
    ['Owner wallets', has('FEELESS_ADMIN_WALLETS'), 'FEELESS_ADMIN_WALLETS=addr1,addr2 — who can open this center. Use a hardware or multisig wallet.'],
    ['Fee claimer / treasury', routes, 'Treasury tab → set where earnings go. A Squads multisig vault is safest.'],
    ['FEELESS launch config', rail?.ready, 'Below: one signed transaction from the owner wallet (~0.01 SOL rent). After this, anyone can launch.'],
    ['Lock the API to your domain', has('ALLOWED_ORIGINS'), 'ALLOWED_ORIGINS=https://your-domain before going public.'],
  ];
  const done = steps.filter(s => s[1]).length;
  return <div className="cc-block setup-guide"><h4>Hook-up steps <em>{done}/{steps.length}</em></h4>
    <ol>{steps.map(([t, ok, how], i) => <li key={t} className={ok ? 'ok' : ''}><i>{ok ? '✓' : i + 1}</i><div><b>{t}</b><small>{how}</small></div></li>)}</ol>
    <small className="cc-empty">Restart the backend after editing .env. Keys are never shown here — only whether they are set.</small>
  </div>;
}

export function LaunchRailAdmin({ call, isOwner }) {
  const { wallet, provider, connect } = useWallet() || {};
  const [rail, setRail] = useState(null);
  const [keys, setKeys] = useState(null);
  const [routes, setRoutes] = useState(false);
  const [p, setP] = useState(RAIL_DEFAULTS);
  const [claimer, setClaimer] = useState('');
  const [status, setStatus] = useState('');
  const load = useCallback(() => {
    fetchLaunchRail().then(setRail);
    call('/admin/setup').then(d => setKeys(d.keys)).catch(() => setKeys([]));
    call('/admin/treasury/routes').then(d => { setRoutes(!!d.routes?.length); const sol = d.routes?.find(r => !r.address.startsWith('0x'))?.address; if (sol) setClaimer(c => c || sol); }).catch(() => {});
  }, [call]);
  useEffect(load, [load]);
  const create = async () => {
    try {
      if (!wallet?.address || wallet.chain !== 'solana' || !provider?.signTransaction) { await connect?.('solana'); return; }
      const fc = claimer.trim() || wallet.address;
      setStatus('Building and dry-running the config…');
      const r = await createLaunchRail({ provider, owner: wallet.address, feeClaimer: fc, params: p, onStatus: setStatus });
      setStatus('Saving…');
      await call('/admin/launch-rail', { method: 'PUT', body: JSON.stringify({ config: r.config, feeClaimer: fc, params: p }) });
      toast.success('FEELESS launch rail is live');
      setStatus(''); load();
    } catch (e) { setStatus(''); toast.error(e.message || 'Could not create the launch config'); }
  };
  return <section className="cc-panel launch-rail-admin">
    <SetupGuide keys={keys} rail={rail} routes={routes} />
    <div className="cc-block"><h4>FEELESS launch config {rail?.ready && <span className="pill-ok">LIVE</span>}</h4>
      {rail?.ready ? <div className="rail-live">
        <p>Every FEELESS launch uses this on-chain config. Fees go to <code>{rail.feeClaimer.slice(0, 4)}…{rail.feeClaimer.slice(-4)}</code><CopyBtn value={rail.feeClaimer} profile />.</p>
        <div className="rail-kv">{FIELDS.map(([k, l]) => <span key={k}><small>{l}</small><b>{Number(rail.params?.[k] ?? RAIL_DEFAULTS[k]).toLocaleString()}</b></span>)}</div>
        <p className="cc-empty">Config <code>{rail.config}</code><CopyBtn value={rail.config} /> · <a href={`https://solscan.io/account/${rail.config}`} target="_blank" rel="noreferrer">Solscan ↗</a>. On-chain configs can't be edited; to change terms, create a new one (old coins keep theirs).</p>
      </div> : <p className="cc-empty">Not created yet. Launches stay disabled until the owner signs this once.</p>}
      {isOwner ? <>
        <div className="rail-form">{FIELDS.map(([k, l, why]) => <label key={k}><span>{l}</span><input inputMode="decimal" value={p[k]} onChange={e => setP(v => ({ ...v, [k]: e.target.value.replace(/[^0-9.]/g, '') }))} /><small>{why}</small></label>)}
          <label className="wide"><span>Fee claimer (receives FEELESS's share)</span><input placeholder={wallet?.address || 'Treasury / multisig address'} value={claimer} onChange={e => setClaimer(e.target.value.trim())} /><small>Defaults to your first Solana treasury route, else the signing wallet. Use a multisig.</small></label>
        </div>
        <button type="button" className="btn-primary" disabled={!!status} onClick={create}>{status || (wallet?.chain === 'solana' ? `${rail?.ready ? 'Create a new' : 'Create the'} launch config · sign with ${wallet.address.slice(0, 4)}…` : 'Connect Solana wallet')}</button>
        <small className="cc-empty">Any owner wallet can sign; switch wallets in Phantom and reconnect to use a different one. The transaction is simulated before you're asked to sign.</small>
      </> : <p className="cc-empty">Only the owner wallet can create the launch config.</p>}
    </div>
  </section>;
}
