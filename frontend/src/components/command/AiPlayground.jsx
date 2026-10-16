// 🧩 THE CODE LAB (Brain pane; owner, 2026-10-14: "playground should preview code and new code I can approve to FEELESS or agents").
// Pick a part of FEELESS, say what to change; a model proposes ONE change (it is shown that file's real outline) → you see the code with
// a PREVIEW first (before → after diff against the real file; a live mock-up for UI changes), why and the risk → ✅ Approve files it to the build queue (Claude Code applies it with tests) · ✕ Drop · ✏ Change it.
// Nothing here writes a file; no model touches the repo.
import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import '../../styles/aiPlay.css';

const IDEAS = { reaper: 'hold a winner one more read when buyers still lead the tape', agents: 'Devil should object to a coin whose dev sold in the last 5 min',
  ranking: 'rank coins with a site AND X a little higher', cockpit: 'show each seat’s snapshot count (📸 1/2) on its card', home: 'add the coin’s 5-minute sparkline to the spotlight' };

// only code proposals (the retired HTML playground left items with no code / status in the same file) — each with a status
export const codeOnly = items => (items || []).filter(x => x && x.code).map(x => ({ ...x, status: x.status || 'proposed', title: x.title || 'code change', file: x.file || '' }));

// 🖼 the change as it will READ in the file: before on the left, after on the right, line for line (a unified diff → paired rows). Pure.
export function sideBySide(diff) {
  const rows = []; let del = []; let add = [];
  const flush = () => { const m = Math.max(del.length, add.length); for (let i = 0; i < m; i++) rows.push([del[i] ?? null, add[i] ?? null, del[i] != null && add[i] != null ? 'chg' : del[i] != null ? 'del' : 'add']); del = []; add = []; };
  String(diff || '').split('\n').forEach(l => {
    if (l.startsWith('+++') || l.startsWith('---')) return;
    if (l.startsWith('@@')) { flush(); rows.push([l, l, 'at']); return; }
    if (l.startsWith('-')) { del.push(l.slice(1)); return; }
    if (l.startsWith('+')) { add.push(l.slice(1)); return; }
    flush(); rows.push([l.slice(1), l.slice(1), 'same']);
  });
  flush(); return rows;
}

export function AiPlayground({ call, prov = 'auto' }) {
  const [items, setItems] = useState([]); const [targets, setTargets] = useState([]); const [target, setTarget] = useState('reaper');
  const [sel, setSel] = useState(null); const [txt, setTxt] = useState(''); const [busy, setBusy] = useState(false); const [view, setView] = useState('diff');
  useEffect(() => { let on = true; Promise.resolve().then(() => call('/admin/ai/playground')).then(r => { if (on) { setItems(codeOnly(r.items)); setTargets(r.targets || []); setSel(s => s || r.items?.[0]?.id || null); } }).catch(() => {}); return () => { on = false; }; }, [call]);
  const cur = items.find(x => x.id === sel) || null;
  const make = useCallback(async from => {
    const v = txt.trim(); if (v.length < 3 || busy) return;
    setBusy(true);
    try { const r = await call('/admin/ai/playground', { method: 'POST', body: JSON.stringify({ prompt: v, target: from ? cur?.target || target : target, provider: prov, ...(from ? { from } : {}) }) });
      setItems(codeOnly(r.items)); setSel(r.item?.id || null); setTxt(''); setView(r.item?.preview ? 'look' : r.item?.diff ? 'side' : r.item?.run ? 'run' : 'diff'); }
    catch (x) { toast.error(x.message); } finally { setBusy(false); }
  }, [txt, busy, call, prov, target, cur]);
  const decide = async approve => {
    if (!cur || busy) return; setBusy(true);
    try { const r = await call('/admin/ai/playground/decide', { method: 'POST', body: JSON.stringify({ id: cur.id, approve }) }); setItems(codeOnly(r.items));
      toast.success(approve ? `✅ approved → build queue ${r.item?.build || ''} — say "build the queue" to Claude` : '✕ dropped'); }
    catch (x) { toast.error(x.message); } finally { setBusy(false); }
  };
  const lines = String(cur?.code || '').split('\n');
  return <div className="apg" data-testid="ai-playground">
    <div className="apg-targets" role="radiogroup" aria-label="Part of FEELESS">{targets.map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={target === k}
      className={target === k ? 'active' : ''} onClick={() => setTarget(k)} data-testid={`apg-t-${k}`} data-tip={l}>{l.split(' — ')[0]}</button>)}</div>
    <form className="apg-ask" onSubmit={e => { e.preventDefault(); make(null); }}>
      <input className="m-input" value={txt} onChange={e => setTxt(e.target.value)} placeholder={IDEAS[target] || 'what should change?'} maxLength={900} data-testid="apg-input" />
      <button type="submit" className="m-btn m-go" disabled={busy || txt.trim().length < 3} data-testid="apg-make">{busy ? '⚙ writing…' : '🧩 Propose'}</button>
      {cur && cur.status === 'proposed' ? <button type="button" className="m-btn" disabled={busy || txt.trim().length < 3} onClick={() => make(cur.id)} data-testid="apg-change" data-tip="The model rewrites THIS proposal with your words">✏ Change it</button> : null}
    </form>
    {cur ? <div className={`apg-prop is-${cur.status}`} data-testid="apg-prop">
      <div className="apg-phead"><b>{cur.title}</b><em>{cur.kind === 'new' ? 'NEW' : 'CHANGE'} · {cur.file}</em><span className={`apg-st is-${cur.status}`}>{cur.status.toUpperCase()}</span></div>
      <p className="apg-why"><b>WHY</b> {cur.why}</p>{cur.risk ? <p className="apg-why is-risk"><b>RISK</b> {cur.risk}</p> : null}
      <div className="apg-views" role="tablist" aria-label="Preview">{[['diff', `🔍 Before → after${cur.changed?.length || cur.new?.length ? ` · ${(cur.changed || []).length} changed · ${(cur.new || []).length} new` : ''}`], ...(cur.preview ? [['look', '🖼 See it working']] : []), ...(cur.diff ? [['side', '🪞 Side by side']] : []), ...(cur.run ? [['run', cur.run.ran ? `▶ Test run · ${cur.run.results.filter(x => x.ok).length}/${cur.run.results.length} ✓` : '▶ Test run · not run']] : []), ['code', '📄 Full code']].map(([k, l]) =>
        <button key={k} type="button" role="tab" aria-selected={view === k} className={view === k ? 'active' : ''} onClick={() => setView(k)} data-testid={`apg-v-${k}`}>{l}</button>)}</div>
      {view === 'run' && cur.run ? <div className="apg-run" data-testid="apg-run">{cur.run.ran ? <ul>{cur.run.results.map((x, i) => <li key={i} className={x.err ? 'is-err' : x.ok === false ? 'is-bad' : x.ok ? 'is-ok' : ''}>
          <code>{x.call}</code><span>→ {x.err ? x.err : <b>{x.got}</b>}</span>{x.expect != null && !x.err ? <small>{x.ok ? '✓ as expected' : `✗ expected ${JSON.stringify(x.expect)}`}</small> : null}</li>)}</ul>
          : <p>Not run: {cur.run.why}</p>}<small className="apg-note">ran in a locked sandbox: no network, no files, 4s, pure functions only</small></div>
        : view === 'look' && cur.preview ? <iframe className="apg-look" title={`${cur.title} preview`} sandbox="allow-scripts" srcDoc={cur.preview} data-testid="apg-look" />
        : view === 'side' && cur.diff ? <div className="apg-side" data-testid="apg-side"><div className="apg-sh"><b>BEFORE · now in {cur.file}</b><b>AFTER · if you approve</b></div>
          {sideBySide(cur.diff).map(([a, b, k], i) => <div key={i} className={`apg-sr is-${k}`} style={{ '--i': Math.min(i, 40) }}><code>{a ?? ''}</code><code>{b ?? ''}</code></div>)}</div>
        : view === 'diff' && cur.diff ? <pre className="apg-code is-diff" data-testid="apg-diff">{String(cur.diff).split('\n').map((l, i) => <span key={i} className={l.startsWith('+++') || l.startsWith('---') ? 'is-h' : l.startsWith('@@') ? 'is-at' : l.startsWith('+') ? 'is-add' : l.startsWith('-') ? 'is-del' : ''}>{l || ' '}{'\n'}</span>)}</pre>
        : <pre className="apg-code" data-testid="apg-code">{lines.map((l, i) => <span key={i}><i>{i + 1}</i>{l || ' '}{'\n'}</span>)}</pre>}
      {cur.status === 'proposed' ? <div className="apg-act"><button type="button" className="m-btn m-go" disabled={busy} onClick={() => decide(true)} data-testid="apg-approve">✅ Approve → build queue</button>
        <button type="button" className="m-btn" disabled={busy} onClick={() => decide(false)} data-testid="apg-drop">✕ Drop</button>
        <small>approving writes nothing yet — Claude Code applies it with tests when you say “build the queue”</small></div>
        : <small className="apg-note">{cur.status === 'approved' ? `✅ in the build queue${cur.build ? ` (${cur.build})` : ''}` : '✕ dropped'}</small>}
    </div> : <div className="apg-empty">{busy ? '⚙ the model is writing it…' : 'Pick a part of FEELESS, say what to change — the model proposes the code, you approve it.'}</div>}
    {items.length ? <ul className="apg-list">{items.map(x => <li key={x.id}><button type="button" className={`${x.id === sel ? 'active' : ''} is-${x.status}`} onClick={() => setSel(x.id)} data-tip={`${x.file} · ${x.by}`}>{x.status === 'approved' ? '✅ ' : x.status === 'dropped' ? '✕ ' : ''}{x.title}</button></li>)}</ul> : null}
  </div>;
}
