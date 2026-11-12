import React, { useCallback, useEffect, useState } from 'react';
import '../../styles/pocWatch.css';

// 👁 PoC watch (owner 2026-11-12, AGT-5): pick a page, the steps to check and how many hours. It checks a few times an hour while the agent does
// other work; every check is kept as proof (time, the page's fingerprint, what changed, each step's answer, its real cost) and a SHORT report is filed
// in the PoC folder at the end. The model is only asked when the page really changed. It only reads; nothing is posted.
const HOURS = [1, 2, 4, 8, 12, 24]; const PER = [1, 2, 3, 4];
const money = v => (v == null ? '—' : v === 0 ? '$0' : v < 0.01 ? `$${Number(v).toFixed(4)}` : `$${Number(v).toFixed(2)}`);
const hm = at => (at ? new Date(at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—');
const left = (w, now) => { const s = Math.max(0, w.endsAt - now); return s >= 3600 ? `${Math.floor(s / 3600)}h ${Math.round((s % 3600) / 60)}m left` : `${Math.round(s / 60)}m left`; };
const SEEN = { yes: 'is-yes', no: 'is-no', unclear: 'is-un' };

function Timeline({ w }) {
  const total = w.hours * w.perHour; const ch = w.checks || [];
  return <ol className="pw-line" aria-label={`${ch.length} of about ${total} checks`} data-testid={`pw-line-${w.id}`}>{Array.from({ length: Math.min(total, 48) }, (_, i) => { const c = ch[i];
    const cls = !c ? '' : !c.ok ? 'is-fail' : c.carried ? 'is-same' : c.changed ? 'is-new' : 'is-same';
    return <li key={i} className={cls} style={{ '--i': i }} data-tip={c ? `${hm(c.at)} · ${!c.ok ? c.why || 'failed' : c.carried ? 'page unchanged · no model call · $0' : `${c.changed ? `page changed (${c.newLines || 0} new lines)` : 'page unchanged'} · ${money(c.usd)}`}${c.sha ? ` · page #${c.sha}` : ''}` : 'still to come'} />; })}</ol>;
}

function WatchCard({ w, now, busy, act, onFolder }) {
  const run = w.status === 'running'; const last = [...(w.checks || [])].reverse().find(c => c.ok && c.steps?.length); const rep = w.report;
  const part = run ? Math.min(1, (now - w.startedAt) / (w.endsAt - w.startedAt)) : 1;
  return <article className={`pw-card m-card${run ? ' is-run' : ''}`} data-testid={`pw-card-${w.id}`}>
    <header><i className="pw-dot" aria-hidden="true" /><span><b>{w.host}</b><small>{run ? `${(w.checks || []).length} checks · ${left(w, now)} · every ${Math.round(w.every / 60)} min` : `${rep?.read ?? 0} checks in ${w.hours} h${w.stoppedEarly ? ' · stopped early' : ''} · filed`}</small></span>
      <em className="m-num" data-tip="What its model calls really cost. Checks where the page did not change cost nothing">{money(w.spentUsd)}</em></header>
    <i className="pw-bar" aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, part)})` }} /></i>
    <Timeline w={w} />
    {last?.headline || rep?.headline ? <p className="pw-head">“{rep?.headline || last.headline}”</p> : null}
    <ul className="pw-steps">{w.steps.map((s, i) => { const a = rep ? rep.steps[i] : last?.steps?.[i]; const seen = rep ? (a?.verdict === 'seen' ? 'yes' : a?.verdict === 'not seen' ? 'no' : 'unclear') : a?.seen;
      return <li key={s} data-testid={`pw-step-${w.id}-${i}`}><b className={`pw-chip ${SEEN[seen] || ''}`}>{rep ? (a?.verdict || '—').toUpperCase() : (seen || 'waiting').toUpperCase()}</b><span><small>{s}</small>{(rep ? a?.last : a?.note) ? <em>{rep ? a.last : a.note}</em> : null}{rep && a?.yes ? <em className="m-num">{a.yes} of {a.checks} checks · first {hm(a.firstYesAt)}</em> : null}</span></li>; })}</ul>
    <footer>{run ? <button type="button" className="m-btn" disabled={!!busy} onClick={() => act({ op: 'watch_stop', text: w.id }, w.id)} data-tip="Ends it now and files the short report with every check so far" data-testid={`pw-stop-${w.id}`}>{busy === w.id ? 'Filing…' : 'Stop and file the report'}</button>
      : <><button type="button" className="m-btn m-go" onClick={onFolder} data-tip="Opens the PoC folder where the report is filed" data-testid={`pw-open-${w.id}`}>Open the report</button><button type="button" className="m-btn" disabled={!!busy} onClick={() => act({ op: 'watch_drop', text: w.id }, w.id)} data-tip="Clears it from this list. The filed report stays in the PoC folder" data-testid={`pw-drop-${w.id}`}>Clear</button></>}</footer>
  </article>;
}

export default function PocWatch({ cat, work, onFolder }) {
  const [d, setD] = useState(null); const [busy, setBusy] = useState(''); const [err, setErr] = useState(''); const [now, setNow] = useState(() => Date.now() / 1000);
  const [f, setF] = useState({ url: '', steps: [''], hours: 4, perHour: 3 });
  const act = useCallback(async (body, key = 'x') => { setBusy(key); setErr(''); try { const j = await work(cat.id, body); setD(j); return j; } catch (e) { setErr(e.message); return null; } finally { setBusy(''); } }, [cat.id, work]);
  useEffect(() => { act({ op: 'watch_get' }, 'load'); const t = setInterval(() => { setNow(Date.now() / 1000); if (!document.hidden) work(cat.id, { op: 'watch_get' }).then(setD).catch(() => {}); }, 60000); return () => clearInterval(t); }, [act, cat.id, work]);
  const watches = d?.watches || []; const running = watches.filter(w => w.status === 'running').length; const max = d?.limits?.watches ?? 4;
  const steps = f.steps.map(s => s.trim()).filter(Boolean); const asks = f.hours * f.perHour;
  const free = /^local\//.test(d?.model || '');
  const cost = !d?.model ? 'Pick a model for this agent first.' : free ? `Up to ${asks} checks on ${d.model}, its own machine: $0.` : d.perAskUsd == null ? `Up to ${asks} checks on ${d.model}. It only asks the model when the page changed; the price shows after its first paid check.` : `Up to ${asks} checks. Worst case ${money(asks * d.perAskUsd)} on ${d.model} if the page changes every time; a quiet page costs $0.`;
  const setStep = (i, v) => setF(x => ({ ...x, steps: x.steps.map((s, j) => (j === i ? v : s)) }));
  const go = async e => { e.preventDefault(); const j = await act({ op: 'watch_add', tools: { url: f.url, steps, hours: f.hours, perHour: f.perHour } }, 'add'); if (j) setF(x => ({ ...x, url: '', steps: [''] })); };
  return <div className="pw" data-testid="pw">
    <div className="pcl-stats pw-stats" role="list" aria-label="PoC watch at a glance">
      <span role="listitem"><small>RUNNING</small><b className={running ? 'is-hot' : ''} data-testid="pw-running">{running}/{max}</b></span>
      <span role="listitem"><small>CHECKS KEPT</small><b>{watches.reduce((n, w) => n + (w.checks || []).length, 0)}</b></span>
      <span role="listitem" data-tip="What one check that asked the model really cost, on average"><small>PER PAID CHECK</small><b>{money(d?.perAskUsd)}</b></span>
      <span role="listitem"><small>SPENT</small><b>{money(watches.reduce((n, w) => n + (w.spentUsd || 0), 0))}</b></span>
      <span role="listitem"><small>READS ON</small><b>{d?.model || '—'}</b></span>
    </div>
    <form className="pw-add m-card" onSubmit={go} data-testid="pw-form">
      <label><small>PAGE</small><input className="m-input" value={f.url} onChange={e => { const v = e.target.value; setF(x => ({ ...x, url: v })); }} placeholder="a coin page, a forum thread, a news page…" aria-label="Page to watch" data-testid="pw-url" /></label>
      <div className="pw-stepin"><small>STEPS TO CHECK · {steps.length}/{d?.limits?.steps ?? 5}</small>{f.steps.map((s, i) => <span key={i} className="pw-stepin-row"><b className="m-num">{i + 1}</b><input className="m-input" value={s} onChange={e => setStep(i, e.target.value)} placeholder={i ? 'another thing to check' : 'Is a launch date announced?'} aria-label={`Step ${i + 1}`} data-testid={`pw-step-in-${i}`} />
        {f.steps.length > 1 ? <button type="button" className="m-btn pw-x" onClick={() => setF(x => ({ ...x, steps: x.steps.filter((_, j) => j !== i) }))} aria-label={`Remove step ${i + 1}`} data-tip="Remove this step">×</button> : null}</span>)}
        {f.steps.length < (d?.limits?.steps ?? 5) ? <button type="button" className="m-btn pw-more" onClick={() => setF(x => ({ ...x, steps: [...x.steps, ''] }))} data-tip="Add another thing it checks each time" data-testid="pw-step-add">+ Step</button> : null}</div>
      <div className="pw-segs"><span><small>FOR</small><span className="m-seg" role="radiogroup" aria-label="How many hours">{HOURS.map(h => <button key={h} type="button" role="radio" aria-checked={f.hours === h} className={f.hours === h ? 'active' : ''} onClick={() => setF(x => ({ ...x, hours: h }))} data-tip={`Watch for ${h} hour${h > 1 ? 's' : ''}, then file the report`} data-testid={`pw-h-${h}`}>{h}h</button>)}</span></span>
        <span><small>CHECKS AN HOUR</small><span className="m-seg" role="radiogroup" aria-label="Checks an hour">{PER.map(n => <button key={n} type="button" role="radio" aria-checked={f.perHour === n} className={f.perHour === n ? 'active' : ''} onClick={() => setF(x => ({ ...x, perHour: n }))} data-tip={`Every ${60 / n} minutes`} data-testid={`pw-p-${n}`}>{n}×</button>)}</span></span></div>
      <p className="pcl-cost" data-testid="pw-cost">💵 {cost} Nothing is posted.</p>
      <button type="submit" className="m-btn m-go" disabled={!!busy || !f.url.trim() || !steps.length || running >= max || !d?.model} data-testid="pw-go">{busy === 'add' ? 'First check…' : 'Start the watch'}</button>
    </form>
    {err ? <p className="lct-err" role="alert" data-testid="pw-err">⚠ {err}</p> : null}
    {watches.length ? <div className="pw-list">{watches.map((w, i) => <div key={w.id} style={{ '--i': i }} className="pw-in"><WatchCard w={w} now={now} busy={busy} act={act} onFolder={onFolder} /></div>)}</div>
      : <p className="pce-hint" data-testid="pw-empty">No watch yet. Give it a page and what to look for. It checks while the agent does other work and files a short report at the end.</p>}
  </div>;
}
