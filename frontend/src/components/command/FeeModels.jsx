import React, { useEffect, useState } from 'react';
import { useWallet } from '../../hooks/useWallet';
import { getChatSession } from '../../lib/chatSession';
import { apiUrl } from '../../lib/api';

// 🧠 FEE'S OWN MODELS (owner, 2026-10-30: "a way to add an OpenRouter model to FeeCat"): the creator picks 1–2 OpenRouter models for Fee, writes her
// prompt (any time — it's the creator's cat), and on a switch chooses KEEP her memory or start FRESH (the old memory is deleted, never mixed in).
// Her ☁ memory drawer shows what she kept (both models agreed) and what she decided. Every save is the creator's signed wallet (the server checks).
export function FeeModels() {
  const { wallet, signMessage } = useWallet() || {};
  const [cat, setCat] = useState(null); const [list, setList] = useState([]); const [pick, setPick] = useState(['', '']); const [text, setText] = useState('');
  const [memory, setMemory] = useState('keep'); const [busy, setBusy] = useState(false); const [msg, setMsg] = useState(null);
  const load = () => fetch(apiUrl('/api/cats/leader')).then(r => r.json()).then(d => { setCat(d.cat); const b = d.cat?.brainsCfg; if (b?.brains) { setPick([b.brains[0] || '', b.brains[1] || '']); setText(b.prompt || ''); } }).catch(() => {});
  useEffect(() => { load(); fetch(apiUrl('/api/cats/models')).then(r => r.json()).then(d => setList((d.models || []).filter(m => m.tools).sort((a, b) => (b.intel ?? -1) - (a.intel ?? -1)).slice(0, 60))).catch(() => {}); }, []);
  const b = cat?.brainsCfg; const had = !!b?.brains?.length;
  const send = async body => {
    const address = wallet?.address; if (!address) { setMsg({ ok: false, t: 'Connect your creator wallet first.' }); return; }
    setBusy(true); setMsg(null);
    try {
      const session = await getChatSession(address, signMessage, { own: true });
      const r = await fetch(apiUrl('/api/cats/leader/action'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...body, address, session }) });
      const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`);
      setMsg({ ok: true, t: '✓ saved — she uses it from her next decision' }); load();
    } catch (e) { setMsg({ ok: false, t: e.message }); } finally { setBusy(false); }
  };
  const brains = pick.filter(Boolean);
  return <section className="fmd" data-testid="fee-models">
    <header><b>🧠 HER MODELS</b><small>{had ? `${b.brains.map(x => x.split('/').pop()).join(' + ')} · ${(b.decisions || []).length} decisions` : 'rules + FeeCat AI today — add an OpenRouter model'}</small></header>
    <div className="fmd-pick">{[0, 1].map(i => <label key={i}><em>MODEL {'AB'[i]}</em><select className="m-input" value={pick[i]} onChange={e => setPick(p => (i ? [p[0], e.target.value] : [e.target.value, p[1]]))} data-testid={`fmd-model-${i}`}>
      <option value="">{i ? 'no second model' : 'pick a model'}</option>{list.map(m => <option key={m.id} value={m.id}>{m.name} · ♟ {m.intel ?? '—'} · {m.perDecision ? `$${m.perDecision.toFixed(4)}/call` : 'free'}</option>)}</select></label>)}</div>
    <label className="fmd-prompt"><em>HER PROMPT</em><textarea className="m-input" rows={3} maxLength={1200} value={text} onChange={e => setText(e.target.value)} placeholder="How she trades — e.g. trade the trenches like a desk, buy germ floors with buyers leading, bank in pieces, never chase." data-testid="fmd-prompt" /></label>
    {had ? <div className="m-seg fmd-mem" role="radiogroup" aria-label="Her memory when the models change">{[['keep', '☁ KEEP HER MEMORY'], ['fresh', '🧹 START FRESH (delete old)']].map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={memory === k} className={memory === k ? 'is-on' : ''} onClick={() => setMemory(k)} data-testid={`fmd-mem-${k}`}>{l}</button>)}</div> : null}
    <span className="fmd-acts"><button type="button" className="m-btn m-go" disabled={busy || !brains.length} onClick={() => send({ action: 'models', brains, text, memory })} data-testid="fmd-save">{had ? 'Save models + prompt' : 'Give her this model'}</button>
      {had ? <button type="button" className="m-btn" disabled={busy || text.trim().length < 20 || text === b.prompt} onClick={() => send({ action: 'brief', text })}>Save prompt only</button> : null}</span>
    {msg ? <p className={`fmd-msg ${msg.ok ? 'is-ok' : 'is-bad'}`} role="status">{msg.t}</p> : null}
    {had ? <details className="fmd-cloud" data-testid="fmd-cloud"><summary>☁ HER MEMORY · {(b.cloud || []).length} kept · {(b.decisions || []).length} decisions</summary>
      <ul>{(b.cloud || []).slice(-12).reverse().map((c, i) => <li key={i}>{c.text || `${c.word} $${c.sym}${c.why ? ` — ${c.why}` : ''}`}</li>)}{!(b.cloud || []).length ? <li className="is-empty">nothing kept yet — a call lands here when both models agree</li> : null}</ul></details> : null}
  </section>;
}
