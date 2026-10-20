import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { errorText } from '../../lib/api';
import '../../styles/codeHealth.css';

// HQ › Lag catcher › 🧹 Code health: the last static scan (backend/code_health.py, cached in data/code_health.json — nothing is
// scanned on a request). Each row opens its file:line in the editor and says the fix.
export const CH_TABS = [
  ['dead_def', '🪦 Dead code', 'Backend functions nothing calls outside tests'],
  ['dead_export', '📦 Dead exports', 'Frontend exports never imported outside their own file / tests'],
  ['dead_css', '🎨 Unused CSS', 'Class rules no component renders'],
  ['dup', '👯 Duplicates', 'The same function body in two places'],
  ['big', '🐘 Biggest', 'Longest functions and components by lines'],
];
const HOW = [['all', 'All'], ['none', 'Unused'], ['tests', 'Tests only'], ['own', 'Own file only']];

export const editorUrl = (root, file, line) => `vscode://file/${encodeURI(`${root}/${file}`)}:${line || 1}`;
const ago = at => { const m = Math.round((Date.now() / 1000 - at) / 60); return m < 60 ? `${m}m ago` : `${Math.round(m / 60)}h ago`; };

export function chRows(d, tab, how) {
  return (d?.rows || []).filter(r => r.kind === tab && (tab !== 'dead_export' || how === 'all' || r.how === how))
    .sort((a, b) => (tab === 'big' ? (b.lines || 0) - (a.lines || 0) : 0));
}

function Row({ r, root, max }) {
  const copy = () => { try { navigator.clipboard.writeText(`${r.file}:${r.line}`); toast.success('Path copied'); } catch { /* clipboard blocked */ } };
  return <li className={`chl-row k-${r.kind}`}>
    <a className="chl-loc" href={editorUrl(root, r.file, r.line)} data-tip="Open in the editor"><b>{r.name}</b><code>{r.file}:{r.line}</code></a>
    {r.lines != null && <span className="chl-bar" data-tip={`${r.lines} lines`}><i style={{ transform: `scaleX(${Math.min(1, r.lines / (max || 1))})` }} /><em>{r.lines}</em></span>}
    <span className="chl-fix">{r.fix}{r.twin && <a href={editorUrl(root, r.twin.split(':')[0], r.twin.split(':')[1])}> → twin</a>}</span>
    <button type="button" className="m-btn chl-copy" onClick={copy} aria-label="Copy file:line">⧉</button>
  </li>;
}

export function CodeHealth({ call }) {
  const [d, setD] = useState(null);
  const [tab, setTab] = useState('dead_def');
  const [how, setHow] = useState('none');
  const load = useCallback(() => call('/admin/perf/code-health').then(setD).catch(e => toast.error(errorText(e))), [call]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (!d?.scanning) return undefined; const t = setTimeout(load, 4000); return () => clearTimeout(t); }, [d, load]);
  const rescan = async () => { try { await call('/admin/perf/code-health/scan', { method: 'POST' }); setD(x => ({ ...x, scanning: true })); } catch (e) { toast.error(errorText(e)); } };
  const rows = useMemo(() => chRows(d, tab, how), [d, tab, how]);
  const max = useMemo(() => Math.max(1, ...rows.map(r => r.lines || 0)), [rows]);
  const t = d?.totals || {};
  const lines = (t.pyLines || 0) + (t.jsLines || 0) + (t.cssLines || 0);
  return <div className="cc-block chl" data-testid="code-health">
    <div className="chl-head"><h4>🧹 Code health</h4>
      <span className="chl-tot">{d?.at ? <>
        <b>{lines.toLocaleString()}</b> lines · py {(t.pyLines || 0).toLocaleString()} · js {(t.jsLines || 0).toLocaleString()} · css {(t.cssLines || 0).toLocaleString()} · scanned {ago(d.at)}</> : 'No scan yet.'}</span>
      <button type="button" className="m-btn" onClick={rescan} disabled={d?.scanning} data-testid="chl-rescan">{d?.scanning ? 'Scanning…' : '↻ Rescan'}</button></div>
    <div className="m-seg chl-tabs">{CH_TABS.map(([k, l, tip]) => <button key={k} type="button" className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-tip={tip} data-testid={`chl-tab-${k}`}>
      {l} <em>{d?.counts?.[k] || 0}</em></button>)}</div>
    {tab === 'dead_export' && <div className="m-seg chl-how">{HOW.map(([k, l]) => <button key={k} type="button" className={how === k ? 'active' : ''} onClick={() => setHow(k)}>{l}</button>)}</div>}
    {tab === 'big' && d?.biggestFiles?.length > 0 && <p className="m-note chl-files">Biggest files: {d.biggestFiles.slice(0, 5).map(f => `${f.file.split('/').pop()} ${f.lines.toLocaleString()}`).join(' · ')}</p>}
    {!rows.length ? <p className="cc-empty">{d?.at ? 'Nothing here. 🟢' : 'Press Rescan.'}</p>
      : <ul className="chl-list">{rows.slice(0, 120).map((r, i) => <Row key={`${r.file}:${r.line}:${i}`} r={r} root={d.root} max={max} />)}</ul>}
    <p className="m-note">Heuristic: dynamic names (getattr, `x-${'{'}…{'}'}` classes, string routes) can hide a use — check before deleting.</p>
  </div>;
}
