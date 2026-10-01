import '../../styles/fusePage.css';
import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../../hooks/useWallet';

// Cmd Ctr › Fuse admin settings. RunnerSettings: every gate / lane exit / light-up rule, range-checked by the server
// (runners.CFG_RANGES); "Reset" = defaults. AutoYieldDefault: arm 💸 auto-collect on NEW cards (users can turn it off).
const LABELS = {
  roundSize: ['Runners per round', ''], minMcap: ['Min market cap', '$'], minVol1h: ['Min 1h volume', '$'], maxTop10: ['Max top-10 hold', '%'],
  maxInsiders: ['Max insiders', '%'], maxDev: ['Max dev hold', '%'], scalpTp: ['Scalp: take all at', '+%'], scalpStop: ['Scalp: stop', '−%'],
  runnerTp1: ['Runner: ⅓ at', '+%'], runnerTp2: ['Runner: ⅓ at', '+%'], runnerTrail: ['Runner: trail', '%'], runnerStop: ['Runner: stop', '−%'],
  holdTrail: ['Hold: trail', '%'], holdStop: ['Hold: stop', '−%'], lightRounds: ['Rounds before the Fuse button lights', ''],
  bondCurve: ['🔔 Bond run: curve at least', '%'], bondBuys: ['🔔 Bond run: buys at least', '%'], bondVol1h: ['🔔 Bond run: 1h volume at least', '$'],
  bondTop10: ['🔔 Bond run: top-10 under (if snipers not out)', '%'], bondPts: ['🔔 Bond run: score boost', 'pts'],
  autoCoins: ['⚔ Arena build: coins', ''], autoPools: ['⚔ Arena build: pools', ''], battleMins: ['⚔ Battle length', 'min'],
};

export function RunnerSettings({ call }) {
  const [d, setD] = useState(null); const [cfg, setCfg] = useState({});
  useEffect(() => { call('/admin/runners/config').then(x => { setD(x); setCfg(x.cfg); }).catch(e => toast.error(e.message)); }, [call]);
  if (!d) return null;
  const save = async reset => { try { const x = await call('/admin/runners/config', { method: 'POST', body: JSON.stringify(reset ? { reset: true } : { cfg }) }); setCfg(x.cfg); toast.success(reset ? 'Runner settings reset' : 'Runner settings saved — next round uses them'); } catch (e) { toast.error(e.message); } };
  return <details className="m-card rn-settings" data-testid="runner-settings"><summary><span className="m-label">⚙ RUNNER SETTINGS</span> <small className="m-dim">gates · lane exits · light-up</small></summary>
    <div className="m-grid">{Object.keys(LABELS).filter(k => k in (d.ranges || {})).map(k => { const [lo, hi] = d.ranges[k]; return <label key={k} className="m-field"><span>{LABELS[k][0]} {LABELS[k][1] && <em>({LABELS[k][1]})</em>}</span>
      <input className="m-input m-num" type="number" min={lo} max={hi} value={cfg[k] ?? ''} onChange={e => setCfg({ ...cfg, [k]: Number(e.target.value) })} data-testid={`rn-${k}`} /><small className="m-dim">{lo}–{hi} · default {d.defaults[k]}</small></label>; })}</div>
    <div className="fg-acts"><button type="button" className="m-btn primary" onClick={() => save(false)}>Save settings</button><button type="button" className="m-btn" onClick={() => save(true)}>Reset to defaults</button></div></details>;
}

export function AutoYieldDefault({ call }) {
  const [v, setV] = useState(null);
  useEffect(() => { call('/admin/fuses/auto-yield').then(setV).catch(() => {}); }, [call]);
  if (!v) return null;
  const save = async next => { try { setV(await call('/admin/fuses/auto-yield', { method: 'POST', body: JSON.stringify(next) })); toast.success(next.on ? `New cards auto-collect at +${next.at}%` : 'Auto-collect default off'); } catch (e) { toast.error(e.message); } };
  return <div className="m-card m-row ay-default" data-testid="auto-yield-default"><span className="m-label">💸 AUTO-COLLECT DEFAULT</span>
    <label className="m-toggle"><input type="checkbox" checked={v.on} onChange={e => save({ ...v, on: e.target.checked })} />Arm on every new card</label>
    <label className="m-field"><span>at +%</span><input className="m-input m-num" type="number" min="10" max="1000" value={v.at} onChange={e => setV({ ...v, at: Number(e.target.value) })} onBlur={() => save(v)} /></label>
    <small className="m-dim">Alert + pre-filled Collect profit (sells only the gain). Holders still approve it and can turn it off per card — FEELESS never signs.</small></div>;
}

// Core › Fees › Card bundle pricing: cards bought all at once (Fuse / runners) pay a flat $ per coin instead of the %,
// never more than maxPct of a leg; legs above maxLegUsd pay the normal %. Cmd Ctr cards pay no FEELESS fee.
export const bundleExample = (b, legUsd, swapBps) => (!b.on || legUsd > b.maxLegUsd ? legUsd * swapBps / 10000 : Math.min(b.perLegUsd, legUsd * b.maxPct / 100));

export function BundlePricing({ call, initial, swapBps = 0 }) {
  const [b, setB] = useState(initial || { on: true, perLegUsd: 0.1, maxPct: 5, maxLegUsd: 50 });
  useEffect(() => { if (initial) setB(initial); }, [initial]);
  const save = async () => { try { setB((await call('/admin/fees/bundle', { method: 'POST', body: JSON.stringify(b) })).bundle); toast.success('Bundle pricing saved — next card quote uses it.'); } catch (e) { toast.error(e.message); } };
  const set = (k, v) => setB(x => ({ ...x, [k]: v }));
  return <div className="cc-block fee-bundle" data-testid="bundle-pricing"><h4>6 · Card bundle pricing (Fuse &amp; runners)</h4>
    <label className="cc-check"><input type="checkbox" checked={b.on} onChange={e => set('on', e.target.checked)} />Flat price per coin when a card is bought all at once</label>
    <div className="cc-mini-grid">
      <label>$ per coin / pool<input type="number" step="0.01" min="0" max="5" value={b.perLegUsd} onChange={e => set('perLegUsd', Number(e.target.value))} data-testid="bundle-per-leg" /></label>
      <label>Never more than (% of a leg)<input type="number" step="0.1" min="0.1" max="20" value={b.maxPct} onChange={e => set('maxPct', Number(e.target.value))} /></label>
      <label>Flat price for legs up to ($)<input type="number" min="1" max="10000" value={b.maxLegUsd} onChange={e => set('maxLegUsd', Number(e.target.value))} /></label></div>
    <ul className="bundle-ex">{[[1, 3], [20, 3], [100, 6]].map(([usd, n]) => { const leg = usd / n; const fee = bundleExample(b, leg, swapBps) * n;
      return <li key={usd}><b>${usd} card · {n} coins</b><span className="m-num">${fee.toFixed(3)} total</span><small>{((fee / usd) * 100).toFixed(2)}%</small></li>; })}
      <li className="is-free"><b>Cmd Ctr card · 12 coins</b><span className="m-num">$0 FEELESS</span><small>network + partner fees only</small></li></ul>
    <small className="cc-empty">Bigger legs than the limit pay the normal %, so the flat price can't be used to dodge the fee on one big swap.</small>
    <button type="button" className="btn-primary" onClick={save} data-testid="bundle-save">Save bundle pricing</button></div>;
}

// Cmd Ctr › Fuse › Card rules: what traders can pick (auto-profit levels, counted after fees from their confirmed buy),
// the swap-mode trigger, the Arena top tier, and Fuse Fee-Back (share of fees paid on a card, unlocked by holding it;
// loyalty + Arena bonuses; cap). The book shows earned / paid / owed per wallet; "Paid" records a payout you sent.
const RULE_LABELS = [['swapDropPct', 'Swap mode: alert when a leg is down', '%'], ['topTierPct', 'Arena top tier: card up at least', '+%'],
  ['fbHolderPct', 'Fee-Back: share of fees paid', '%'], ['fbHoldHours', 'Unlocks after holding', 'h'], ['fbLoyaltyPct', 'Loyalty bonus', '+%'],
  ['fbLoyaltyDays', 'Loyalty after', 'days'], ['fbArenaPct', 'Arena bonus (card hot/blazing)', '+%'], ['fbCapPct', 'Fee-Back cap', '%'], ['netFeeUsdPerLeg', 'Network fee estimate per leg', '$'], ['copyPct', '⚡ Copy cards: owner earns of the copier\'s fee', '%'], ['seasonBoostPct', '🏆 Season top 3: Fee-Back boost', '+%']];

export function CardRules({ call }) {
  const [d, setD] = useState(null); const [r, setR] = useState(null); const [lv, setLv] = useState('');
  useEffect(() => { call('/admin/fuses/rules').then(x => { setD(x); setR(x.rules); setLv(x.rules.yieldLevels.join(', ')); }).catch(() => {}); }, [call]);
  if (!r) return <div className="m-card ay-default is-loading" data-testid="card-rules"><span className="m-label">🃏 CARD RULES</span><span className="m-dim">Loading…</span></div>;
  const save = async body => { try { const x = await call('/admin/fuses/rules', { method: 'POST', body: JSON.stringify(body) }); setD(d0 => ({ ...d0, ...x })); setR(x.rules); setLv(x.rules.yieldLevels.join(', ')); toast.success(body.wallet ? 'Payout recorded' : 'Card rules saved'); } catch (e) { toast.error(e.message); } };
  const fb = d.feeback || { rows: [], owedUsd: 0, earnedUsd: 0 };
  return <details className="m-card rn-settings card-rules" data-testid="card-rules"><summary><span className="m-label">🃏 CARD RULES · AUTO-PROFIT · SWAP · FEE-BACK</span><small className="m-dim">Fee-Back owed ${fb.owedUsd.toFixed(2)} of ${fb.earnedUsd.toFixed(2)} earned</small></summary>
    <div className="cr-grid">
      <label className="m-field"><span>Auto-profit levels traders pick (after fees)</span><input className="m-input m-num" value={lv} onChange={e => setLv(e.target.value)} placeholder="25, 50, 100, 200" data-testid="cr-levels" /></label>
      <label className="m-field"><span>Default level</span><input className="m-input m-num" type="number" value={r.yieldDefault} onChange={e => setR({ ...r, yieldDefault: Number(e.target.value) })} /></label>
      {RULE_LABELS.map(([k, l, u]) => <label key={k} className="m-field"><span>{l} <small>{u}</small></span><input className="m-input m-num" type="number" step="any" value={r[k]} onChange={e => setR({ ...r, [k]: Number(e.target.value) })} /></label>)}
    </div>
    <p className="m-note">A card holder gets back {r.fbHolderPct}% of the FEELESS fees they paid on a card after holding it {r.fbHoldHours}h, +{r.fbLoyaltyPct}% after {r.fbLoyaltyDays} days, +{r.fbArenaPct}% while it burns hot on the Arena (max {r.fbCapPct}%). Tracked from the fee ledger; you pay it out.</p>
    <div className="fg-acts"><button type="button" className="m-btn primary m-go" onClick={() => save({ ...r, yieldLevels: lv.split(/[ ,]+/).map(Number).filter(Boolean) })} data-testid="cr-save">Save card rules</button>
      <button type="button" className="m-btn" onClick={() => save(d.defaults)}>Reset</button></div>
    {fb.rows.length > 0 && <table className="vd-table cr-book"><thead><tr><th>Wallet</th><th>Cards</th><th>Earned</th><th>Paid</th><th>Owed</th><th /></tr></thead><tbody>
      {fb.rows.slice(0, 30).map(w => <tr key={w.wallet}><td><code>{w.wallet.slice(0, 4)}…{w.wallet.slice(-4)}</code></td><td>{w.cards}</td><td>${w.earnedUsd.toFixed(3)}</td><td>${w.paidUsd.toFixed(3)}</td><td className={w.owedUsd > 0 ? 'm-pos' : ''}>${w.owedUsd.toFixed(3)}</td>
        <td>{w.owedUsd > 0 && <button type="button" className="m-btn" onClick={() => save({ wallet: w.wallet, paidUsd: w.owedUsd })}>Mark paid</button>}</td></tr>)}</tbody></table>}
  </details>;
}


// 💸 Weekly Fuse payout: everyone owed Fuse Fee-Back + copy cuts, paid in SOL from the connected fee wallet in ONE approval
// (lib/batchSend: packed, simulated, then signed). The server credits only what actually moved on-chain, from a signer,
// at the frozen plan price and never above what each wallet was owed. FEELESS wallets and flagged bots are never paid.
export function FusePayouts({ call }) {
  const { wallet, provider, connect } = useWallet() || {};
  const [plan, setPlan] = useState(null); const [busy, setBusy] = useState('');
  const load = () => call('/admin/fuses/payouts/plan').then(setPlan).catch(e => toast.error(e.message));
  const pay = async () => {
    if (!wallet?.address || !provider) { connect?.(); return; }
    try {
      setBusy('Preparing…');
      const { batchSend } = await import('../../lib/batchSend');
      const sigs = await batchSend({ provider, owner: wallet.address, recipients: plan.rows.map(r => ({ address: r.wallet, amount: r.sol })), kind: 'fuse-payout', onStatus: setBusy });
      setBusy('Verifying on-chain…');
      const out = await call('/admin/fuses/payouts/paid', { method: 'POST', body: JSON.stringify({ planId: plan.id, sigs }) });
      toast.success(`Paid $${out.paidUsd.toFixed(2)} to ${out.wallets} wallets — verified on-chain.`); setPlan(null);
    } catch (e) { toast.error(e.message); } finally { setBusy(''); }
  };
  return <div className="m-card fpay" data-testid="fuse-payouts"><div className="m-row"><span className="m-label">💸 WEEKLY FUSE PAYOUT</span>
    <small className="m-dim">Fee-Back + copy cuts owed to traders · one approval from your fee wallet · verified on-chain</small>
    {!plan && <button type="button" className="m-btn primary m-go" onClick={load} data-testid="payout-load">Build this week's payout</button>}</div>
    {plan && <>{!plan.rows.length ? <p className="m-dim">Nobody is owed more than $0.05 right now{plan.bots ? ` (${plan.bots} flagged bot wallet${plan.bots > 1 ? 's' : ''} excluded)` : ''}.</p>
      : <><ul className="fpay-rows">{plan.rows.slice(0, 40).map((r, i) => <li key={r.wallet} style={{ '--i': i }}><code>{r.wallet.slice(0, 4)}…{r.wallet.slice(-4)}</code><span className="m-num">${r.owedUsd.toFixed(3)}</span><b className="m-num">{r.sol.toFixed(5)} SOL</b></li>)}</ul>
        <div className="m-row"><b className="m-num">${plan.totalUsd.toFixed(2)} · {plan.totalSol.toFixed(5)} SOL</b><small className="m-dim">at ${plan.solUsd}/SOL{plan.bots ? ` · ${plan.bots} bot wallet(s) excluded` : ''}</small>
          <button type="button" className="m-btn primary m-go" disabled={Boolean(busy)} onClick={pay} data-testid="payout-pay">{busy || (wallet?.address ? `Pay ${plan.rows.length} wallets` : 'Connect fee wallet')}</button></div></>}
      {plan.history?.length > 0 && <details className="fpay-hist"><summary>Past payouts</summary>{plan.history.map(h => <small key={h.at}>{new Date(h.at * 1000).toLocaleDateString()} · ${h.rows.reduce((a, r) => a + r.usd, 0).toFixed(2)} to {h.rows.length} · {h.sigs[0].slice(0, 8)}…</small>)}</details>}</>}
  </div>;
}

// ⚡ Stronger engine found: the server compares the live runner config with the recommended one (runners.RECOMMENDED) and
// lists every weaker setting with its reason + each lane's self-tuning record. Nothing changes until Cmd Ctr clicks Apply.
export function EngineSuggest({ call }) {
  const [d, setD] = useState(null);
  const load = () => call('/admin/runners/suggest').then(setD).catch(() => {});
  useEffect(() => { load(); }, [call]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!d?.suggestions) return null;
  const apply = async () => { try { await call('/admin/runners/config', { method: 'POST', body: JSON.stringify({ cfg: { ...d.cfg, ...Object.fromEntries(d.suggestions.map(s => [s.key, s.to])) } }) });
    toast.success('Stronger engine applied — the next round uses it.'); load(); } catch (e) { toast.error(e.message); } };
  const lanes = Object.entries(d.lanes || {});
  return <div className={`m-card eng-sug ${d.suggestions.length ? 'is-on' : ''}`} data-testid="engine-suggest">
    <div className="m-row"><span className="m-label">⚡ ENGINE</span>{d.suggestions.length ? <b>Stronger config found · {d.suggestions.length} settings</b> : <small className="m-dim">Running the recommended engine.</small>}
      {d.suggestions.length > 0 && <button type="button" className="m-btn primary m-go" onClick={apply} data-testid="engine-apply">Apply stronger engine</button>}</div>
    {d.suggestions.length > 0 && <ul className="eng-list">{d.suggestions.map(s => <li key={s.key}><code>{s.key}</code><span className="m-num">{s.now} → <b>{s.to}</b></span><small className="m-dim">{s.why}</small></li>)}</ul>}
    {lanes.length > 0 && <div className="eng-lanes">{lanes.map(([l, p]) => <span key={l} className={`m-chip ${d.weights?.[l] < 1 ? 'warn' : d.weights?.[l] > 1 ? 'ok' : ''}`} data-tip={`${p.n} picks · ${p.winRate}% won · lost ${p.losingDays} day(s) in a row`}>{l} {p.avgPct >= 0 ? '+' : ''}{p.avgPct}% · ×{d.weights?.[l] ?? 1}</span>)}</div>}
  </div>;
}
