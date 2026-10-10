import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { openCoin } from '../CoinDrawer';
import '../../styles/agentDesk.css';

// 🤖 HQ › AGENTS (owner, 2026-10-09: "code your own agents to learn trading and trenching — one tracks the numbers, one knows why they
// moved, one knows exactly when to enter, one argues it's right or not; none can work without the others; start by conquering the 5 min").
// GET /admin/agents every 20s: the four agents as cards with their OWN scorecard, the stage (5 → 15 → 60 min), the live table (every
// coin with each agent's word in order: numbers → why → call → argument → GO), the team's $20 paper desk, and the one owner switch that
// lets proven GO calls feed the real card's rush. A record, never a promise.
const pct = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);
const tone = v => (v == null ? '' : v > 0 ? 'm-pos' : v < 0 ? 'm-neg' : '');
const CALL = { enter: ['ENTER', 'is-go'], wait: ['WAIT', 'is-wait'], skip: ['SKIP', 'is-no'] };
const VERDICT = { agree: ['agrees', 'is-go'], object: ['objects', 'is-no'], '—': ['—', ''] };
export const agentLine = a => (a.n ? `${a.n} judged · ${pct(a.med)} typical at 5 min${a.right != null ? ` · ${a.right}% right` : ''}` : 'no judged calls yet — every call is checked 5 minutes later');

export function AgentDesk({ call }) {
  const [d, setD] = useState(null); const [busy, setBusy] = useState(false);
  const load = useCallback(() => call('/admin/agents').then(setD).catch(e => toast.error(e.message)), [call]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 20000); return () => clearInterval(t); }, [load]);
  if (!d) return <p className="cc-empty">Waking the agents…</p>;
  const st = d.stage || {};
  const feed = async v => { setBusy(true); try { await call('/admin/agents', { method: 'POST', body: JSON.stringify({ feed: v }) }); toast.success(v ? '🤖 Agents may feed your card once proven' : '🤖 Agents stay on paper'); load(); } catch (e) { toast.error(e.message); } finally { setBusy(false); } };
  return <section className="agd m-live" data-testid="agent-desk">
    <header className="agd-head"><div><b>🤖 THE AGENT DESK</b><small>Four agents, one chain — none of them can call a trade without the other three. Every call is checked 5 minutes later; they move to 15 min only after they conquer 5.</small></div>
      <div className="agd-stage" data-testid="agd-stage">{[5, 15, 60].map(h => <span key={h} className={(st.conquered || []).includes(h) ? 'is-done' : st.h === h ? 'is-now' : ''}>{(st.conquered || []).includes(h) ? '✓' : st.h === h ? '⚔' : '🔒'} {h}m</span>)}
        <small>{st.team?.n ? `team ${st.team.n}/${st.needN} judged · ${pct(st.team.med)} · ${st.team.won}% won (needs ${st.needWin}%)` : `needs ${st.needN} judged GO calls, a positive median and ${st.needWin}% won`}</small></div></header>
    <div className="agd-chain">{(d.agents || []).map((a, i) => <React.Fragment key={a.key}><div className={`agd-agent is-${a.key}`} style={{ '--i': i }} data-testid={`agent-${a.key}`}>
      <span className="agd-ico" aria-hidden>{a.icon}</span><b>{a.name}</b><small>{a.job}</small>
      <em className={tone(a.med)}>{a.n ? pct(a.med) : '—'}</em><i>{agentLine(a)}</i></div>{i < 3 && <span className="agd-arrow" aria-hidden>→</span>}</React.Fragment>)}</div>
    <div className="agd-row2">
      <div className="agd-box" data-testid="agd-desk"><b>📜 PAPER DESK · $5 a GO, out at 5 min</b><p className={`agd-big ${tone(d.desk.now - d.desk.start)}`}>${d.desk.now.toFixed(2)} <small>from ${d.desk.start} · {d.desk.trades} trades</small></p>
        <small className="m-dim">Control group (coins Trigger said WAIT): {d.control?.n ? `${pct(d.control.med)} typical` : 'not judged yet'} — the team must beat this to mean anything. Slippage on a 5-min scalp is not modelled.</small></div>
      <div className="agd-box" data-testid="agd-drivers"><b>🔍 WHAT SHERLOCK LEARNED</b>{(d.drivers || []).length ? <ul>{d.drivers.slice(0, 7).map(x => <li key={x.key}><span>{x.words}</span><em className={tone(x.med)}>{pct(x.med)}</em><small>n {x.n}</small></li>)}</ul> : <small className="m-dim">Nothing judged yet — drivers start from their priors.</small>}</div>
      <div className="agd-box" data-testid="agd-feed"><b>💵 YOUR REAL CARD</b><p className="m-dim">{d.proven5 ? 'The 5-minute stage is conquered. Their GO calls can go first in your card\'s rush (small tickets, every keeper check still runs).' : 'Paper only until they conquer the 5-minute stage. You can switch this on now — it starts the day they prove it.'}</p>
        <div className="m-seg"><button type="button" disabled={busy} className={d.feedAsked ? 'active' : ''} onClick={() => feed(true)} data-testid="agd-feed-on">Feed my card</button><button type="button" disabled={busy} className={!d.feedAsked ? 'active' : ''} onClick={() => feed(false)} data-testid="agd-feed-off">Paper only</button></div>
        <small className="m-dim">Trigger's bar right now: lean ≥ {d.bar} · {d.open} calls waiting to be judged</small></div>
    </div>
    <div className="agd-table" data-testid="agd-table"><div className="agd-th"><span>coin</span><span>📊 Tally</span><span>🔍 Sherlock</span><span>⏱ Trigger</span><span>⚖ Devil</span><span /></div>
      {(d.table || []).map(x => { const c = CALL[x.trigger[0]] || ['', '']; const v = VERDICT[x.devil[0]] || ['', ''];
        return <div key={x.mint} className={`agd-tr ${x.go ? 'is-go' : ''}`} data-testid={`agd-row-${x.symbol}`}>
          <button type="button" className="agd-sym" onClick={() => openCoin({ mint: x.mint, pairAddress: x.pair, symbol: x.symbol })}>${x.symbol}</button>
          <span className="agd-nums"><em className={tone(x.nums.d5)}>{pct(x.nums.d5)} 5m</em>{x.nums.pace != null ? ` · pace ${x.nums.pace}×` : ''}{x.nums.buy != null ? ` · ${Math.round(x.nums.buy)}% buys` : ''}</span>
          <span className="agd-why">{x.why.drivers.length ? x.why.drivers.slice(0, 2).map(dd => <i key={dd[0]} className={dd[1] >= 0 ? 'is-up' : 'is-dn'}>{dd[2]}</i>) : <i>nothing moving it</i>}</span>
          <span className={`agd-call ${c[1]}`} data-tip={x.trigger[1]}>{c[0]}</span>
          <span className={`agd-call ${v[1]}`} data-tip={x.devil[1] || ''}>{v[0]}{x.devil[1] && x.devil[0] === 'object' ? <small>{x.devil[1]}</small> : null}</span>
          <span className="agd-go">{x.go ? '🟢 GO' : ''}</span></div>; })}
      {!(d.table || []).length && <small className="m-dim">The first pass runs within a minute of the backend starting.</small>}</div>
  </section>;
}
