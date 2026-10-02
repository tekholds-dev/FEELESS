import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { investigate } from '../CaseFile';
import '../../styles/fuseLab.css';

// HQ › Safety › 🛡 Bot shield: every known wallet through every bot engine. Flags feed reputation (bot −40 / watch −15),
// stop daily rewards, and zero Fuse creator cuts. Every flag cites its evidence; Clear / Confirm here always wins.
const ENGINE = { reward_farmer: '🎁 Reward farmer', clockwork: '⏱ Clockwork', batch_cluster: '🧩 Batch cluster', wash_trader: '🔁 Wash trader',
  dust_farmer: '🧂 Dust farmer', chat_spam: '📢 Chat spam', referral_farm: '👥 Referral farm', fuse_self_deal: '⚛️ Fuse self-deal' };
const LENS = [['flagged', 'Flagged'], ['bot', 'Bots'], ['watch', 'Watch'], ['all', 'All']];

export function BotShield({ call }) {
  const [lens, setLens] = useState('flagged'); const [d, setD] = useState(null); const [open, setOpen] = useState(null);
  const load = () => call(`/admin/shield?verdict=${lens}`).then(setD).catch(e => toast.error(e.message));
  useEffect(() => { setD(null); load(); }, [lens]); // eslint-disable-line react-hooks/exhaustive-deps
  const act = (address, action) => call('/admin/shield', { method: 'POST', body: JSON.stringify({ address, action }) }).then(() => { toast.success(action === 'cleared' ? 'Cleared — rewards + rep restored' : action === 'bot' ? 'Confirmed bot' : 'Back to automatic'); load(); }).catch(e => toast.error(e.message));
  return <section className="m-card m-live bsh" data-testid="bot-shield">
    <header className="bsh-head"><div><span className="m-label">🛡 BOT SHIELD · OUR DEFENDER</span><h3>Catch every farm. Cite every flag.</h3>
      <p className="m-dim">8 engines read FEELESS's own records. A flag lowers reputation (bot −40, watch −15), stops daily check-in rewards and zeroes Fuse creator cuts. Your Clear / Confirm always wins.</p></div>
      {d && <div className="bsh-counts"><span className="m-chip bad">{d.counts.bot} bots</span><span className="m-chip warn">{d.counts.watch} watch</span><span className="m-chip ok">{d.counts.clean} clean</span><small className="m-dim">{d.scanned} scanned</small></div>}</header>
    {d && <div className="bsh-engines">{Object.entries(ENGINE).map(([k, l]) => <div key={k} className={`bsh-engine ${d.engines[k] ? 'hot' : ''}`}><span>{l}</span><b className="m-num">{d.engines[k] || 0}</b></div>)}</div>}
    <div className="m-seg" role="radiogroup" aria-label="Show">{LENS.map(([k, l]) => <button type="button" key={k} role="radio" aria-checked={lens === k} className={lens === k ? 'active' : ''} onClick={() => setLens(k)}>{l}</button>)}</div>
    {!d ? <div className="fl-row is-ghost" /> : !d.rows.length ? <p className="m-dim">Nothing here — the shield is quiet.</p> : <div className="bsh-list">{d.rows.map(r => <article key={r.address} className={`bsh-row v-${r.verdict}`}>
      <button type="button" className="bsh-sum" aria-expanded={open === r.address} onClick={() => setOpen(o => (o === r.address ? null : r.address))}>
        <b className="m-num">{r.score}</b><code>{r.address.slice(0, 4)}…{r.address.slice(-4)}</code><span className="bsh-tags">{r.hits.map(h => <em key={h.engine}>{ENGINE[h.engine] || h.engine}</em>)}</span>
        <span className={`m-chip ${r.verdict === 'bot' ? 'bad' : r.verdict === 'watch' ? 'warn' : 'ok'}`}>{r.manual ? `${r.verdict} · manual` : r.verdict}</span></button>
      {open === r.address && <div className="bsh-detail">
        <ul>{r.hits.flatMap(h => h.evidence.map((e, i) => <li key={h.engine + i}><b>{ENGINE[h.engine]} · {h.score}</b><span>{e.claim}</span><small className="m-dim">{e.source}</small></li>))}</ul>
        <div className="bsh-acts"><button type="button" className="m-btn" onClick={() => investigate(r.address)}>🔎 Case file</button><a className="m-btn" href={`/terminal/profile/${r.address}`}>Profile</a>
          <button type="button" className="m-btn primary" onClick={() => act(r.address, 'cleared')}>Clear (human)</button><button type="button" className="m-btn danger" onClick={() => act(r.address, 'bot')}>Confirm bot</button>
          {r.manual && <button type="button" className="m-btn" onClick={() => act(r.address, 'reset')}>Back to auto</button>}</div></div>}
    </article>)}</div>}
  </section>;
}
