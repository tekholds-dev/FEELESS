import React, { useState } from 'react';
import { apiUrl } from '../../lib/api';
import { agentAuth } from '../../lib/chatSession';
import { Ic3 } from '../../lib/icon3d';

// 🔑 RECOVERY KEY + 12 WORDS (owner 2026-11-04): either one brings this agent back if its wallet is lost. Shown once, we keep only a one-way hash, either can be rotated at any time. They control who owns the agent; they hold no money and are not a wallet seed.
const KINDS = [['phrase', '12 words', 'Easy to write down'], ['key', 'Recovery key', 'One long code']];
export function RecoveryKit({ cat, view }) {
  const [kit, setKit] = useState(view || cat?.recoveryView || {}); const [shown, setShown] = useState(null); const [saved, setSaved] = useState(false); const [err, setErr] = useState(''); const [copied, setCopied] = useState(false); const [confirm, setConfirm] = useState(null);
  if (!cat || cat.isLeader) return null;
  const make = async kind => { setErr(''); setConfirm(null);
    try { const r = await fetch(apiUrl(`/api/cats/${cat.id}/recovery-kit`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'recovery', text: kind, ...agentAuth() }) }); const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`); setShown(j); setKit(j.kit); setSaved(false); setCopied(false); } catch (e) { setErr(e.message); } };
  const copy = async () => { try { await navigator.clipboard.writeText(shown.secret); setCopied(true); } catch { /* it stays on screen */ } };
  return <section className="stp-rec" data-testid="recovery-kit"><h3><Ic3 e="🔑" size="24px" /> RECOVER IT</h3>
    {shown ? <div className="stp-rec-show" data-testid="recovery-show"><b>Write this down now. It will never show again.</b>
      {shown.kind === 'phrase' ? <ol className="stp-words">{shown.secret.split(' ').map((w, i) => <li key={i}><i>{i + 1}</i>{w}</li>)}</ol> : <code data-testid="recovery-code">{shown.secret}</code>}
      <small>It controls who owns this agent. It holds no money, and it is not a wallet seed: never put it in a wallet.</small>
      <span className="stp-row"><button type="button" className="m-btn" onClick={copy}>{copied ? 'Copied' : 'Copy'}</button><label className="stp-rec-ok"><input type="checkbox" checked={saved} onChange={e => setSaved(e.target.checked)} data-testid="recovery-saved" /> I saved it</label>{saved ? <button type="button" className="m-btn m-go" onClick={() => setShown(null)} data-testid="recovery-done">Done, hide it</button> : null}</span></div>
      : <div className="stp-rec-tiles">{KINDS.map(([k, t, x]) => { const has = kit?.[k]?.set; return <div key={k} className={`stp-rec-tile${has ? ' is-on' : ''}`} data-testid={`recovery-${k}`}><b>{t}</b><small>{has ? `Set ${new Date(kit[k].at * 1000).toLocaleDateString()}` : x}</small>
          {confirm === k ? <span className="stp-row"><button type="button" className="m-btn m-go" onClick={() => make(k)} data-testid={`recovery-yes-${k}`}>Yes, replace it</button><button type="button" className="m-btn" onClick={() => setConfirm(null)}>Keep it</button></span>
            : <button type="button" className={`m-btn${has ? '' : ' m-go'}`} onClick={() => (has ? setConfirm(k) : make(k))} data-tip={has ? 'Makes a new one. The old one stops working at once' : 'Shows it once'} data-testid={`recovery-make-${k}`}>{has ? 'Rotate' : 'Make it'}</button>}</div>; })}</div>}
    <p className="stp-rec-note">Lost your wallet? Sign in with a new one, then My agents › Recover an agent. After a recovery its wallet cannot pay out for 3 days.</p>
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</section>;
}
