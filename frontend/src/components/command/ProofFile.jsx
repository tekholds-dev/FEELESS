import React, { useMemo, useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { agentAuthQuery } from '../../lib/chatSession';
import '../../styles/proofFile.css';

// 🗂 SLICE 14 · A PROOF FILE SHOWS EVERYTHING (owner 2026-11-18: "no proof should look like this in git: the snapshots and all logs need to
// show, plus the wired info from each"). Reads the `fileRecord` the backend writes into every proof file (backend/proof_file.py): the true
// record, each page's snapshot, the step log, kits, judge reviews, the bid or trade with its receipt, and a link back to its proof window.
// An old file shows what it has, and every part it never recorded is named in plain words. Nothing is computed here but sums for the bars.
export const OPEN_PROOF = 'feeless:open-proof';
const SHORT = m => String(m || '').split('/').pop();
const num = (v, d = 2) => (Number(v) || 0).toLocaleString(undefined, { maximumFractionDigits: d });
const usd = v => (Number(v) ? `$${num(v, 5)}` : '$0');
const clock = at => (at ? new Date(Number(at) * 1000).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—');
const PARTS = [['true', 'Record'], ['snaps', 'Snapshots'], ['steps', 'Step log'], ['kits', 'Kits'], ['judges', 'Judges'], ['deal', 'Bid / trade']];
const DEAL_WORD = { bid: 'THE BID', trade: 'THE TRADE', perp: 'THE PERP CALLS', post: 'THE POSTS' };

export function partsOf(r) {
  const s = r?.snapshots || {};
  return { true: !!(r?.true?.ran?.length || r?.true?.checks?.length), snaps: !!(s.pages?.length || s.stash?.length), steps: !!r?.steps?.length, kits: !!(r?.kits?.length || r?.kitsDid?.length), judges: !!r?.judges, deal: !!(r?.deal?.rows?.length || r?.deal?.say) };
}

export function openProofWindow(w) {
  if (w?.win && w?.id) window.dispatchEvent(new CustomEvent(OPEN_PROOF, { detail: { id: w.agent, win: w.win, proof: w.id } }));
}

function Sec({ k, title, children, count }) {
  return <section className="pfr-sec" id={`pfr-${k}`} data-testid={`pfr-${k}`}><h4>{title}{count != null ? <b className="m-num">{count}</b> : null}</h4>{children}</section>;
}

function TrueRec({ t }) {
  const checks = t.checks || []; const ran = (t.ran || []).filter(r => r.ok); const sites = t.read?.sites || []; const ft = t.foot || {};
  return <Sec k="true" title="THE TRUE RECORD" count={checks.length ? `${checks.filter(c => c.ok).length}/${checks.length}` : null}>
    {checks.length ? <ol className="pfr-checks">{checks.map((c, i) => <li key={c.key} className={c.ok ? 'is-ok' : 'is-bad'} style={{ '--i': i }} data-tip={c.why || c.label} data-testid={`pfr-check-${c.key}`}><small>{String(c.key).toUpperCase()}</small><i aria-hidden="true"><u /></i><em className="m-num">{c.ok ? 'PASS' : 'FAIL'}</em><span>{c.why}</span></li>)}</ol> : null}
    <ul className="pfr-minds" data-testid="pfr-minds">{ran.length ? ran.map((r, i) => <li key={r.asked} style={{ '--i': i }} data-tip={`${r.asked} answered as ${(r.answered || []).join(', ') || '?'} via ${(r.routes || []).join('/') || '?'}${r.standIn ? ' (a stand-in answered)' : ''}`}><b>{SHORT(r.asked)}</b><span>{(r.answered || []).map(SHORT).join(', ') || '?'}</span><small className="m-num">{r.calls} call{r.calls === 1 ? '' : 's'} · {num(r.secs, 1)} s · {usd(r.usd)}</small></li>) : <li className="is-none">{t.mindsCheck?.why || 'No mind answered.'}</li>}</ul>
    <div className="pfr-facts">
      <span data-tip={sites.join(', ') || 'No site was read'}><small>SOURCES READ</small><b className="m-num">{sites.length}</b><em>{sites.slice(0, 4).join(' · ')}{sites.length > 4 ? ' …' : ''}</em></span>
      <span data-tip={ft.shared?.length ? `Shared with #${ft.nearest}: ${ft.shared.join(', ')}` : 'Nothing shared with a past proof of its kind'}><small>FOOTPRINT NEW</small><b className={`m-num ${ft.repeat ? 'dn' : 'up'}`}>{ft.pct ?? '—'}%</b><i className="pfr-bar" aria-hidden="true"><u style={{ transform: `scaleX(${Math.min(1, (Number(ft.pct) || 0) / 100)})` }} /></i></span>
      {t.test ? <span data-tip={`Run by ${t.test.by || 'Claude'} on ${t.test.agent || "Sicario's"}: $0, nothing bought, bid or posted`}><small>TEST</small><b>{(t.test.pair || []).map(SHORT).join(' + ') || 'free minds'}</b><em>bench {t.test.bench || '—'}</em></span> : null}
    </div>
  </Sec>;
}

function Shot({ u, site }) {   // a picture that will not open (a PoB's needs its owner's sign-in) says so instead of a broken image
  const [bad, setBad] = useState(!u);
  if (bad) return <i className="pfr-noshot" data-tip="This picture opens only with its owner's sign-in">{u ? 'OWNER ONLY' : 'NO PICTURE'}</i>;
  return <a href={u} target="_blank" rel="noopener noreferrer"><img src={u} alt={`${site || 'Page'} as it read it`} loading="lazy" onError={() => setBad(true)} /></a>;
}

function Snaps({ s, fid, agent }) {
  const pages = s.pages || []; const stash = s.stash || []; const tally = s.stashTally || {};
  const src = file => (agent && fid && file ? apiUrl(`/api/cats/${agent}/powshot/${String(fid).replace(/[^a-z0-9]/gi, '').toLowerCase()}/${file}?${agentAuthQuery()}`) : null);
  return <Sec k="snaps" title="SNAPSHOTS" count={pages.length + stash.length}>
    {pages.length ? <ul className="pfr-shots">{pages.map((p, i) => { const u = src(p.file); return <li key={`${p.file}${i}`} style={{ '--i': Math.min(i, 12) }} data-tip={p.title || p.url || p.site}><Shot u={u} site={p.site} /><b>{p.site || 'page'}</b><small className="m-num">{clock(p.at)}{p.mind != null ? ` · mind ${p.mind + 1}` : ''}{p.found != null ? ` · ${p.found} found` : ''}</small></li>; })}</ul> : null}
    {stash.length ? <ul className="pfr-stash" data-testid="pfr-stash">{stash.map((r, i) => <li key={`${r.site}${i}`} style={{ '--i': Math.min(i, 12) }}><b>{r.site}</b><small className="m-num">{clock(r.at)}{r.category ? ` · ${[].concat(r.category).join(', ')}` : ''}</small>
      {[['scrape', 'SCRAPE', x => (x.chars ? `${num(x.chars, 0)} chars` : '') + (x.nums ? ` · ${x.nums} #` : '')], ['static', 'STATIC', x => (x.bytes ? `${num(x.bytes / 1024, 0)} KB` : '')], ['shot', 'SHOT', () => '']].map(([k, l, say]) => <em key={k} className={`m-chip ${r[k]?.kept ? 'is-on' : 'is-off'}`} data-tip={r[k]?.kept ? `${l.toLowerCase()} kept, sealed in the stash` : `no ${l.toLowerCase()} kept`}>{l} {r[k]?.kept ? say(r[k]) || '✓' : '—'}</em>)}
      <em className={`m-chip ${r.hit ? 'is-hit' : ''}`} data-tip={r.hit ? 'Read from the stash: no browsing, $0' : 'Browsed fresh'}>{r.hit ? 'STASH HIT' : 'BROWSED'}</em></li>)}</ul> : null}
    {Object.keys(tally).length ? <p className="pfr-note m-num" data-testid="pfr-stash-tally">{tally.hits ?? 0} stash hits · {tally.browsed ?? 0} browsed{tally.savedSecs ? ` · ${num(tally.savedSecs, 0)} s saved` : ''}{tally.savedUsd ? ` · ${usd(tally.savedUsd)} saved` : ''}</p> : null}
    {s.private ? <p className="pfr-note">PoB snapshots are yours alone: their pictures open only with your sign-in, and page links stay off the file.</p> : null}
  </Sec>;
}

function Steps({ steps, tot }) {
  const top = Math.max(1, ...steps.map(s => Number(s.secs) || 0));
  return <Sec k="steps" title="STEP LOG" count={tot?.calls ?? steps.length}>
    <ol className="pfr-steps">{steps.map((s, i) => <li key={`${s.at}${i}`} className={s.ok ? '' : 'is-bad'} style={{ '--i': Math.min(i, 14) }} data-tip={`${s.asked || '?'} → ${s.model || 'no answer'} via ${s.route || '?'}${s.tokens ? `, ${s.tokens} tokens` : ''}${s.err ? `: ${s.err}` : ''}`}>
      <small className="m-num">{clock(s.at)}</small><b>{SHORT(s.asked)}{s.mind != null ? <sup>{s.mind + 1}</sup> : null}</b><span>{s.ok ? SHORT(s.model) || '?' : 'no answer'}</span><i className="pfr-bar" aria-hidden="true"><u style={{ transform: `scaleX(${(Number(s.secs) || 0) / top})` }} /></i><em className="m-num">{num(s.secs, 1)} s</em><em className="m-num">{usd(s.usd)}</em></li>)}</ol>
    {tot ? <p className="pfr-note m-num">{tot.calls} calls · {num(tot.secs, 1)} s · {usd(tot.usd)} in all</p> : null}
  </Sec>;
}

function Judges({ j }) {
  const calls = j.calls || []; const h = j.hidden;
  return <Sec k="judges" title="JUDGE REVIEWS" count={j.score != null ? j.score : null}>
    <div className="pfr-facts">
      <span><small>VERDICT</small><b className={j.verdict === 'pass' || j.agree ? 'up' : ''}>{j.verdict || (j.score != null ? `score ${j.score}` : 'no verdict')}</b><em>{j.why || ''}</em></span>
      {j.recused?.length ? <span data-tip="A judge that built the proof may not judge it"><small>RECUSED</small><b>{j.recused.join(', ')}</b></span> : null}
      {j.missing?.length ? <span data-tip="Judges that were asked and gave no review"><small>NO ANSWER</small><b className="dn">{j.missing.join(', ')}</b></span> : null}
      {h ? <span data-tip="The hidden check the builders never see"><small>HIDDEN CHECK</small><b className="m-num">{h.passed}/{h.total}</b><i className="pfr-bar" aria-hidden="true"><u style={{ transform: `scaleX(${(Number(h.pct) || 0) / 100})` }} /></i></span> : null}
    </div>
    {j.judges?.length ? <ul className="pfr-minds">{j.judges.map(x => <li key={x.judge}><b>{x.judge}</b><span>{x.verdict || ''} {x.why || ''}</span><small className="m-num">{x.score ?? ''}</small></li>)}</ul> : null}
    {calls.length ? <p className="pfr-note m-num" data-tip={calls.map(c => `${SHORT(c.asked)} ${c.ok ? 'answered' : 'no answer'} ${clock(c.at)}`).join(' · ')}>{calls.length} judge call{calls.length === 1 ? '' : 's'} · {calls.filter(c => c.ok).length} answered · {usd(calls.reduce((a, c) => a + (Number(c.usd) || 0), 0))}</p> : null}
  </Sec>;
}

const DEAL_COLS = [['ticker', 'TICKER'], ['title', 'MARKET'], ['market', 'MARKET'], ['sym', 'COIN'], ['side', 'SIDE'], ['count', 'COUNT'], ['price', 'PRICE'], ['sol', 'IN SOL'], ['usd', 'USD'], ['entry', 'ENTRY'], ['exit', 'EXIT'], ['pnlPct', 'P&L %'], ['pnlSol', 'P&L SOL'], ['roePct', 'ROE %'], ['status', 'STATUS'], ['outcome', 'OUTCOME'], ['where', 'WHERE'], ['views', 'VIEWS']];
function Deal({ d }) {
  return <Sec k="deal" title={DEAL_WORD[d.type] || 'THE DEAL'}>
    {d.rows?.length ? d.rows.map((r, i) => <div key={i} className="pfr-deal" style={{ '--i': i }}>
      <div className="gst-tiles">{DEAL_COLS.filter(([k]) => r[k] != null && r[k] !== '').map(([k, l]) => <div key={k}><small>{l}</small><b className={`m-num ${/pnl|roe/i.test(k) ? (Number(r[k]) > 0 ? 'up' : Number(r[k]) < 0 ? 'dn' : '') : ''}`}>{typeof r[k] === 'number' ? num(r[k], 6) : String(r[k])}</b></div>)}</div>
      {r.legs?.length ? <ul className="pfr-legs">{r.legs.map((x, k) => <li key={k}><b>{x.title || x.ticker}</b><small className="m-num">{x.side} {x.price != null ? `@ ${x.price}` : ''}</small></li>)}</ul> : null}
      {r.receipt ? <p className="pfr-receipt" data-testid="pfr-receipt">{Object.entries(r.receipt).map(([k, v]) => <em key={k} className={`m-chip ${v ? 'is-on' : 'is-off'}`} data-tip={{ confirmed: 'Read back from the venue after it was sent', orderKept: 'The order id is kept on the server, never in the file', buyKept: 'The buy signature is kept on the server, never in the file', sellKept: 'The sell signature is kept on the server, never in the file', settled: 'The chain confirmed the settlement' }[k] || k}>{v ? '✓' : '—'} {{ confirmed: 'CONFIRMED', orderKept: 'ORDER ID', buyKept: 'BUY SIG', sellKept: 'SELL SIG', settled: 'SETTLED' }[k] || k}</em>)}</p> : null}
      {r.why ? <p className="pfr-note">{String(r.why).slice(0, 300)}</p> : null}
    </div>) : null}
    {d.say ? <p className="pfr-note" data-testid="pfr-deal-say">{d.say}</p> : null}
    {d.feesApart ? <p className="pfr-note">P&L never includes fees: they live on the receipt.</p> : null}
  </Sec>;
}

export function ProofFile({ rec }) {
  const has = useMemo(() => partsOf(rec), [rec]);
  if (!rec) return <section className="pfr is-old" data-testid="pfr"><p className="pfr-miss-h">This file was written before proof files carried their full record. It shows only what the proof kept.</p></section>;
  const n = PARTS.filter(([k]) => has[k]).length; const w = rec.window || {};
  return <section className="pfr m-card" data-testid="pfr" aria-label="The full record of this proof">
    <header className="pfr-h">
      <span className="pfr-ring" style={{ '--p': n / PARTS.length }} data-tip={`${n} of ${PARTS.length} parts were recorded`}><b className="m-num">{n}/{PARTS.length}</b></span>
      <span className="pfr-ht"><small>THE FULL RECORD{rec.test ? ' · TEST' : ''}</small><b>{rec.kind} {rec.n ? `#${rec.n}` : ''}</b></span>
      {w.win && w.id ? <button type="button" className="m-btn m-go pfr-open" onClick={() => openProofWindow(w)} data-tip="Opens this proof in its own window on the desk" data-testid="pfr-open"><ExternalLink size={14} aria-hidden="true" /> {w.say || 'Open its proof window'}</button> : null}
    </header>
    <nav className="m-seg pfr-jump" aria-label="Parts of this record">{PARTS.map(([k, l]) => <a key={k} href={`#pfr-${k === 'snaps' ? 'snaps' : k}`} className={has[k] ? 'is-on' : 'is-off'} onClick={e => { e.preventDefault(); e.currentTarget.closest('.pfr')?.querySelector(`#pfr-${k}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }} data-tip={has[k] ? `Jump to ${l.toLowerCase()}` : `${l}: never recorded`} data-testid={`pfr-part-${k}`}>{has[k] ? '●' : '○'} {l}</a>)}</nav>
    {has.true ? <TrueRec t={rec.true} /> : null}
    {has.snaps ? <Snaps s={rec.snapshots} fid={rec.id} agent={w.agent} /> : null}
    {has.steps ? <Steps steps={rec.steps} tot={rec.stepTotals} /> : null}
    {has.kits ? <Sec k="kits" title="KITS USED" count={(rec.kits || []).length || (rec.kitsDid || []).length}><ul className="pfr-kits">{(rec.kitsDid?.length ? rec.kitsDid : rec.kits.map(name => ({ name }))).map(k => <li key={k.name} className="m-chip is-on" data-tip={k.did || `${k.name} was in its toolkit`}>{k.name}{k.did ? <small>{k.did}</small> : null}</li>)}</ul></Sec> : null}
    {has.judges ? <Judges j={rec.judges} /> : null}
    {has.deal ? <Deal d={rec.deal} /> : null}
    {rec.missing?.length ? <section className="pfr-sec pfr-miss" data-testid="pfr-missing"><h4>NEVER RECORDED<b className="m-num">{rec.missing.length}</b></h4><ul>{rec.missing.map(m => <li key={m}>{m}</li>)}</ul></section> : null}
    <p className="pfr-note">Keys, tokens, sign-ins, order ids and signatures never go in a proof file.</p>
  </section>;
}
