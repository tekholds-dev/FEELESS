import React, { useEffect, useMemo, useState } from 'react';

// 📂 AGT-21: its agent works in YOUR repo. Pick files, then Ask (it reads them and answers, naming file and line) or Change one file (it rewrites
// it, you see the diff, and only Send puts it on a branch of its own: feeless/edit-…; your main is never touched). Each shows its price first.
const money = n => (n == null ? 'price not listed' : n === 0 ? 'free' : n < 0.01 ? `≈$${n.toFixed(4)}` : `≈$${n.toFixed(2)}`);
export function ProjectWork({ project, ask }) {
  const [mode, setMode] = useState('ask'); const [q, setQ] = useState(''); const [picked, setPicked] = useState([]); const [text, setText] = useState('');
  const [price, setPrice] = useState(null); const [busy, setBusy] = useState(''); const [err, setErr] = useState(''); const [out, setOut] = useState(null);
  const paths = project?.paths || []; const max = mode === 'ask' ? 8 : 1;
  const hits = useMemo(() => { const w = q.trim().toLowerCase(); return w ? paths.filter(x => x.toLowerCase().includes(w) && !picked.includes(x)).slice(0, 8) : []; }, [q, paths, picked]);
  const sel = picked.slice(0, max); const key = sel.join('|');
  useEffect(() => { setPrice(null); if (!sel.length) return undefined; const t = setTimeout(() => { ask({ op: mode === 'ask' ? 'project_ask' : 'project_edit', tools: { [mode === 'ask' ? 'paths' : 'path']: mode === 'ask' ? sel : sel[0], dry: true } }).then(setPrice).catch(e => setErr(e.message)); }, 300); return () => clearTimeout(t); }, [key, mode]);   // eslint-disable-line react-hooks/exhaustive-deps
  const go = async () => { setBusy('go'); setErr(''); setOut(null); try { setOut({ mode, ...(await ask({ op: mode === 'ask' ? 'project_ask' : 'project_edit', text: text.trim(), tools: mode === 'ask' ? { paths: sel } : { path: sel[0] } })) }); } catch (e) { setErr(e.message); } setBusy(''); };
  const send = async () => { setBusy('send'); setErr(''); try { const j = await ask({ op: 'project_edit_send', job: out.draft }); setOut(o => ({ ...o, sent: j.sent })); } catch (e) { setErr(e.message); } setBusy(''); };
  return <div className="pjw" data-testid="project-work">
    <span className="m-seg" role="radiogroup" aria-label="What its agent does">{[['ask', 'Ask about files'], ['edit', 'Change a file']].map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={mode === k} className={mode === k ? 'active' : ''} onClick={() => { setMode(k); setOut(null); }} data-testid={`pjw-${k}`}>{l}</button>)}</span>
    <div className="pjw-pick"><input className="m-input" value={q} onChange={e => setQ(e.target.value)} placeholder={`Find a file in ${project.full} (${paths.length} listed)`} aria-label="Find a file" data-testid="pjw-find" />
      {hits.length ? <ul className="pjw-hits" role="listbox">{hits.map(x => <li key={x}><button type="button" role="option" aria-selected="false" onClick={() => { setPicked(p => (mode === 'edit' ? [x] : [...p, x].slice(0, 8))); setQ(''); }} data-testid={`pjw-hit-${x}`}>{x}</button></li>)}</ul> : null}
      {sel.length ? <span className="pjw-chips">{sel.map(x => <button key={x} type="button" className="m-chip" onClick={() => setPicked(p => p.filter(y => y !== x))} aria-label={`Take out ${x}`} data-tip="Take it out">{x} ✕</button>)}</span> : <small className="pjw-hint">{mode === 'ask' ? 'Pick up to 8 files it should read.' : 'Pick the one file to change.'} Secret-looking files are never listed.</small>}</div>
    <form className="pjw-ask" onSubmit={e => { e.preventDefault(); if (text.trim() && sel.length) go(); }}><input className="m-input" value={text} onChange={e => setText(e.target.value)} maxLength={800} placeholder={mode === 'ask' ? 'Where is the login checked? Why is this slow?' : 'Add a dark mode toggle, rename fetchUser to loadUser…'} aria-label={mode === 'ask' ? 'Your question' : 'The change'} data-testid="pjw-text" />
      <button type="submit" className="m-btn m-go" disabled={!!busy || !text.trim() || !sel.length} data-tip={price?.model ? `${price.model} reads ${sel.length} file${sel.length === 1 ? '' : 's'}. OpenRouter's own rate for this much text` : 'Pick a file first'} data-testid="pjw-go">{busy === 'go' ? (mode === 'ask' ? 'Reading…' : 'Rewriting…') : `${mode === 'ask' ? 'Ask' : 'Rewrite it'}${sel.length ? ` · ${money(price?.usd)}` : ''}`}</button></form>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
    {out?.mode === 'ask' && out.said ? <div className="pjw-said" data-testid="pjw-said"><p>{out.said}</p><small className="m-num">read {out.read?.join(', ')} · ${Number(out.usd || 0).toFixed(4)}</small></div> : null}
    {out?.mode === 'edit' && out.diff ? <div className="pjw-diff" data-testid="pjw-diff"><header><b>{out.path}</b><em className="m-num is-add">+{out.added}</em><em className="m-num is-rem">−{out.removed}</em><small className="m-num">${Number(out.usd || 0).toFixed(4)}</small></header>
      <pre>{out.diff.split('\n').map((l, i) => <span key={i} className={l.startsWith('+') && !l.startsWith('+++') ? 'is-add' : l.startsWith('-') && !l.startsWith('---') ? 'is-rem' : l.startsWith('@@') ? 'is-hunk' : ''}>{l}{'\n'}</span>)}</pre>
      {out.sent ? <p className="pjw-sent" data-testid="pjw-sent">✓ On its own branch <a href={out.sent.url} target="_blank" rel="noopener noreferrer">{out.sent.branch} ↗</a>. Review it on GitHub; your {project.branch} is untouched.</p>
        : <span className="pjw-do"><button type="button" className="m-btn m-go" disabled={!!busy} onClick={send} data-tip={`Puts this one file on a new branch. Never ${project.branch}`} data-testid="pjw-send">{busy === 'send' ? 'Sending…' : 'Send to its own branch'}</button><button type="button" className="m-btn" onClick={() => setOut(null)} data-testid="pjw-discard">Discard</button></span>}</div> : null}
  </div>;
}
