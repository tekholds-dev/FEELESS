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
