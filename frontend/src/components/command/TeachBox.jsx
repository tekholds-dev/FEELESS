import React, { useRef, useState } from 'react';
import { toast } from 'sonner';
import { hubLoad, useAi } from '../../lib/agentHub';
import { uploadImage } from '../../lib/adminCall';
import '../../styles/teachBox.css';

export const TEACH_KINDS = [['note', '💬 NOTE', 'how you trench — the model reads it with every coin'], ['narrative', '📖 NARRATIVE', 'what is hot and why — coins whose ticker / name carry its words get it'],
  ['chart', '📈 CHART', 'a chart lesson: the caption (+ a picture of the chart) — the model reads the caption']];
const ago = at => { const s = Math.max(0, Date.now() / 1000 - Number(at || 0)); return s < 60 ? `${Math.round(s)}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`; };

// 🎓 TEACH THE DESK: the creator's notes, narratives and chart lessons go into every fitting model read (the model teaches the agents
// through its graded reads); the 🎓 record = the model's reads on coins YOU taught, judged 15 min later like every other read.
export function TeachBox({ o, mint, sym, call, isOwner }) {
  const t = o?.teach || {}; const items = t.items || [];
  const [kind, setKind] = useState('note'); const [text, setText] = useState(''); const [img, setImg] = useState(null); const [onCoin, setOnCoin] = useState(false); const [busy, setBusy] = useState(false);
  const file = useRef(null);
  const rec = ((useAi(o?.ai) || {}).learn?.vitals || []).find(r => r.bucket === 'TAUGHT');
  const send = async (body, ok) => {
    setBusy(true);
    try { await call('/admin/agents', { method: 'POST', body: JSON.stringify({ teach: body }) }); await hubLoad(); if (ok) toast.success(ok); return true; }
    catch (e) { toast.error(e.message); return false; } finally { setBusy(false); }
  };
  const teach = async () => {
    if (text.trim().length < 3 || busy) return;
    if (await send({ kind, text, img: img || undefined, ...(onCoin && mint ? { mint, sym } : {}) }, 'taught — every fitting model read carries it from the next round')) { setText(''); setImg(null); }
  };
  const attach = async e => {
    const f = e.target.files?.[0]; e.target.value = '';
    if (!f) return;
    setBusy(true);
    try { setImg(await uploadImage(f)); setKind('chart'); } catch (er) { toast.error(er.message); } finally { setBusy(false); }
  };
  return <section className="tch" data-testid="teach-box">
    <header className="tch-head"><b>🎓 TEACH THE DESK</b><small>your words reach every fitting model read — the record says if it helps</small>
      {rec?.n ? <em className={rec.med > 0 ? 'is-up' : 'is-dn'} data-testid="teach-record">🎓 {rec.n} judged · {rec.med > 0 ? '+' : ''}{rec.med}%</em> : <em data-testid="teach-record">🎓 learning</em>}</header>
    <div className="m-seg tch-kinds" role="tablist" aria-label="What you are teaching">{TEACH_KINDS.map(([k, l, tip]) => <button key={k} type="button" role="tab" aria-selected={kind === k} className={kind === k ? 'active' : ''}
      onClick={() => setKind(k)} data-tip={tip} data-testid={`teach-kind-${k}`}>{l}<small>{(t.counts || {})[k] || 0}</small></button>)}</div>
    <div className="tch-write">
      <textarea className="m-input tch-text" value={text} maxLength={280} rows={2} disabled={!isOwner}
        placeholder={kind === 'narrative' ? 'e.g. frog season — frogs with a site + X keep running' : kind === 'chart' ? 'e.g. the entry was the first higher low after the bond dip' : 'e.g. never chase a +15% five-minute candle'}
        onChange={e => setText(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) teach(); }} data-testid="teach-text" />
      <div className="tch-row">
        <button type="button" className="m-btn tch-clip" disabled={!isOwner || busy} onClick={() => file.current?.click()} data-tip="attach a picture of the chart" data-testid="teach-attach">📎</button>
        <input ref={file} type="file" accept="image/png,image/jpeg,image/webp,image/gif" hidden onChange={attach} />
        {img ? <img className="tch-thumb" src={img} alt="your chart" /> : null}
        {mint ? <label className={`tch-coin ${onCoin ? 'is-on' : ''}`}><input type="checkbox" checked={onCoin} onChange={e => setOnCoin(e.target.checked)} data-testid="teach-oncoin" />on ${sym || mint.slice(0, 4)}</label> : null}
        <small className="tch-n">{text.length}/280</small>
        <button type="button" className="m-btn m-go tch-send" disabled={!isOwner || busy || text.trim().length < 3} aria-busy={busy} onClick={teach} data-testid="teach-send">TEACH ⏎</button></div>
    </div>
    {(t.narratives || []).length ? <p className="tch-words">{t.narratives.map(w => <i key={w}>#{w}</i>)}</p> : null}
    <ul className="tch-list" data-testid="teach-list">{items.slice(0, 8).map((x, i) => <li key={x.id} className={`is-${x.kind}`} style={{ '--i': i }}>
      <span className="tch-k">{x.kind === 'narrative' ? '📖' : x.kind === 'chart' ? '📈' : '💬'}</span>
      <p>{x.text}{x.sym ? <small> · ${x.sym}</small> : null}</p>
      {x.img ? <a href={x.img} target="_blank" rel="noreferrer"><img className="tch-thumb" src={x.img} alt="" /></a> : null}
      <small className="tch-age">{ago(x.at)}</small>
      {isOwner ? <button type="button" className="tch-x" aria-label="remove" onClick={() => send({ remove: x.id })} data-testid={`teach-rm-${x.id}`}>✕</button> : null}</li>)}</ul>
  </section>;
}
