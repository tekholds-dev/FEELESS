import '../../styles/fusePage.css';
import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';

// Cmd Ctr › Fuse admin settings. RunnerSettings: every gate / lane exit / light-up rule, range-checked by the server
// (runners.CFG_RANGES); "Reset" = defaults. AutoYieldDefault: arm 💸 auto-collect on NEW cards (users can turn it off).
const LABELS = {
  roundSize: ['Runners per round', ''], minMcap: ['Min market cap', '$'], minVol1h: ['Min 1h volume', '$'], maxTop10: ['Max top-10 hold', '%'],
  maxInsiders: ['Max insiders', '%'], maxDev: ['Max dev hold', '%'], scalpTp: ['Scalp: take all at', '+%'], scalpStop: ['Scalp: stop', '−%'],
  runnerTp1: ['Runner: ⅓ at', '+%'], runnerTp2: ['Runner: ⅓ at', '+%'], runnerTrail: ['Runner: trail', '%'], runnerStop: ['Runner: stop', '−%'],
  holdTrail: ['Hold: trail', '%'], holdStop: ['Hold: stop', '−%'], lightRounds: ['Rounds before the Fuse button lights', ''],
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
