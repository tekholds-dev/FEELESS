import React, { useEffect, useMemo, useRef, useState } from 'react';
import { apiUrl } from '../../lib/api';
import '../../styles/pocStudio.css';

// 🎬 Slice 5 (owner 2026-11-18): a filed PoC is a content STUDIO graded on real reach. It shows the trend it rode, the real files it made
// (image, short video, post, thread) in phone story, feed and wide, and the goal set at filing. Nothing posts until YOU approve here: pick the
// posting service your accounts are signed into (Upload-Post, Zernio or Ayrshare), the platforms and what each gets, then Approve and post.
// Views and engagement are read back at 24 h and 7 d and graded against the goal, with the cost per 1,000 views.
export const FORMATS = [['story', 'Story', '9:16 phone story / Reels / TikTok / Shorts'], ['feed', 'Feed', '4:5 feed post'], ['wide', 'Wide', '16:9 X card, LinkedIn, YouTube']];
export const PLATS = [['x', 'X'], ['tiktok', 'TikTok'], ['youtube', 'YouTube'], ['instagram', 'Instagram'], ['bluesky', 'Bluesky'], ['threads', 'Threads'], ['linkedin', 'LinkedIn'], ['facebook', 'Facebook']];
const PIECES = { x: ['image', 'video', 'thread'], tiktok: ['video'], youtube: ['video'], instagram: ['video', 'image'], bluesky: ['image', 'video', 'thread'], threads: ['image', 'video', 'thread'], linkedin: ['image', 'video'], facebook: ['image', 'video'] };
export const GOALS = [['reach', 'Reach', 'views'], ['buzz', 'Buzz', 'likes, replies and shares'], ['followers', 'Followers', 'new followers'], ['clicks', 'Clicks', 'link clicks']];
const GOAL_WORD = Object.fromEntries(GOALS.map(([k, , w]) => [k, w]));
const VERDICT = { hit: 'is-up', missed: 'is-dn', 'on pace': 'is-up', behind: 'is-dn', 'not given': '' };

export const fmt = n => (n == null ? '—' : n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e4 ? `${Math.round(n / 1e3)}K` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : String(n));

/** Pure: the file of one piece in one format, or null. */
export function fileOf(files, piece, format) { return (files || []).find(f => f.piece === piece && f.format === format && f.url && !f.error) || null; }

/** Pure: the approve body from the owner's picks — only platforms switched on, each with the piece it gets. */
export function approveBody(svc, picks, realPost) {
  const platforms = Object.fromEntries(Object.entries(picks).filter(([, v]) => v.on).map(([k, v]) => [k, v.piece]));
  return { svc, platforms, ...(realPost ? { realPost: true } : {}) };
}

/** Pure: default picks — the video to the vertical-video apps, the picture to X / Bluesky / Threads / LinkedIn, all off until he switches one on. */
export function defaultPicks() { return Object.fromEntries(PLATS.map(([k]) => [k, { on: false, piece: PIECES[k][0] }])); }

function Meter({ value, target, label, verdict }) {
  const pct = value != null && target ? Math.min(1, value / target) : 0;
  return <div className="pst-meter" data-tip={`${label}: ${value == null ? 'not given' : fmt(value)} of ${fmt(target)}`}>
    <div className="pst-meter-bar"><i style={{ transform: `scaleX(${pct})` }} /></div>
    <span><b className={`m-num ${VERDICT[verdict] || ''}`}>{value == null ? '—' : fmt(value)}</b><small>of {fmt(target)} · {label}</small></span>
  </div>;
}

export default function PocStudio({ cat, f, work, onFolders }) {
  const s = f?.studio; const [fmtKey, setFmt] = useState('story'); const [msg, setMsg] = useState(''); const [busy, setBusy] = useState('');
  const [svcs, setSvcs] = useState(null); const [svc, setSvc] = useState('uploadpost'); const [accts, setAccts] = useState(null);
  const [picks, setPicks] = useState(defaultPicks); const [real, setReal] = useState(false); const [confirm, setConfirm] = useState(false);
  const [goalT, setGoalT] = useState(s?.goal?.type || 'reach'); const [goalN, setGoalN] = useState(String(s?.goal?.target || ''));
  useEffect(() => { setGoalT(s?.goal?.type || 'reach'); setGoalN(String(s?.goal?.target || '')); }, [s?.goal?.type, s?.goal?.target]);
  const workRef = useRef(work); workRef.current = work; const isPosted = !!f?.posted;   // a fresh `work` each parent render must not refetch the service list
  useEffect(() => { let live = true; if (!isPosted) Promise.resolve().then(() => workRef.current(cat.id, { op: 'poc_accounts' })).then(j => live && setSvcs(j.services || [])).catch(() => {}); return () => { live = false; }; }, [cat.id, isPosted]);
  const posted = f?.posted; const goal = s?.goal || {}; const last = f?.reach?.last; const reads = f?.reach?.reads || [];
  const on = useMemo(() => Object.entries(picks).filter(([, v]) => v.on), [picks]);
  if (!s) return null;
  const call = async (key, body, after) => { setMsg(''); setBusy(key); try { const j = await work(cat.id, body); if (j.pocFolders) onFolders?.(j.pocFolders); after?.(j); } catch (e) { setMsg(e.message); } setBusy(''); };
  const svcRow = (svcs || []).find(x => x.id === svc);
  const files = s.files || []; const img = fileOf(files, 'image', fmtKey); const vid = fileOf(files, 'video', fmtKey); const post = fileOf(files, 'post', fmtKey); const thr = fileOf(files, 'thread', fmtKey);
  const made = files.filter(x => x.url && !x.error).length;
  return <section className="pst m-live" aria-label={`PoC #${f.n} content studio`} data-testid={`pst-${f.id}`}>
    <header className="pst-head">
      {s.clip ? <div className="pst-trend" data-tip="Clip farm: cut from your own upload, the moment both minds scored">
        <span className="m-label">CLIPPED FROM YOUR UPLOAD</span>
        <b className="pst-from" data-testid="pst-clip-from">{s.clip.from}</b>
        <small><span className="m-chip">{Math.floor(s.clip.s / 60)}:{String(Math.floor(s.clip.s % 60)).padStart(2, '0')}–{Math.floor(s.clip.e / 60)}:{String(Math.floor(s.clip.e % 60)).padStart(2, '0')}</span> {Math.round(s.clip.dur)} s · {(s.clip.minds || []).map(m => `Mind ${'AB'[m.mind % 2]} ${m.score ?? '—'}/10`).join(' · ')} · {s.clip.track?.how === 'face' ? 'tracked on the face' : 'tracked on the motion'}{s.slot ? ` · planned ${s.slot}` : ''}</small>
      </div> : <div className="pst-trend" data-tip="Trend first: what was moving today when it decided, and how big it was">
        <span className="m-label">RODE TODAY’S TREND</span>
        <a href={s.trend?.url} target="_blank" rel="noreferrer noopener" data-testid="pst-trend">{s.trend?.text}</a>
        <small><span className="m-chip">{s.trend?.source}</span> {s.trend?.rank ? s.trend.unit : `${fmt(s.trend?.signal)} ${s.trend?.unit || ''}`}{s.trends?.length ? ` · picked from ${s.trends.length} trends` : ''}</small>
      </div>}
      <Meter value={posted ? (goal.type === 'reach' ? last?.views : goal.type === 'buzz' ? last?.engagement : goal.type === 'clicks' ? last?.clicks : null) ?? null : null} target={goal.target} label={GOAL_WORD[goal.type] || 'views'} verdict={(f.grade || last?.grade)?.verdict} />
      <dl className="pst-facts">
        <div data-tip="What the minds and the media cost. The free maker on this machine is $0"><dt>COST</dt><dd className="m-num">${(Number(f.cost || 0) + Number(s.maker?.usd || 0)).toFixed(2)}</dd></div>
        <div data-tip="Dollars per 1,000 views, from the last read"><dt>PER 1K VIEWS</dt><dd className="m-num" data-testid="pst-cpm">{last?.grade?.cpm == null ? '—' : `$${last.grade.cpm.toFixed(2)}`}</dd></div>
        <div data-tip="Every piece in every format"><dt>FILES</dt><dd className="m-num">{made}/{s.clip ? 9 : 12}</dd></div>
      </dl>
    </header>
    <p className="pst-angle"><b>{s.hook}</b> {s.angle ? <span>· {s.angle}</span> : null}{f.test ? <span className="m-chip pst-test">TEST</span> : null}</p>

    <div className="m-seg pst-formats" role="tablist" aria-label="Format">{FORMATS.map(([k, l, tip]) => <button key={k} type="button" role="tab" aria-selected={fmtKey === k} className={fmtKey === k ? 'active' : ''} onClick={() => setFmt(k)} data-tip={tip} data-testid={`pst-fmt-${k}`}>{l}</button>)}</div>
    <div className={`pst-files is-${fmtKey}${s.clip ? ' is-clip' : ''}`}>
      <figure style={{ '--i': 0 }}><span className="m-label">{s.clip ? 'COVER' : 'IMAGE'}</span>{img ? <a href={apiUrl(img.url)} target="_blank" rel="noreferrer noopener" data-tip="Open the full-size file"><img src={apiUrl(img.url)} alt={s.hook} loading="lazy" data-testid={`pst-img-${fmtKey}`} /></a> : <small>Not made</small>}</figure>
      <figure style={{ '--i': 1 }}><span className="m-label">{s.clip ? `CLIP · ${{ story: '9:16', feed: '1:1', wide: '16:9' }[fmtKey]}` : 'SHORT VIDEO'}</span>{vid ? <video src={apiUrl(vid.url)} controls muted playsInline preload="metadata" data-testid={`pst-vid-${fmtKey}`} /> : <small>Not made</small>}</figure>
      <figure style={{ '--i': 2 }} className="pst-text"><span className="m-label">POST</span>{post ? <><p data-testid={`pst-post-${fmtKey}`}>{post.text}</p><a className="m-btn" href={apiUrl(post.url)} download data-tip="The post as a text file">Download</a></> : <small>Not made</small>}</figure>
      {s.clip ? null : <figure style={{ '--i': 3 }} className="pst-text"><span className="m-label">THREAD · {thr?.parts || 0} PARTS</span>{thr ? <><div className="pst-cards">{(thr.cards || []).map((u, i) => <img key={u} src={apiUrl(u)} alt={`Part ${i + 1}`} loading="lazy" />)}</div><a className="m-btn" href={apiUrl(thr.url)} download data-tip="The thread as a text file">Download</a></> : <small>Not made</small>}</figure>}
    </div>

    {posted ? <section className="pst-posted" aria-label="Posted" data-testid="pst-posted">
      <span className="m-label">POSTED AFTER YOUR APPROVE · {(svcs || []).find(x => x.id === posted.svc)?.name || posted.svc}</span>
      <ul>{Object.entries(posted.platforms || {}).map(([k, r]) => <li key={k} className={r.ok ? '' : 'is-bad'}><b>{(PLATS.find(p => p[0] === k) || [k, k])[1]}</b> <small>{r.piece}</small> {r.url ? <a href={r.url} target="_blank" rel="noreferrer noopener">open</a> : null}{r.error ? <small> {r.error}</small> : null}</li>)}</ul>
      <div className="pst-reads">{[['h24', '24 h'], ['d7', '7 d']].map(([k, l]) => { const r = reads.find(x => x.key === k); return <div key={k} className="pst-read" data-testid={`pst-read-${k}`}><span className="m-label">{l}</span>{r ? <><b className="m-num">{fmt(r.views)}</b><small>views · {fmt(r.engagement)} engaged</small><span className={`m-chip ${VERDICT[r.grade?.verdict] || ''}`}>{r.grade?.verdict}</span></> : <small>reads {l} after it posted</small>}</div>; })}</div>
      <button type="button" className="m-btn" disabled={!!busy} onClick={() => call('read', { op: 'poc_reach', job: f.id })} data-tip="Reads views and engagement now from the posting service" data-testid="pst-read-now">{busy === 'read' ? 'Reading…' : 'Read reach now'}</button>
    </section> : <section className="pst-approve" aria-label="Approve and post" data-testid="pst-approve">
      <span className="m-label">NOTHING IS POSTED UNTIL YOU APPROVE</span>
      <div className="pst-goal" data-tip="The goal it is graded against at 7 days. Locked once it posts">
        <div className="m-seg" role="group" aria-label="Goal">{GOALS.map(([k, l]) => <button key={k} type="button" aria-pressed={goalT === k} className={goalT === k ? 'active' : ''} onClick={() => setGoalT(k)} data-testid={`pst-goal-${k}`}>{l}</button>)}</div>
        <input className="m-input" inputMode="numeric" value={goalN} onChange={e => setGoalN(e.target.value.replace(/\D/g, ''))} aria-label="Goal number" data-testid="pst-goal-n" />
        <small>{GOAL_WORD[goalT]} in 7 days · set by {goal.by === 'owner' ? 'you' : goal.by === 'minds' ? 'its minds' : 'code'}{goal.why ? `: ${goal.why}` : ''}</small>
        <button type="button" className="m-btn" disabled={!!busy || (goalT === goal.type && Number(goalN) === goal.target)} onClick={() => call('goal', { op: 'poc_goal', job: f.id, tools: { type: goalT, target: Number(goalN) } })} data-testid="pst-goal-save">{busy === 'goal' ? 'Saving…' : 'Save goal'}</button>
      </div>
      <div className="m-seg pst-svcs" role="group" aria-label="Posting service">{(svcs || []).map(x => <button key={x.id} type="button" aria-pressed={svc === x.id} className={svc === x.id ? 'active' : ''} onClick={() => { setSvc(x.id); setAccts(null); }} data-tip={`Your accounts signed into ${x.name}. ${x.saved ? 'Key saved on this agent' : 'No key saved yet'}`} data-testid={`pst-svc-${x.id}`}>{x.name}{x.saved ? ' ✓' : ''}</button>)}</div>
      {svcRow && !svcRow.saved ? <small className="pst-hint">Sign your X / TikTok / YouTube … accounts into <a href={svcRow.site} target="_blank" rel="noreferrer noopener">{svcRow.name}</a>, then save its key in Vault › API keys ({svcRow.how}).</small> : null}
      {svcRow?.saved ? <button type="button" className="m-btn" disabled={!!busy} onClick={() => call('accts', { op: 'poc_accounts', tools: { svc } }, j => setAccts(j.accounts || []))} data-testid="pst-accts">{busy === 'accts' ? 'Checking…' : 'My connected accounts'}</button> : null}
      {accts ? <div className="pst-accts">{accts.length ? accts.map(a => <span key={`${a.platform}${a.name}`} className="m-chip">{a.platform} · {a.name}</span>) : <small>No account connected there yet.</small>}</div> : null}
      <div className="pst-plats">{PLATS.filter(([k]) => !svcRow || svcRow.platforms.includes(k)).map(([k, l], i) => { const p = picks[k]; return <div key={k} className={`pst-plat${p.on ? ' is-on' : ''}`} style={{ '--i': i }}>
        <button type="button" className="m-btn" aria-pressed={p.on} onClick={() => { setConfirm(false); setPicks(x => ({ ...x, [k]: { ...x[k], on: !x[k].on } })); }} data-tip={`Post on ${l}`} data-testid={`pst-plat-${k}`}>{l}</button>
        {PIECES[k].length > 1 ? <select className="m-input" value={p.piece} onChange={e => setPicks(x => ({ ...x, [k]: { ...x[k], piece: e.target.value } }))} aria-label={`${l} gets`} data-testid={`pst-piece-${k}`}>{PIECES[k].filter(pc => pc !== 'thread' || svcRow?.thread !== false).map(pc => <option key={pc} value={pc}>{pc}</option>)}</select> : <small>{p.piece}</small>}
      </div>; })}</div>
      {f.test ? <label className="pst-real"><input type="checkbox" checked={real} onChange={e => setReal(e.target.checked)} data-testid="pst-real" /> This is a TEST PoC: post it for real anyway</label> : null}
      {!confirm ? <button type="button" className="m-btn m-go" disabled={!on.length || !svcRow?.saved || (f.test && !real)} onClick={() => setConfirm(true)} data-tip="Shows exactly what goes where before anything posts" data-testid="pst-approve-btn">Approve and post {on.length ? `on ${on.length}` : ''}</button>
        : <div className="pst-confirm" role="alertdialog" aria-label="Confirm the post" data-testid="pst-confirm">
          <p>Post through <b>{svcRow?.name}</b>: {on.map(([k, v]) => `${(PLATS.find(p => p[0] === k) || [])[1]} gets the ${v.piece}`).join(', ')}. This goes public on your accounts.</p>
          <button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => call('post', { op: 'poc_approve', job: f.id, tools: approveBody(svc, picks, real) }, () => setConfirm(false))} data-testid="pst-confirm-yes">{busy === 'post' ? 'Posting…' : 'Yes, post it'}</button>
          <button type="button" className="m-btn" onClick={() => setConfirm(false)}>Not yet</button>
        </div>}
    </section>}
    {msg ? <small className="pst-msg" role="alert">{msg}</small> : null}
  </section>;
}
