import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Bookmark, Heart, MessageCircle, Send, X, Download, Save, Plus, Trash2 } from 'lucide-react';
import '../../styles/pocWire.css';

// 🧩 THE POC CONTENT BOARD (owner 2026-11-13: "wireframe a week of content"; 2026-11-15 the Excalidraw canvas read as "wtf … try new styles and
// better components"). One picture, laid out as the real post on three drawn surfaces (phone story, feed post, street billboard), with its words on
// it, then planned Mon–Sun: drag the post onto a day (or tap +), each day keeps its own copy. Save files the post itself (no device chrome) back
// into the proof as a NEW version; the original stays. The board is kept in this browser per picture.
export const FORMATS = [['story', 'Story 9:16', 1080, 1920], ['feed', 'Feed 1:1', 1080, 1080], ['billboard', 'Billboard 16:9', 1920, 1080]];
export const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const SPOTS = [['top', 'Top'], ['bottom', 'Bottom']];
const FITS = [['cover', 'Fill'], ['contain', 'Fit']];
const FOCI = ['0% 0%', '50% 0%', '100% 0%', '0% 50%', '50% 50%', '100% 50%', '0% 100%', '50% 100%', '100% 100%'];
const KEY = id => `feeless:pocwire2:${id}`;

export const blankPost = (title = 'Picture') => ({ fmt: 'story', headline: String(title).slice(0, 48), caption: '', handle: 'feeless', cta: 'Tap in', fit: 'cover', spot: 'bottom', focus: '50% 50%', time: '18:00' });

// Pure (tested): where the picture lands inside a W×H post — cover crops to fill, contain fits whole; focus picks which part of a crop stays.
export function placePic(W, H, iw, ih, fit = 'cover', focus = '50% 50%') {
  const r = fit === 'contain' ? Math.min(W / iw, H / ih) : Math.max(W / iw, H / ih);
  const w = iw * r; const h = ih * r; const [fx, fy] = String(focus).split(' ').map(v => (parseFloat(v) || 0) / 100);
  return { x: (W - w) * (Number.isFinite(fx) ? fx : 0.5) + 0, y: (H - h) * (Number.isFinite(fy) ? fy : 0.5) + 0, w, h };
}

// Pure (tested): the board after placing a post on a day (a copy, so editing the stage later never rewrites the day).
export function planDay(week, day, post) { return { ...week, [day]: { ...post } }; }
export const planned = week => DAYS.filter(d => week[d]).length;

const wrap = (ctx, text, maxW) => {   // words to lines that fit maxW
  const out = []; let line = '';
  String(text || '').split(/\s+/).filter(Boolean).forEach(w => { const t = line ? `${line} ${w}` : w; if (ctx.measureText(t).width > maxW && line) { out.push(line); line = w; } else line = t; });
  if (line) out.push(line); return out;
};
const cssVar = (n, d) => { try { return getComputedStyle(document.documentElement).getPropertyValue(n).trim() || d; } catch { return d; } };

// The post itself as a PNG data URL, drawn at full size on a canvas (what gets saved / downloaded).
export async function renderPost(img, post) {
  const [, , W, H] = FORMATS.find(f => f[0] === post.fmt) || FORMATS[0];
  const c = document.createElement('canvas'); c.width = W; c.height = H; const ctx = c.getContext('2d');
  ctx.fillStyle = cssVar('--m-bg', 'black'); ctx.fillRect(0, 0, W, H);
  if (img) { const p = placePic(W, H, img.naturalWidth || 1, img.naturalHeight || 1, post.fit, post.focus); ctx.drawImage(img, p.x, p.y, p.w, p.h); }
  const top = post.spot === 'top'; const band = H * 0.42;
  const g = ctx.createLinearGradient(0, top ? 0 : H - band, 0, top ? band : H);
  g.addColorStop(top ? 0 : 1, 'rgba(0,0,0,.78)'); g.addColorStop(top ? 1 : 0, 'rgba(0,0,0,0)');
  ctx.fillStyle = g; ctx.fillRect(0, top ? 0 : H - band, W, band);
  const pad = Math.round(W * 0.06); const hs = Math.round(Math.min(W, H) * 0.085); const cs = Math.round(hs * 0.42);
  ctx.textBaseline = 'top'; ctx.fillStyle = 'white';
  ctx.font = `800 ${hs}px Unbounded, sans-serif`; const hl = wrap(ctx, String(post.headline || '').toUpperCase(), W - pad * 2).slice(0, 3);
  ctx.font = `500 ${cs}px Sora, sans-serif`; const cl = wrap(ctx, post.caption, W - pad * 2).slice(0, 3);
  const ctaH = post.cta ? Math.round(cs * 2.1) : 0;
  const block = hl.length * hs * 1.08 + (cl.length ? cs * 0.6 + cl.length * cs * 1.3 : 0) + (ctaH ? cs + ctaH : 0);
  let y = top ? pad : H - pad - block;
  ctx.font = `800 ${hs}px Unbounded, sans-serif`; hl.forEach(l => { ctx.fillText(l, pad, y); y += hs * 1.08; });
  if (cl.length) { y += cs * 0.6; ctx.font = `500 ${cs}px Sora, sans-serif`; ctx.fillStyle = 'rgba(255,255,255,.86)'; cl.forEach(l => { ctx.fillText(l, pad, y); y += cs * 1.3; }); }
  if (ctaH) {
    y += cs; ctx.font = `700 ${cs}px Sora, sans-serif`; const tw = ctx.measureText(post.cta).width + cs * 2.4;
    ctx.fillStyle = cssVar('--m-accent', 'white'); ctx.beginPath(); (ctx.roundRect ? ctx.roundRect(pad, y, tw, ctaH, ctaH / 2) : ctx.rect(pad, y, tw, ctaH)); ctx.fill();
    ctx.fillStyle = cssVar('--m-accent-ink', 'black'); ctx.fillText(post.cta, pad + cs * 1.2, y + (ctaH - cs) / 2);
  }
  ctx.font = `600 ${Math.round(cs * 0.8)}px "JetBrains Mono", monospace`; ctx.fillStyle = 'rgba(255,255,255,.7)';
  ctx.fillText(`@${post.handle || 'feeless'}`, pad, top ? H - pad - cs : pad);
  return c.toDataURL('image/png');
}

const loadImg = url => new Promise(ok => { if (!url) return ok(null); const i = new Image(); i.crossOrigin = 'anonymous'; i.onload = () => ok(i); i.onerror = () => ok(null); i.src = url; });

function Words({ post, size }) {   // the words on the post, as they will print
  return <div className={`pwr-words is-${post.spot} is-${size}`}>
    {post.headline ? <b>{post.headline}</b> : null}{post.caption ? <p>{post.caption}</p> : null}{post.cta ? <i>{post.cta}</i> : null}
  </div>;
}
function Pic({ src, post }) { return src ? <img src={src} alt="" draggable={false} style={{ objectFit: post.fit, objectPosition: post.focus }} /> : <span className="pwr-nopic">No picture</span>; }

// The three drawn surfaces. Pure presentation: phone story with bezel + progress, feed card with its action row, billboard on posts with lamps.
function Surface({ src, post, mini = false }) {
  if (post.fmt === 'feed') return <div className={`pwr-feed${mini ? ' is-mini' : ''}`}>
    {mini ? null : <header><span className="pwr-av" /><b>{post.handle || 'feeless'}</b><small>Sponsored</small></header>}
    <div className="pwr-shot"><Pic src={src} post={post} /><Words post={post} size={mini ? 's' : 'm'} /></div>
    {mini ? null : <footer><span><Heart size={18} /><MessageCircle size={18} /><Send size={18} /></span><Bookmark size={18} /><p><b>{post.handle || 'feeless'}</b> {post.caption || 'Your caption shows here.'}</p></footer>}
  </div>;
  if (post.fmt === 'billboard') return <div className={`pwr-bill${mini ? ' is-mini' : ''}`}>
    {mini ? null : <span className="pwr-lamps" aria-hidden="true"><i /><i /><i /></span>}
    <div className="pwr-shot"><Pic src={src} post={post} /><Words post={post} size={mini ? 's' : 'l'} /></div>
    {mini ? null : <span className="pwr-legs" aria-hidden="true"><i /><i /></span>}
  </div>;
  return <div className={`pwr-phone${mini ? ' is-mini' : ''}`}>
    <div className="pwr-shot"><Pic src={src} post={post} />
      {mini ? null : <><span className="pwr-bars" aria-hidden="true"><i className="is-done" /><i className="is-now" /><i /></span>
        <span className="pwr-who"><span className="pwr-av" /><b>{post.handle || 'feeless'}</b><small>2h</small></span></>}
      <Words post={post} size={mini ? 's' : 'm'} /></div>
    {mini ? null : <span className="pwr-notch" aria-hidden="true" />}
  </div>;
}

export default function PocWire({ src, kind = 'image', from = null, title = 'Picture', onSave, onClose }) {
  const [post, setPost] = useState(() => blankPost(title)); const [week, setWeek] = useState({}); const [day, setDay] = useState('');
  const [err, setErr] = useState(''); const [done, setDone] = useState(''); const [busy, setBusy] = useState(''); const [over, setOver] = useState('');
  const img = useRef(null); const pic = kind === 'image' ? src : null;
  useEffect(() => {   // this picture's kept board, else a fresh one
    try { const kept = JSON.parse(localStorage.getItem(KEY(from)) || 'null'); if (kept?.post) { setPost({ ...blankPost(title), ...kept.post }); setWeek(kept.week || {}); } } catch { /* blocked or empty: start fresh */ }
  }, [from, title]);
  useEffect(() => { try { localStorage.setItem(KEY(from), JSON.stringify({ post, week })); } catch { /* full or blocked: the board still works */ } }, [from, post, week]);
  useEffect(() => { let on = true; loadImg(pic).then(i => { if (on) { img.current = i; if (pic && !i) setErr('The picture could not be read here, so it cannot be drawn into the export.'); } }); return () => { on = false; }; }, [pic]);
  useEffect(() => { document.body.classList.add('has-pwr'); const k = e => { if (e.key === 'Escape') onClose?.(); }; window.addEventListener('keydown', k); return () => { document.body.classList.remove('has-pwr'); window.removeEventListener('keydown', k); }; }, [onClose]);
  const set = patch => { setPost(p => { const n = { ...p, ...patch }; if (day) setWeek(w => planDay(w, day, n)); return n; }); setDone(''); };
  const place = d => { setWeek(w => planDay(w, d, post)); setDay(d); setDone(''); };
  const open = d => { setDone(''); if (week[d]) { setPost({ ...week[d] }); setDay(d); } else place(d); };
  const drop = d => { const { [d]: _gone, ...rest } = week; setWeek(rest); if (day === d) setDay(''); };
  const fmt = FORMATS.find(f => f[0] === post.fmt) || FORMATS[0]; const n = planned(week);
  const name = `${fmt[1]}${day ? ` · ${day}` : ''} · ${title}`.slice(0, 60);
  const exportNow = async () => { if (!img.current && pic) throw new Error('The picture is still loading.'); return renderPost(img.current, post); };
  const save = async () => { setErr(''); setDone(''); setBusy('save'); try { await onSave?.(await exportNow(), 'wire', from); setDone(`Saved "${name}" into the proof as a new version. The original stays.`); } catch (e) { setErr(e.message || 'Could not save the post.'); } setBusy(''); };
  const download = async () => { setErr(''); try { const a = document.createElement('a'); a.href = await exportNow(); a.download = `${name.replace(/[^\w-]+/g, '-').slice(0, 40)}.png`; a.click(); } catch (e) { setErr(e.message || 'Could not export the post.'); } };
  const field = (k, label, ph, max, area) => <label className="pwr-field"><span className="m-label">{label}</span>
    {area ? <textarea className="m-input" rows={3} maxLength={max} value={post[k]} placeholder={ph} onChange={e => set({ [k]: e.target.value })} data-testid={`pwr-${k}`} />
      : <input className="m-input" maxLength={max} value={post[k]} placeholder={ph} onChange={e => set({ [k]: e.target.value })} data-testid={`pwr-${k}`} />}</label>;
  const seg = (k, opts, label) => <div className="m-seg" role="radiogroup" aria-label={label}>{opts.map(([v, l]) => <button key={v} type="button" role="radio" aria-checked={post[k] === v} className={post[k] === v ? 'active' : ''} onClick={() => set({ [k]: v })} data-testid={`pwr-${k}-${v}`} data-tip={`${label}: ${l}`}>{l}</button>)}</div>;
  const dragProps = useMemo(() => ({ draggable: true, onDragStart: e => { e.dataTransfer.setData('text/plain', 'pwr-post'); e.dataTransfer.effectAllowed = 'copy'; } }), []);

  return <div className="pwr" role="dialog" aria-modal="true" aria-label={`Content board: ${title}`} data-testid="poc-wire">
    <header className="pwr-h">
      <span className="pwr-t"><span className="m-label">PoC · content board</span><b>{title}</b></span>
      <div className="m-seg pwr-fmts" role="radiogroup" aria-label="Format">{FORMATS.map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={post.fmt === k} className={post.fmt === k ? 'active' : ''} onClick={() => set({ fmt: k })} data-testid={`pwr-fmt-${k}`} data-tip={`Lay the post out as a ${l}`}>{l}</button>)}</div>
      <span className="pwr-acts">
        <button type="button" className="m-btn" disabled={!!busy} onClick={download} data-tip="Downloads this post as a full-size PNG" data-testid="pwr-download"><Download size={14} /> PNG</button>
        <button type="button" className="m-btn m-go" disabled={!!busy} onClick={save} data-tip="Files this post into the proof as a new version; the original stays" data-testid="pwr-save"><Save size={14} /> {busy === 'save' ? 'Saving…' : 'Save to proof'}</button>
        <button type="button" className="m-btn pwr-x" onClick={onClose} aria-label="Close" data-tip="Close (Esc)" data-testid="pwr-close"><X size={16} /></button></span>
    </header>
    {err ? <p className="pwr-note is-bad" role="alert">⚠ {err}</p> : done ? <p className="pwr-note" role="status" data-testid="pwr-done">{done}</p> : null}
    <div className="pwr-body">
      <section className="pwr-stage m-live" aria-label="Post preview">
        <span className="pwr-tag m-chip ok">{day ? `Editing ${day}` : 'Draft'} · {fmt[2]}×{fmt[3]}</span>
        <AnimatePresence mode="wait"><motion.div key={post.fmt} className="pwr-surface" {...dragProps} data-tip="Drag onto a day to plan it" data-testid="pwr-surface"
          initial={{ opacity: 0, scale: 0.96, y: 8 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.96, y: -8 }} transition={{ duration: 0.2 }}>
          <Surface src={pic} post={post} /></motion.div></AnimatePresence>
      </section>
      <aside className="pwr-side m-card" aria-label="Words and framing">
        {field('headline', 'Headline', 'Big words on the post', 48)}
        {field('caption', 'Caption', 'What the post says under it', 160, true)}
        <div className="pwr-two">{field('handle', 'Handle', 'feeless', 24)}{field('cta', 'Button', 'Tap in', 18)}</div>
        <div className="pwr-row"><span className="m-label">Picture</span>{seg('fit', FITS, 'Picture')}</div>
        <div className="pwr-row"><span className="m-label">Words</span>{seg('spot', SPOTS, 'Words')}</div>
        <div className="pwr-row"><span className="m-label">Keep in view</span>
          <div className="pwr-focus" role="radiogroup" aria-label="Keep in view">{FOCI.map(f => <button key={f} type="button" role="radio" aria-checked={post.focus === f} className={post.focus === f ? 'active' : ''} onClick={() => set({ focus: f })} data-tip={`Crop around ${f}`} aria-label={`Crop around ${f}`} />)}</div></div>
        {day ? <label className="pwr-field"><span className="m-label">Posts at ({day})</span><input type="time" className="m-input" value={post.time} onChange={e => set({ time: e.target.value })} data-testid="pwr-time" /></label> : null}
      </aside>
    </div>
    <section className="pwr-week" aria-label="Week of content">
      <header><span className="m-label">Week of content <em>{n}/7 planned</em></span><span className="pwr-meter" aria-hidden="true"><i style={{ transform: `scaleX(${n / 7})` }} /></span></header>
      <ol>{DAYS.map((d, i) => { const p = week[d];
        return <li key={d} style={{ '--i': i }} className={`${p ? 'is-set' : ''}${day === d ? ' is-on' : ''}${over === d ? ' is-over' : ''}`}
          onDragOver={e => { e.preventDefault(); setOver(d); }} onDragLeave={() => setOver('')} onDrop={e => { e.preventDefault(); setOver(''); place(d); }}>
          <button type="button" className="pwr-day" onClick={() => open(d)} data-testid={`pwr-day-${d}`} data-tip={p ? `Edit ${d}'s post` : `Plan this post on ${d}`}>
            <span className="pwr-dh"><b>{d}</b>{p ? <small>{p.time}</small> : null}</span>
            {p ? <span className="pwr-thumb"><Surface src={pic} post={p} mini /></span> : <span className="pwr-empty"><Plus size={16} /><small>Drop or tap</small></span>}
            {p ? <small className="pwr-dl">{(FORMATS.find(f => f[0] === p.fmt) || FORMATS[0])[1]}</small> : null}
          </button>
          {p ? <button type="button" className="pwr-rm" onClick={() => drop(d)} aria-label={`Clear ${d}`} data-tip={`Clear ${d}`} data-testid={`pwr-rm-${d}`}><Trash2 size={13} /></button> : null}
        </li>; })}</ol>
    </section>
  </div>;
}
