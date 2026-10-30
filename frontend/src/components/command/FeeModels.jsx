import React, { useEffect, useState } from 'react';
import { useWallet } from '../../hooks/useWallet';
import { getChatSession } from '../../lib/chatSession';
import { apiUrl } from '../../lib/api';
import { ModelPop } from './LaunchCat';

// 🧠 FEE'S OWN MODELS (owner, 2026-10-30): the creator picks Fee's models from the FULL smart list in a pop-out (search · cheapest · $ range ·
// categories), never a dropdown. Model A is her LEAD — it makes every buy / sell call; NEXA (FeeCat AI) helps: her read rides inside every case
// the lead sees. Model B is an optional second opinion. On a switch: KEEP her memory, let the NEW MODEL SORT it (keeps what still helps, drops the
// rest), or START FRESH. Every save is the creator's signed wallet (the server checks).
const MEMORY = [['keep', '☁ KEEP HER MEMORY'], ['sort', '🧠 NEW MODEL SORTS IT'], ['fresh', '🧹 START FRESH']];
const short = id => String(id || '').split('/').pop();


export function FeeModels() {
  const { wallet, signMessage } = useWallet() || {};
  const [cat, setCat] = useState(null); const [d, setD] = useState(null); const [pick, setPick] = useState(['', '']); const [text, setText] = useState('');
  const [memory, setMemory] = useState('keep'); const [busy, setBusy] = useState(false); const [msg, setMsg] = useState(null); const [open, setOpen] = useState(-1);
  const load = () => fetch(apiUrl('/api/cats/leader')).then(r => r.json()).then(x => { setCat(x.cat); const b = x.cat?.brainsCfg; if (b?.brains) { setPick([b.brains[0] || '', b.brains[1] || '']); setText(b.prompt || ''); } }).catch(() => {});
  useEffect(() => { load(); fetch(apiUrl('/api/cats/models')).then(r => r.json()).then(setD).catch(() => {}); }, []);
  const b = cat?.brainsCfg; const had = !!b?.brains?.length;
  const row = id => (d?.models || []).find(m => m.id === id);
  const send = async body => {
    const address = wallet?.address; if (!address) { setMsg({ ok: false, t: 'Connect your creator wallet first.' }); return; }
    setBusy(true); setMsg(null);
    try {
      const session = await getChatSession(address, signMessage, { own: true });
      const r = await fetch(apiUrl('/api/cats/leader/action'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...body, address, session }) });
      const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`);
      setMsg({ ok: true, t: body.memory === 'sort' ? '✓ saved — the new lead is sorting her cloud now' : '✓ saved — she uses it from her next decision' }); load();
    } catch (e) { setMsg({ ok: false, t: e.message }); } finally { setBusy(false); }
  };
  const brains = pick.filter(Boolean);
  const slot = i => { const m = row(pick[i]);
    return <div className={`fmd-slot${pick[i] ? ' is-on' : ''}`} key={i}>
      <em>{i ? 'MODEL B · SECOND OPINION (optional)' : 'MODEL A · HER LEAD — makes every call'}</em>
      {pick[i] ? <span className="fmd-slot-m"><b>{m?.name || short(pick[i])}</b><small>{m ? `♟ ${m.intel ?? '—'} · ${m.perDecision ? `$${m.perDecision.toFixed(4)} a decision` : 'free'}` : pick[i]}</small></span>
        : <span className="fmd-slot-m"><b>{i ? 'no second model' : 'no lead yet'}</b><small>{i ? 'NEXA already helps — add one only for a second opinion' : 'pick a smart, cheap model'}</small></span>}
      <span className="fmd-slot-acts"><button type="button" className="m-btn" onClick={() => setOpen(i)} disabled={!d} data-testid={`fmd-open-${i}`} data-tip="Open the full model list">{pick[i] ? 'Change' : 'Pick from the list'}</button>
        {i && pick[i] ? <button type="button" className="m-btn" onClick={() => setPick(p => [p[0], ''])} data-testid="fmd-drop-1">Drop</button> : null}</span>
    </div>; };
  return <section className="fmd" data-testid="fee-models">
    <header><b>🧠 HER MODELS</b><small>{had ? `${b.brains.map(short).join(' + ')} · ${(b.decisions || []).length} decisions` : 'rules + NEXA today — give her an OpenRouter lead'}</small></header>
    <div className="fmd-pick">{slot(0)}{slot(1)}</div>
    <p className="fmd-nexa" data-tip="NEXA (FeeCat AI) reads every coin first — her read rides inside the case the lead decides on">🤝 <b>NEXA helps</b> — her read of every coin rides in the case your lead model decides on.</p>
    <label className="fmd-prompt"><em>HER PROMPT</em><textarea className="m-input" rows={3} maxLength={1200} value={text} onChange={e => setText(e.target.value)} placeholder="How she trades — e.g. trade the trenches like a desk, buy germ floors with buyers leading, bank in pieces, never chase." data-testid="fmd-prompt" /></label>
    {had ? <div className="m-seg fmd-mem" role="radiogroup" aria-label="Her memory when the models change">{MEMORY.map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={memory === k} className={memory === k ? 'is-on' : ''} onClick={() => setMemory(k)} data-testid={`fmd-mem-${k}`}>{l}</button>)}</div> : null}
    <span className="fmd-acts"><button type="button" className="m-btn m-go" disabled={busy || !pick[0]} onClick={() => send({ action: 'models', brains, text, memory })} data-testid="fmd-save">{had ? 'Save models + prompt' : 'Make it her lead'}</button>
      {had ? <button type="button" className="m-btn" disabled={busy || text.trim().length < 20 || text === b.prompt} onClick={() => send({ action: 'brief', text })}>Save prompt only</button> : null}</span>
    {msg ? <p className={`fmd-msg ${msg.ok ? 'is-ok' : 'is-bad'}`} role="status">{msg.t}</p> : null}
    {had ? <details className="fmd-cloud" data-testid="fmd-cloud"><summary>☁ HER MEMORY · {(b.cloud || []).length} kept · {(b.decisions || []).length} decisions</summary>
      <ul>{(b.cloud || []).slice(-12).reverse().map((c, i) => <li key={i}>{c.text || `${c.word} $${c.sym}${c.why ? ` — ${c.why}` : ''}`}</li>)}{!(b.cloud || []).length ? <li className="is-empty">nothing kept yet — a call lands here when both models agree</li> : null}</ul></details> : null}
    {open >= 0 ? <ModelPop d={d} title={open ? '🧠 MODEL B · SECOND OPINION' : '👑 MODEL A · HER LEAD'} picked={pick.filter(Boolean).map(id => ({ id }))} onPick={id => setPick(p => (open ? [p[0], id === p[0] ? '' : id] : [id, p[1] === id ? '' : p[1]]))} onClose={() => setOpen(-1)} /> : null}
  </section>;
}
