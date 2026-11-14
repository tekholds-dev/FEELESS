import { useEffect, useMemo, useRef, useState } from 'react';
import { drawFrame, pickLook, sceneName, seeded, readyScenes, LOOKS_PER_PROOF } from '../../lib/proofFx';
import { fetchFeelessCandles } from '../../lib/candles';
import { isCalm, useOnScreen } from '../../lib/fxPause';
import '../../styles/proofLive.css';

// 🎆 The chat while a proof runs (owner 2026-11-11): the messages fade into a live stage of that proof — a canvas look picked from 100
// per proof (lib/proofFx) that reacts to its real vitals — with the vitals on top. "Show chat" brings the messages back any time.
const LABEL = { pow: 'PROOF OF WORK', pop: 'PROOF OF PERPS', pob: 'PROOF OF BIDS', poc: 'PROOF OF CONTENT', poe: 'PROOF OF ECO', pos: 'PROOF OF STATIC', work: 'WORKING' };
const PH_ORDER = ['propose', 'split', 'scout', 'choose', 'buy', 'watch', 'research', 'sell'];
const money = v => `$${Number(v || 0) < 1 ? Number(v || 0).toFixed(4) : Number(v || 0).toFixed(2)}`;
const clock = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

// which proof is running, from the desk state. null = nothing is running.
export function proofOf(d, live) {
  if (!d) return null;
  const k = String(d.task?.proofKind || '').toLowerCase();
  if (d.powFolder) return 'pow';
  if (d.popFolder) return 'pop';
  if (d.pobRun || d.pobRead) return 'pob';
  if (['pow', 'pop', 'pob', 'poc', 'poe', 'pos'].includes(k)) return k;
  const label = String(d.deskProof?.label || d.deskProof?.kind || '').toLowerCase();
  const fromDesk = label.includes('static') ? 'pos' : label.includes('content') || label === 'poc' ? 'poc' : label.includes('eco') ? 'poe' : null;
  return live ? fromDesk : null;   // a plain ask keeps the chat: only a proof turns into the stage
}

// what the run is on, in a few words
function subject(kind, d) {
  const f = d?.powFolder; const pop = d?.popFolder; const pob = d?.pobRun || d?.pobRead;
  if (f) return f.sym ? `$${f.sym}` : `${(f.coins || []).length || 'new'} coins`;
  if (pop) return `${pop.market || 'the market'} ${pop.side || ''}`.trim();
  if (pob) return pob.topic || pob.q || 'tonight\'s games';
  return d?.deskProof?.name || String(d?.task?.text || 'its task').slice(0, 60);
}

// a number that counts toward its new value instead of jumping
function useTween(value, ms = 600) {
  const [shown, setShown] = useState(value); const from = useRef(value);
  useEffect(() => { const a = from.current; const b = Number(value) || 0; if (a === b) return undefined; const t0 = performance.now(); let raf;
    const step = now => { const k = Math.min(1, (now - t0) / ms); const v = a + (b - a) * (1 - (1 - k) ** 3); setShown(v); if (k < 1) raf = requestAnimationFrame(step); else from.current = b; };
    raf = requestAnimationFrame(step); return () => cancelAnimationFrame(raf); }, [value, ms]);
  return shown;
}

// 📡 the stage's data — the run's own numbers and words only. Missing data = that scene is not shown.
const num = v => (Number.isFinite(Number(v)) ? Number(v) : null);
function useRunData(kind, d, wins, spent, steps) {
  const f = d?.powFolder; const pop = d?.popFolder; const pob = d?.pobRun || d?.pobRead;
  const [candles, setCandles] = useState([]);
  useEffect(() => {   // the coin's REAL 1-minute candles from FEELESS's candle service (the same source as every chart), every 15 s
    if (!f?.pair) { setCandles([]); return undefined; } let on = true;
    const load = () => fetchFeelessCandles('solana', f.pair, '1m', null, f.mint).then(r => { if (on) setCandles((r?.candles || []).slice(-60).map(k => (Array.isArray(k) ? { o: +k[1], h: +k[2], l: +k[3], c: +k[4] } : { o: +k.open, h: +k.high, l: +k.low, c: +k.close })).filter(k => k.h > 0)); }).catch(() => {});
    load(); const i = setInterval(() => { if (!document.hidden) load(); }, 15000); return () => { on = false; clearInterval(i); };
  }, [f?.pair, f?.mint]);
  const series = useRef([]); const roe = useRef([]);
  const lastS = series.current[series.current.length - 1];
  if (!lastS || lastS.spent !== spent || lastS.steps !== steps) series.current = [...series.current, { spent: Number(spent) || 0, steps, at: Date.now() }].slice(-60);
  const r = num(pop?.roePct); if (r != null && roe.current[roe.current.length - 1] !== r) roe.current = [...roe.current, r].slice(-80);
  const brains = wins.map(w => String(w?.model || '').split('/').pop());
  const mindOf = by => { const b = String(by || ''); if (/^B\b/.test(b)) return 1; if (/^A\b/.test(b)) return 0; const i = brains.findIndex(x => x && b.includes(x.slice(0, 10))); return i < 0 ? 0 : i; };
  const talk = (f?.talk || pob?.talk || []).length ? (f?.talk || pob?.talk).map(t => ({ mind: mindOf(t.by), text: t.text }))
    : (d?.chat || []).filter(m => m.by !== 'you').slice(-7).map(m => ({ mind: 0, text: m.text }));
  const stepRows = wins.flatMap((w, i) => (Array.isArray(w?.steps) ? w.steps : []).filter(x => x && typeof x === 'object').map(x => ({ mind: i, at: x.at || 0, text: `${x.action || 'step'}${x.detail ? ` · ${x.detail}` : x.thought ? ` · ${x.thought}` : ''}` })))
    .sort((a, b) => a.at - b.at);
  const entry = num(f?.entry); const now = num(f?.now); const okEntry = entry && now ? entry > now / 50 && entry < now * 50 : !!entry;
  const e0 = okEntry ? entry : null;
  return {
    candles, line: (f?.line || []).map(num).filter(v => v > 0), entry: e0,
    tp: e0 && num(f?.tp) ? e0 * (1 + num(f.tp) / 100) : null, sl: e0 && num(f?.sl) ? e0 * (1 - Math.abs(num(f.sl)) / 100) : null,
    coins: (f?.coins || []).map(c => ({ sym: c.sym || '?', picked: !!(c.pick || (f?.mint && c.mint === f.mint)), chg: num(c.chg ?? c.priceChange ?? c.change) })),
    talk, steps: stepRows, series: series.current, roe: roe.current,
    pages: wins.map((w, i) => ({ mind: i, host: w?.host || w?.url || '' })).filter(x => x.host),
    pos: pop ? { market: pop.market, side: pop.side, lev: num(pop.lev ?? pop.leverage) } : null,
    game: pob && (pob.home || pob.homeScore != null) ? { home: pob.home, away: pob.away, hs: pob.homeScore, as: pob.awayScore, clock: pob.clock, pick: pob.pick } : null,
  };
}

export default function ProofLive({ d, wins = [], spent = 0, name = '', kind, onShowChat }) {
  const box = useRef(null); const cv = useRef(null); const on = useOnScreen(box);
  const seed = d?.task?.id || d?.powFolder?.id || d?.popFolder?.id || d?.deskProof?.id || kind;
  const look = useMemo(() => pickLook(kind, seed), [kind, seed]);
  const rnd = useMemo(() => { const r = seeded(seed); return Array.from({ length: 120 }, () => r()); }, [seed]);
  const steps = wins.reduce((n, w) => n + (Array.isArray(w?.steps) ? w.steps.length : Number(w?.steps) || 0), 0);
  const energy = useRef(0); const last = useRef({ steps, spent });
  useEffect(() => { if (steps > last.current.steps || spent > last.current.spent) energy.current = 1; last.current = { steps, spent }; }, [steps, spent]);
  const [t0] = useState(() => Date.now()); const [now, setNow] = useState(Date.now());
  useEffect(() => { const i = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(i); }, []);
  const data = useRunData(kind, d, wins, spent, steps); const dataRef = useRef(data); dataRef.current = data;
  const [scene, setScene] = useState(() => sceneName(kind, look, 0, data));

  useEffect(() => {   // the frame loop: stops off-screen, in a hidden tab and under fx-lite / reduced motion (one still frame then)
    const c = cv.current; if (!c) return undefined; const ctx = c.getContext?.('2d'); if (!ctx) return undefined;
    let raf = 0; let alive = true; const start = performance.now() - ((Date.now() - t0) || 0);
    const size = () => { const r = c.getBoundingClientRect(); const dpr = Math.min(2, window.devicePixelRatio || 1); c.width = Math.max(1, r.width * dpr); c.height = Math.max(1, r.height * dpr); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); return r; };
    // the open band (canvas px) between the step row and the vitals — the data scene draws only there, never under a panel
    const band = () => { const b = box.current; const top = b?.querySelector('.pl-steps') || b?.querySelector('.pl-top'); const vit = b?.querySelector('.pl-vitals');
      if (!top || !vit) return null; const c0 = c.getBoundingClientRect().top; return [top.getBoundingClientRect().bottom - c0 + 6, vit.getBoundingClientRect().top - c0 - 6]; };
    let r = size(); const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(() => { r = size(); }) : null; ro?.observe(c);
    let shownScene = '';
    const frame = now_ => { if (!alive) return; const t = (now_ - start) / 1000;
      energy.current = Math.max(0, energy.current - 0.012);
      const out = drawFrame(ctx, { w: r.width, h: r.height, t, kind, look, energy: energy.current, rnd, data: dataRef.current, band: band() });
      if (out.scene !== shownScene) { shownScene = out.scene; setScene(out.scene); }
      if (!isCalm() && on && !document.hidden) raf = requestAnimationFrame(frame); };
    frame(performance.now());
    const vis = () => { if (!document.hidden && on && !isCalm()) { cancelAnimationFrame(raf); raf = requestAnimationFrame(frame); } };
    document.addEventListener('visibilitychange', vis);
    return () => { alive = false; cancelAnimationFrame(raf); ro?.disconnect(); document.removeEventListener('visibilitychange', vis); };
  }, [kind, look, rnd, on, t0]);

  const nReady = readyScenes(kind, data).length;
  const f = d?.powFolder; const at = f ? PH_ORDER.indexOf(f.phase) : -1;
  const spentT = useTween(spent); const stepsT = useTween(steps, 400);
  const minds = wins.slice(0, 2);
  const lastSaid = [...(d?.chat || [])].reverse().find(m => m.by !== 'you')?.text || '';
  return <div ref={box} className={`pl pl-${kind}`} data-testid="proof-live" data-look={`${look.bg}-${look.scene}-${look.fg}-${look.pal}`} data-scene={scene}>
    <canvas ref={cv} className="pl-cv" aria-hidden="true" />
    <div className="pl-top">
      <span className="pl-chip"><i aria-hidden="true" />{LABEL[kind] || LABEL.work}</span>
      <b className="pl-on" title={subject(kind, d)}>{subject(kind, d)}</b>
      <button type="button" className="pl-chat" onClick={onShowChat} data-tip="Show the chat — the live stage comes back when you hide it" data-testid="proof-live-chat">Show chat</button>
    </div>
    {at >= 0 ? <ol className="pl-steps" aria-label={`Step ${at + 1} of ${PH_ORDER.length}: ${f.phase}`}>{PH_ORDER.map((x, n) => <li key={x} className={n < at ? 'is-done' : n === at ? 'is-at' : ''}><span>{x}</span></li>)}</ol> : null}
    <div className="pl-vitals" role="group" aria-label="Live vitals">
      <span data-tip="How long this run has been going"><em>TIME</em><b className="m-num">{clock((now - t0) / 1000)}</b></span>
      <span data-tip="Steps both minds have taken"><em>STEPS</em><b className="m-num">{Math.round(stepsT)}</b></span>
      <span data-tip="What this run has cost so far, from each call's own bill"><em>SPENT</em><b className="m-num is-hot">{money(spentT)}</b></span>
      <span data-tip={`Live view of real run data · ${nReady} view${nReady === 1 ? '' : 's'} this run can fill right now · one of ${LOOKS_PER_PROOF} looks`}><em>VIEW</em><b className="m-num">{scene || 'waiting for data'}</b></span>
    </div>
    <div className="pl-minds">{minds.map((w, i) => <div key={i} className={`pl-mind${w?.status === 'working' ? ' is-on' : ''}`} style={{ '--i': i }}>
      <b>{'AB'[i]} · {String(w?.model || '').split('/').pop().replace(':free', '') || 'mind'}</b>
      <small>{w?.bubble || (w?.status === 'working' ? 'working…' : 'waiting its turn')}</small></div>)}</div>
    {lastSaid ? <p className="pl-said" aria-live="polite"><b>{name || 'It'}:</b> {String(lastSaid).slice(0, 160)}</p> : null}
  </div>;
}
