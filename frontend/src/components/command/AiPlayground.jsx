// 🧪 THE AI PLAYGROUND (Brain pane): ask a model to MAKE something — a card design, a chart theme, an animation, a mock-up — and see it
// live. The model writes one self-contained HTML document (ai_play.py); it runs in a sandboxed frame with NO same-origin (no cookies, no HQ
// session, no site storage) and the server injects a CSP that blocks all network. ✏ Change it = the model edits its own document.
import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import '../../styles/aiPlay.css';

const IDEAS = ['a neon trench chart background: grid floor rolling toward you, green swell on a buy', 'a holographic Fuse card that tilts and shimmers',
  'a rug-pull alarm animation for a dumping coin', 'a live "agents thinking" visual: ten nodes passing a coin down a chain'];

export function AiPlayground({ call, prov = 'auto' }) {
  const [items, setItems] = useState([]); const [sel, setSel] = useState(null); const [txt, setTxt] = useState(''); const [busy, setBusy] = useState(false);
  useEffect(() => { let on = true; Promise.resolve().then(() => call('/admin/ai/playground')).then(r => { if (on) { setItems(r.items || []); setSel(s => s || r.items?.[0]?.id || null); } }).catch(() => {}); return () => { on = false; }; }, [call]);
  const cur = items.find(x => x.id === sel) || null;
  const make = useCallback(async (from) => {
    const v = txt.trim(); if (v.length < 3 || busy) return;
    setBusy(true);
    try { const r = await call('/admin/ai/playground', { method: 'POST', body: JSON.stringify({ prompt: v, provider: prov, ...(from ? { from } : {}) }) });
      setItems(r.items || []); setSel(r.item?.id || null); setTxt(''); }
    catch (x) { toast.error(x.message); } finally { setBusy(false); }
  }, [txt, busy, call, prov]);
  return <div className="apg" data-testid="ai-playground">
    <div className="apg-stage">{cur ? <iframe key={cur.id} title={cur.prompt} className="apg-frame" sandbox="allow-scripts" srcDoc={cur.html} data-testid="apg-frame" />
      : <div className="apg-empty">{busy ? '⚙ the model is building it…' : 'Nothing made yet — ask for something below.'}</div>}
      {busy ? <i className="apg-scan" aria-hidden="true" /> : null}</div>
    <form className="apg-ask" onSubmit={e => { e.preventDefault(); make(null); }}>
      <input className="m-input" value={txt} onChange={e => setTxt(e.target.value)} placeholder="make me… (a chart theme, a card, an animation)" maxLength={800} data-testid="apg-input" />
      <button type="submit" className="m-btn m-go" disabled={busy || txt.trim().length < 3} data-testid="apg-make">{busy ? '…' : '🧪 Make'}</button>
      {cur ? <button type="button" className="m-btn" disabled={busy || txt.trim().length < 3} onClick={() => make(cur.id)} data-testid="apg-change" data-tip="The model edits THIS creation with your words">✏ Change it</button> : null}
    </form>
    {!items.length ? <div className="apg-ideas">{IDEAS.map(i => <button key={i} type="button" className="m-chip" onClick={() => setTxt(i)}>{i}</button>)}</div> : null}
    {items.length ? <ul className="apg-list">{items.map(x => <li key={x.id}><button type="button" className={x.id === sel ? 'active' : ''} onClick={() => setSel(x.id)} data-tip={`${x.by} · ${new Date(x.at * 1000).toLocaleString()}`}>{x.prompt}</button></li>)}</ul> : null}
    <small className="apg-note">Sandboxed: no network, no site access. Like one? Tell the Brain “🧱 build this” to queue it.</small>
  </div>;
}
