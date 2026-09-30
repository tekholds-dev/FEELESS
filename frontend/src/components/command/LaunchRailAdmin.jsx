import React, { Suspense, lazy, useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../../hooks/useWallet';
import { RAIL_DEFAULTS, RAIL_PRESETS, railWarnings, checkRail, createLaunchRail, fetchLaunchRail, partnerFees, claimPartnerFees, configPools, claimCreationToll } from '../../lib/launchRail';
import { CopyBtn } from '../CopyBtn';
import { errorText } from '../../lib/api';
import { useSolPrice, usd } from '../../lib/solPrice';
import { TreasurySend } from './TreasurySend';
const CmdLaunch = lazy(() => import('./CmdLaunch').then(m => ({ default: m.CmdLaunch })));

const FIELDS = [
  ['initialMarketCap', 'Opening market cap (SOL)', 'Where the curve starts. 30 SOL ≈ pump.fun-style low open.'],
  ['migrationMarketCap', 'Graduation market cap (SOL)', 'When reached, liquidity moves to a Meteora DAMM v2 pool automatically.'],
  ['startingFeeBps', 'Launch fee (bps)', 'Anti-snipe: first-block buyers pay this (9900 = 99%, the max). Decays to the normal fee.'],
  ['endingFeeBps', 'Normal fee (bps)', 'Fee after the decay window (100 = 1%).'],
  ['feeDecayMin', 'Anti-snipe window (min)', 'How long the launch fee takes to fall to normal.'],
  ['creatorFeePct', 'Creator share of fees (%)', 'The rest goes to the FEELESS fee claimer below.'],
  ['lockedLpPct', 'Liquidity locked forever (%)', 'Share of graduated LP nobody can withdraw. 100 = unruggable.'],
  ['supply', 'Token supply', 'Fixed; mint authority is revoked at creation.'],
];

// FEELESS's share of trading fees on coins launched on our configs. It sits inside each coin's pool until
// the config's fee claimer claims it; then it lands in that wallet as SOL (or USDC).
function PartnerFees({ configs }) {
  const { wallet, provider, connect } = useWallet() || {};
  const [rows, setRows] = useState(null);
  const [busy, setBusy] = useState('');
  const load = useCallback(() => Promise.all(configs.map(c => partnerFees(c.config, c.quote === 'USDC' ? 6 : 9).then(r => r.map(x => ({ ...x, ...c }))).catch(() => [])))
    .then(all => setRows(all.flat())), [configs.map(c => c.config).join()]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [load]);
  const claim = async r => {
    try {
      if (wallet?.address !== r.feeClaimer) { toast.message?.(`Connect the fee claimer ${r.feeClaimer.slice(0, 4)}… to claim.`); await connect?.('solana'); return; }
      await claimPartnerFees({ provider, feeClaimer: wallet.address, pool: r.pool, onStatus: setBusy });
      toast.success('Claimed — it is in the fee claimer wallet now.'); load();
    } catch (e) { toast.error(e.message || 'Claim failed'); } finally { setBusy(''); }
  };
  const total = (rows || []).reduce((a, r) => a + r.unclaimed, 0);
  return <div className="cc-block"><h4>💰 FEELESS fee share to claim <small className="chain-tag">{rows ? `${total.toFixed(4)} across ${rows.length} coin${rows.length === 1 ? '' : 's'}` : 'reading pools…'}</small></h4>
    <p className="cc-empty">Every coin launched on your configs pays FEELESS its share of trading fees. It waits inside that coin's pool until the fee claimer wallet signs a claim — then it lands in that wallet.</p>
    {rows && !rows.length && <p className="cc-empty">Nothing to claim yet.</p>}
    {(rows || []).slice(0, 20).map(r => <div key={r.pool} className="rail-house"><b>{r.label}</b><span>{r.unclaimed.toFixed(5)} {r.quote === 'USDC' ? 'USDC' : 'SOL'} unclaimed · pool <code>{r.pool.slice(0, 4)}…{r.pool.slice(-4)}</code></span><button type="button" className="btn-primary" disabled={!!busy} onClick={() => claim(r)}>{busy || (wallet?.address === r.feeClaimer ? 'Claim' : 'Connect claimer')}</button></div>)}
  </div>;
}

// Coins launched on house configs. Created by an owner wallet = house coin; anyone else = outsider (they paid your toll).
function HouseCoins({ house, owners }) {
  const { wallet, provider, connect } = useWallet() || {};
  const [rows, setRows] = useState(null);
  const [busy, setBusy] = useState('');
  useEffect(() => { Promise.all(house.map(h => configPools(h.config).then(r => r.map(x => ({ ...x, label: h.label, feeClaimer: h.feeClaimer, toll: h.params?.poolCreationFeeSol }))).catch(() => []))).then(a => setRows(a.flat())); }, [house]);
  const own = new Set(owners || []);
  const claim = async r => {
    try {
      if (wallet?.address !== r.feeClaimer) { await connect?.('solana'); return; }
      await claimCreationToll({ provider, feeClaimer: wallet.address, pool: r.pool, onStatus: setBusy }); toast.success('Toll claimed.');
    } catch (e) { toast.error(e.message?.includes('Claimed') ? 'Already claimed.' : e.message || 'Claim failed'); } finally { setBusy(''); }
  };
  return <div className="cc-block"><h4>🏠 Coins on house configs <small className="chain-tag">{rows ? `${rows.filter(r => own.has(r.creator)).length} house · ${rows.filter(r => !own.has(r.creator)).length} outsiders` : 'reading…'}</small></h4>
    {rows && !rows.length && <p className="cc-empty">No coins launched on house configs yet.</p>}
    {(rows || []).slice(0, 30).map(r => <div key={r.pool} className="rail-house"><b className={own.has(r.creator) ? 'hc-house' : 'hc-out'}>{own.has(r.creator) ? '🏠 House' : '⚠ Outsider'}</b><span>{r.label} · mint <code>{r.mint.slice(0, 4)}…{r.mint.slice(-4)}</code> · by <code>{r.creator.slice(0, 4)}…{r.creator.slice(-4)}</code></span>{Number(r.toll) > 0 && <button type="button" className="btn-outline" disabled={!!busy} onClick={() => claim(r)}>{busy || `Claim ${r.toll} SOL toll`}</button>}</div>)}
  </div>;
}

// What can be launched on FEELESS, what each one needs, and whether it's ready right now.
function LaunchMap({ rail }) {
  const live = !!rail?.ready;
  const items = [
    ['🪙', 'FEELESS coin', 'Bonding curve on your launch config → graduates to a locked Meteora pool.', live ? 'Ready' : 'Needs the config below (once)', live, '/terminal/launch'],
    ['💊', 'Pump.fun coin', 'Launches on pump.fun from the same Launch page. Fees go to pump.fun, not FEELESS.', 'Ready', true, '/terminal/launch'],
    ['🌊', 'Pool for a token you hold', 'Token/SOL pool on Meteora DAMM v2 (e.g. your reserve token). You deposit both sides.', 'Pools tab · needs tokens + SOL', true, null],
    ['🪂', 'Airdrop / holder rewards', 'Batch SOL or token drops from your wallet, simulated first.', 'Airdrop Studio', true, null],
    ['🎖', 'Badge payouts', 'Badges earn a % of a wallet you choose; the wallet signs its payout.', 'Badges tab', true, null],
  ];
  return <div className="launch-map" data-testid="launch-map">
    <div className="launch-steps">
      <div className={live ? 'done' : 'now'}><i>1</i><b>Launch config</b><small>ONE-TIME · owner or admin signs a template on-chain</small></div>
      <div className={live ? 'now' : ''}><i>2</i><b>Anyone launches coins</b><small>Launch page · each coin uses the config</small></div>
      <div><i>3</i><b>Graduation</b><small>auto Meteora pool · LP locked forever</small></div>
    </div>
    <details className="tr-explain"><summary>❓ Is the config one-time? Do I pick it per coin?</summary>
      <p><b>One-time.</b> The config is a template stored on-chain: curve, fees, anti-snipe, where FEELESS's fee share goes. You create it once; after that the Launch page uses it automatically for every coin — nobody picks it per coin. It can't be edited. To change terms, create a new one: new coins use the new config, coins already launched keep theirs. Launching your own coin (e.g. from your fee reserve wallet) is step 2: connect that wallet on the Launch page, and its creator share of fees becomes claimable by that wallet.</p></details>
    <div className="launch-kinds">{items.map(([ic, t, what, need, ok, href]) => <div key={t} className={`launch-kind ${ok ? 'ok' : 'todo'}`}><i>{ic}</i><b>{t}</b><small>{what}</small><em>{ok ? '✓' : '!'} {need}</em>{href && <a href={href}>Open →</a>}</div>)}</div>
  </div>;
}

// The order the site owner hooks things up in. Status comes from the server (presence only).
function SetupGuide({ keys, rail, routes }) {
  const has = k => keys?.find(x => x.key === k)?.set;
  const steps = [
    ['Solana RPC', has('SOLANA_RPC_URL'), 'Helius key in backend/.env as SOLANA_RPC_URL. Powers reads, forensics and the wallet relay.'],
    ['Price + chart data', has('JUPITER_API_KEY'), 'JUPITER_API_KEY in backend/.env.'],
    ['Public site URL', has('PUBLIC_SITE_URL'), 'PUBLIC_SITE_URL=https://your-domain in backend/.env. New coins\' name + image are served from here.'],
    ['Owner wallets', has('FEELESS_ADMIN_WALLETS'), 'FEELESS_ADMIN_WALLETS=addr1,addr2 — who can open this center. Use a hardware or multisig wallet.'],
    ['Fee claimer / treasury', routes, 'Treasury tab → set where earnings go. A Squads multisig vault is safest.'],
    ['FEELESS launch config', rail?.ready, 'Below: one signed transaction from the owner or an admin wallet (~0.01 SOL rent). After this, anyone can launch.'],
    ['Lock the API to your domain', has('ALLOWED_ORIGINS'), 'ALLOWED_ORIGINS=https://your-domain before going public.'],
  ];
  const done = steps.filter(s => s[1]).length;
  return <div className="cc-block setup-guide"><h4>Hook-up steps <em>{done}/{steps.length}</em></h4>
    <ol>{steps.map(([t, ok, how], i) => <li key={t} className={ok ? 'ok' : ''}><i>{ok ? '✓' : i + 1}</i><div><b>{t}</b><small>{how}</small></div></li>)}</ol>
    <small className="cc-empty">Restart the backend after editing .env. Keys are never shown here — only whether they are set.</small>
  </div>;
}

// What the public Launch tab offers. Owners always see every rail and house configs.
function LaunchTabRules({ call, tab, onSaved }) {
  const [t, setT] = useState(() => ({ rails: ['feeless', 'pump'], devBuy: true, maxDevBuySol: 5, banner: true, ...(tab || {}) }));
  const [busy, setBusy] = useState(false);
  const has = r => t.rails.includes(r);
  const flip = r => setT(x => ({ ...x, rails: has(r) ? x.rails.filter(y => y !== r) : [...x.rails, r] }));
  const save = async () => { setBusy(true); try { await call('/admin/launch-tab', { method: 'PUT', body: JSON.stringify({ ...t, maxDevBuySol: Number(t.maxDevBuySol) || 0 }) }); toast.success('Launch tab updated.'); onSaved?.(); } catch (e) { toast.error(errorText(e)); } finally { setBusy(false); } };
  return <div className="cc-block m-card" data-testid="launch-tab-rules"><div className="m-label">LAUNCH TAB · WHAT EVERYONE ELSE GETS <em>owners always see everything</em></div>
    <div className="m-row">{[['feeless', '🌐 FEELESS rail'], ['pump', '💊 Pump.fun']].map(([k, l]) => <label key={k} className="m-toggle"><input type="checkbox" checked={has(k)} onChange={() => flip(k)} />{l}</label>)}
      <label className="m-toggle"><input type="checkbox" checked={t.banner} onChange={e => setT(x => ({ ...x, banner: e.target.checked }))} />Banner upload</label>
      <label className="m-toggle"><input type="checkbox" checked={t.devBuy} onChange={e => setT(x => ({ ...x, devBuy: e.target.checked }))} />First buy</label>
      {t.devBuy && <label className="m-field"><span>Max first buy (SOL)</span><input className="m-input" inputMode="decimal" style={{ width: 90 }} value={t.maxDevBuySol} onChange={e => setT(x => ({ ...x, maxDevBuySol: e.target.value.replace(/[^0-9.]/g, '') }))} /></label>}
      <button type="button" className="m-btn primary" disabled={busy || !t.rails.length} onClick={save}>{busy ? 'Saving…' : 'Save launch tab'}</button></div>
    {!t.rails.length && <small className="m-neg">Keep at least one rail on.</small>}</div>;
}

const LR_TABS = [['launch', '🚀 Launch'], ['earnings', '💰 Earnings'], ['rules', '📜 Rules'], ['costs', '⛽ Costs'], ['setup', '⚙ Setup']];
const COST_FIELDS = [
  ['pumpSlippagePct', 'Pump.fun first-buy slippage (%)', 'The first buy lands in the same tx as the launch, so nobody can move the price: 1% is plenty. Higher only inflates the wallet preview.'],
  ['pumpPriorityFeeSol', 'Pump.fun priority fee (SOL)', 'Tip for faster inclusion. 0.0001 is enough most of the time; raise it when the network is congested.'],
  ['feelessPriorityFeeSol', 'FEELESS / House priority fee (SOL)', 'Same tip for launches on your own Meteora configs (public and house).'],
];

// Launch costs: what the platform adds on top of the chain's own rent. Clamped server-side (max 0.01 SOL priority).
function LaunchCosts({ call, costs, onSaved, solPx }) {
  const [v, setV] = useState(null);
  useEffect(() => { if (costs) setV(costs); }, [costs]);
  const save = async () => { try { await call('/admin/launch-costs', { method: 'PUT', body: JSON.stringify(v) }); toast.success('Launch costs saved'); onSaved?.(); } catch (e) { toast.error(e.message || 'Could not save'); } };
  if (!v) return <p className="cc-empty">Loading…</p>;
  return <div className="m-card m-stack" data-testid="launch-costs">
    <span className="m-label">LAUNCH COSTS <em>applies to every launch from now on</em></span>
    {COST_FIELDS.map(([k, label, why]) => <label key={k} className="lr-cost"><span>{label}{/SOL/.test(label) && solPx ? <em className="usd-hint"> {usd(v[k], solPx)}</em> : null}</span>
      <input className="m-input" inputMode="decimal" value={v[k]} onChange={e => setV(x => ({ ...x, [k]: e.target.value.replace(/[^0-9.]/g, '') }))} /><small className="m-dim">{why}</small></label>)}
    <div className="m-note">Not adjustable: pump.fun's own ~1% on the first buy, PumpPortal's 0.5% on the first buy (pump.fun launches only), ~0.02 SOL refundable rent per coin.</div>
    <button type="button" className="m-btn primary" onClick={save}>Save launch costs</button>
  </div>;
}

export function LaunchRailAdmin({ call, isOwner }) {
  const { wallet, provider, connect } = useWallet() || {};
  const [rail, setRail] = useState(null);
  const [keys, setKeys] = useState(null);
  const [owners, setOwners] = useState([]);
  const solPx = useSolPrice();
  const [routes, setRoutes] = useState(false);
  const [p, setP] = useState(RAIL_DEFAULTS);
  const [claimer, setClaimer] = useState('');
  const [status, setStatus] = useState('');
  const [preset, setPreset] = useState('shield');
  const [scope, setScope] = useState('public');
  const [launchOpen, setLaunchOpen] = useState(false);
  const [view, setView] = useState(() => { try { return localStorage.getItem('feeless:launch-desk') || 'launch'; } catch { return 'launch'; } });
  const pickView = v => { setView(v); try { localStorage.setItem('feeless:launch-desk', v); } catch { /* private mode */ } };
  const [houseLabel, setHouseLabel] = useState('');
  const [check, setCheck] = useState(null);
  const unit = p.quote === 'USDC' ? 'USDC' : 'SOL';
  const warnings = railWarnings({ ...p, feeClaimerSet: !!claimer.trim() });
  // Debounced dry-check with Meteora's own validator: nobody signs a config the program would reject.
  useEffect(() => {
    const fc = claimer.trim() || wallet?.address;
    if (!fc) { setCheck(null); return undefined; }
    const t = setTimeout(() => checkRail(p, fc).then(r => setCheck({ ok: true, ...r })).catch(e => setCheck({ ok: false, error: e.message })), 300);
    return () => clearTimeout(t);
  }, [p, claimer, wallet?.address]);
  const pick = pr => { setPreset(pr.id); setP(v => ({ ...RAIL_DEFAULTS, supply: v.supply, lockedLpPct: 100, ...pr.params })); };
  const load = useCallback(() => {
    fetchLaunchRail().then(setRail);
    call('/admin/setup').then(d => { setKeys(d.keys); setOwners(d.owners || []); }).catch(() => setKeys([]));
    call('/admin/treasury/routes').then(d => { setRoutes(!!d.routes?.length); const sol = d.routes?.find(r => !r.address.startsWith('0x'))?.address; if (sol) setClaimer(c => c || sol); }).catch(() => {});
  }, [call]);
  useEffect(load, [load]);
  const create = async () => {
    try {
      if (!wallet?.address || wallet.chain !== 'solana' || !provider?.signTransaction) { await connect?.('solana'); return; }
      const fc = claimer.trim() || wallet.address;
      setStatus('Building and dry-running the config…');
      const params = scope === 'house' ? { ...p, poolCreationFeeSol: Number(p.poolCreationFeeSol ?? 5) || 0 } : { ...p, poolCreationFeeSol: 0 };
      const r = await createLaunchRail({ provider, owner: wallet.address, feeClaimer: fc, params, onStatus: setStatus });
      setStatus('Saving…');
      await call('/admin/launch-rail', { method: 'PUT', body: JSON.stringify({ config: r.config, feeClaimer: fc, params: { ...params, preset }, scope, label: houseLabel }) });
      toast.success('FEELESS launch rail is live');
      setStatus(''); load();
    } catch (e) { setStatus(''); toast.error(e.message || 'Could not create the launch config'); }
  };
  const houses = rail?.house?.length || 0;
  return <section className="cc-panel launch-rail-admin lr-meta">
    <div className="m-card lr-head">
      <span className="m-label">LAUNCH DESK <em>pump.fun · FEELESS · house</em></span>
      <div className="lr-kpis">
        <div className="m-stat"><small>FEELESS rules</small><b className={`m-num sm ${rail?.ready ? 'm-pos' : ''}`}>{rail?.ready ? 'LIVE' : 'not set'}</b></div>
        <div className="m-stat"><small>House configs</small><b className="m-num sm">{houses}</b></div>
        <div className="m-stat"><small>Public rails</small><b className="m-num sm">{(rail?.tab?.rails || []).join(' · ') || '—'}</b></div>
        <div className="m-stat"><small>Pump slippage · priority</small><b className="m-num sm">{rail?.costs ? `${rail.costs.pumpSlippagePct}% · ${rail.costs.pumpPriorityFeeSol} SOL` : '…'}</b></div>
      </div>
    </div>
    <div className="m-seg lr-tabs" role="tablist">{LR_TABS.map(([k2, l2]) => <button key={k2} type="button" role="tab" aria-selected={view === k2} className={view === k2 ? 'active' : ''} onClick={() => pickView(k2)}>{l2}</button>)}</div>
    {view === 'launch' && <>
    <div className="cc-block cc-launch-coin"><h4>Step 2 · Launch a coin <small className="chain-tag">rail · config · coin · sign · receipt</small></h4>
      {!launchOpen
        ? <><p className="cc-empty">Pick 🏠 House, 🌐 FEELESS or 💊 Pump.fun, choose the config for this coin, fill it in, sign once. The receipt (CA, pump link, tx, terms) shows right after. Launch from the wallet that should own the coin.</p><button type="button" className="btn-primary" onClick={() => setLaunchOpen(true)} data-testid="open-cmd-launch">🚀 Open the launcher</button></>
        : <Suspense fallback={<p className="cc-empty">Loading the launcher…</p>}><CmdLaunch rail={rail} /></Suspense>}</div>
    </>}
    {view === 'earnings' && <>
    {rail?.house?.length > 0 && <HouseCoins house={rail.house} owners={owners} />}
    {rail?.ready && <PartnerFees configs={[{ label: 'Public', config: rail.config, feeClaimer: rail.feeClaimer, quote: rail.params?.quote }, ...(rail.house || []).map(h => ({ label: h.label, config: h.config, feeClaimer: h.feeClaimer, quote: h.params?.quote }))]} />}
      {!houses && !rail?.ready && <p className="m-note">Nothing earning yet — fee share and house-coin tolls show here once FEELESS or House configs have coins.</p>}
    </>}
    {view === 'rules' && <>
      <LaunchMap rail={rail} />
    <div className="cc-block"><h4>Step 1 · Launch rules {rail?.ready && <span className="pill-ok">LIVE</span>}</h4>
      <div className="rail-notcoin"><b>⚠ This does not create a coin.</b> It sets the rules every coin follows (curve, fees, anti-snipe, locked liquidity). No name, ticker or image here. To launch an actual coin, open the <a href="/terminal/launch">Launch page →</a> (name, ticker, image, first buy) after these rules exist.</div>
      {rail?.ready ? <div className="rail-live">
        <p>Every FEELESS launch uses this on-chain config. Fees go to <code>{rail.feeClaimer.slice(0, 4)}…{rail.feeClaimer.slice(-4)}</code><CopyBtn value={rail.feeClaimer} profile />.</p>
        <div className="rail-kv">{FIELDS.map(([k, l]) => <span key={k}><small>{l}</small><b>{Number(rail.params?.[k] ?? RAIL_DEFAULTS[k]).toLocaleString()}</b></span>)}</div>
        <p className="cc-empty">Config <code>{rail.config}</code><CopyBtn value={rail.config} /> · <a href={`https://solscan.io/account/${rail.config}`} target="_blank" rel="noreferrer">Solscan ↗</a>. On-chain configs can't be edited; to change terms, create a new one (old coins keep theirs).</p>
      </div> : <p className="cc-empty">Not created yet. Launches stay disabled until the owner or an admin signs this once.</p>}
      {rail && !rail.siteUrl && <div className="m-note warn" data-testid="rail-needs-domain"><b>Pump.fun launches work right now — Step 2 › Open the launcher › 💊 Pump.fun.</b>FEELESS-rail and House launches also need a public https domain: set PUBLIC_SITE_URL in backend/.env (coin names + images are hosted there forever, so a localhost or tunnel address would break the coin).</div>}
      {<>
        <div className="rail-presets" role="radiogroup" aria-label="Launch style">{RAIL_PRESETS.map(pr => <button key={pr.id} type="button" role="radio" aria-checked={preset === pr.id} className={preset === pr.id ? 'active' : ''} onClick={() => pick(pr)}><b>{pr.label}</b><small>{pr.blurb}</small></button>)}</div>
        <div className={`rail-ready ${check?.ok && !warnings.length ? 'ok' : check?.ok ? 'warn' : 'bad'}`} data-testid="rail-ready">
          <b>{!check ? '… checking' : check.ok ? `✓ Valid on Meteora · ${Number(check.raise.toFixed(check.quote === 'USDC' ? 0 : 1)).toLocaleString()} ${check.quote} raise to graduate` : `✗ Meteora would reject this: ${check.error}`}</b>
          {warnings.map(w => <span key={w}>⚠ {w}</span>)}
          <em><b className="rail-once">ONE-TIME SETUP</b> {rail?.ready ? 'Launches are LIVE on the current config; creating another only affects new coins.' : 'Sign once and every coin launched on FEELESS uses it — nobody picks it per coin.'} Anti-snipe stack: decaying launch fee + dynamic (volatility) fee + fixed supply, mint & freeze revoked, 100% LP lock.</em>
        </div>
        <div className="rail-form">{FIELDS.map(([k, l0, why]) => { const l = l0.replace('(SOL)', `(${unit})`); return <label key={k}><span>{l}{/SOL/.test(l) && solPx ? <em className="usd-hint"> {usd(p[k], solPx)}</em> : null}</span><input inputMode="decimal" value={p[k]} onChange={e => setP(v => ({ ...v, [k]: e.target.value.replace(/[^0-9.]/g, '') }))} /><small>{why}</small></label>; })}
          <label className="wide"><span>Fee claimer (receives FEELESS's share)</span><input placeholder={wallet?.address || 'Treasury / multisig address'} value={claimer} onChange={e => setClaimer(e.target.value.trim())} /><small>Defaults to your first Solana treasury route, else the signing wallet. Use a multisig.</small></label>
        </div>
        <div className="rail-scope"><div className="bdg-seg" role="radiogroup" aria-label="Who launches on this config">{[['public', '🌐 Public site config'], ['house', '🏠 House config (owner + admins)']].map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={scope === k} className={scope === k ? 'active' : ''} onClick={() => setScope(k)}>{l}</button>)}</div>
          <small className="cc-empty">{scope === 'public' ? 'Used by the Launch page for everyone. Creating a new one replaces it for new coins only.' : 'Only owners and admins see it on the Launch page, for FEELESS\'s own coins (e.g. your fee reserve coin). Set its fee claimer to the wallet that should earn from it. It never replaces the public config.'}</small>
          {scope === 'house' && <><input placeholder="House config name (e.g. Reserve coins)" maxLength={40} value={houseLabel} onChange={e => setHouseLabel(e.target.value)} />
            <label className="bdg-pct"><input inputMode="decimal" value={p.poolCreationFeeSol ?? '5'} onChange={e => setP(v => ({ ...v, poolCreationFeeSol: e.target.value.replace(/[^0-9.]/g, '') }))} /><span>SOL outsider toll</span></label>
            <small className="cc-empty">Meteora configs can't block other launchers on-chain, so house configs charge a <b>launch toll</b> paid to your fee claimer. An outsider launching on it pays you {Number(p.poolCreationFeeSol ?? 5) || 0} SOL. You pay it too when you launch, then claim 90% back (Meteora keeps 10%) — so each of your own launches costs ≈ {((Number(p.poolCreationFeeSol ?? 5) || 0) * 0.1).toFixed(3)} SOL. Outsider coins are flagged below and never count as house coins on the site.</small></>}</div>
        <button type="button" className="btn-primary" disabled={!!status || check?.ok === false} onClick={create}>{status || (wallet?.chain === 'solana' ? `Create ${scope === 'house' ? 'house' : 'public'} launch rules (no coin) · sign with ${wallet.address.slice(0, 4)}…` : 'Connect Solana wallet')}</button>
        <small className="cc-empty">The owner or any admin wallet can sign; switch wallets in Phantom and reconnect to use a different one. The transaction is simulated before you're asked to sign.</small>
      </>}
    </div>
    {rail?.house?.length > 0 && <div className="cc-block"><h4>🏠 House configs <small className="chain-tag">owners + admins launch with these from the Launch page</small></h4>
      {rail.house.map(h => <div key={h.config} className="rail-house"><b>{h.label}</b><span>{Number(h.params?.initialMarketCap ?? 30)} → {Number(h.params?.migrationMarketCap ?? 500)} {h.params?.quote === 'USDC' ? 'USDC' : 'SOL'} · snipe tax {Number(h.params?.startingFeeBps ?? 9900) / 100}% · fees to <code>{h.feeClaimer.slice(0, 4)}…{h.feeClaimer.slice(-4)}</code></span><a href={`https://solscan.io/account/${h.config}`} target="_blank" rel="noreferrer">config ↗</a></div>)}</div>}
    </>}
    {view === 'costs' && <>
      <LaunchCosts call={call} costs={rail?.costs} onSaved={load} solPx={solPx} />
    <details className="tr-explain"><summary>💰 What the config numbers cost you</summary>
      <ul>
        <li><b>Opening / graduation market cap are valuations, not deposits.</b> Nobody pays {Number(p.initialMarketCap) || 0} SOL{solPx ? ` (${usd(p.initialMarketCap, solPx).slice(2)})` : ''} to launch. The curve simply starts pricing the coin there; buyers' SOL moves it up to graduation.</li>
        <li><b>Creating this config:</b> ~0.01 SOL{solPx ? ` (${usd(0.01, solPx).slice(2)})` : ''} rent, once, from your wallet.</li>
        <li><b>Each coin launch:</b> ~0.02 SOL rent + network fee paid by the creator, plus any optional first buy they choose.</li>
        <li><b>Lower opening MC</b> = cheaper early tokens and more room to run; <b>higher</b> = fewer tokens per SOL at open.</li>
      </ul>
    </details>
    </>}
    {view === 'setup' && <>
      <SetupGuide keys={keys} rail={rail} routes={routes} />
    {isOwner && rail && <LaunchTabRules call={call} tab={rail.tab} onSaved={load} />}
      {isOwner && <TreasurySend ownerWallets={owners} />}
    <details className="tr-explain"><summary>🔐 Secure your coins & airdrop on a small budget</summary>
      <ol>
        <li><b>Split roles:</b> keep the creator wallet cold (hardware wallet) and only connect it to sign; use a separate hot wallet for day-to-day.</li>
        <li><b>Treasury in a multisig:</b> create a Squads vault (2-of-3), set it as the fee claimer and treasury route. Fees can then only move with 2 signatures.</li>
        <li><b>Lock liquidity</b> when you create pools (Pools tab, "Lock forever") — it earns the rug-proof badge and costs nothing extra.</li>
        <li><b>Airdrop cheaply:</b> SOL-only drops cost ~0.000005 SOL per transaction (18 wallets each). Token drops cost ~0.002 SOL per <i>new</i> holder (their token account rent) — so 100 new holders ≈ 0.2 SOL{solPx ? ` (${usd(0.2, solPx).slice(2)})` : ''}. Target existing holders first (Holders tab) — no account rent.</li>
        <li><b>Batch, don't spray:</b> schedule in Airdrop Studio, then "Send from wallet" packs transfers and simulates before you sign.</li>
        <li><b>Never</b> paste a seed phrase anywhere, including here. FEELESS never asks for one.</li>
      </ol>
    </details>
    </>}
  </section>;
}
