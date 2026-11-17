import React, { useCallback, useEffect, useRef, useState } from 'react';
import { motion } from 'motion/react';
import { apiUrl } from '../../lib/api';
import { agentAuthQuery } from '../../lib/chatSession';
import '../../styles/assetShelf.css';

// 🗂 ASSET SHELF (owner 2026-11-15: "POC, POSTATIC, AND GAME FOLDERS'S STUDIOS NEED A DISCOVERY OR SOMETHING THEY CAN DOWNLOAD OR EVEN UPLOAD ASSETS
// TO THEIR FILE"). One shelf, every studio (agent_assets.py):
//   · DISCOVER  real free media from the source's own API: images and video (Wikimedia Commons), sound (Openverse: Freesound and more), 3D
//               (the CC0 library). Each one names its licence and creator. Keep saves a copy to My files; Use puts it straight into the studio.
//   · MY FILES  everything this agent's owner uploaded or kept: drop files in, download them any time, use them in any studio.
const WORD = { image: 'Images', video: 'Video', audio: 'Sound', model: '3D' };
const NOUN = { image: 'images', video: 'video', audio: 'sound', model: '3D models' };
const mb = n => (n >= 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.max(1, Math.round((n || 0) / 1e3))} KB`);
const b64Of = f => new Promise((ok, no) => { const r = new FileReader(); r.onload = () => ok(String(r.result).split(',')[1] || ''); r.onerror = () => no(new Error('That file could not be read.')); r.readAsDataURL(f); });
export const fileUrl = (catId, id, dl) => apiUrl(`/api/cats/${catId}/asset/${id}?${agentAuthQuery()}${dl ? '&dl=1' : ''}`);

function Face({ r, src }) {
  if (r.kind === 'image') return <img src={r.thumb || src} alt="" loading="lazy" />;
  if (r.kind === 'video') return r.thumb ? <img src={r.thumb} alt="" loading="lazy" /> : <video src={src} muted preload="metadata" playsInline />;
  if (r.kind === 'audio') return <span className="asf-wave" aria-hidden="true">{[5, 9, 4, 11, 7, 10, 3, 8, 6].map((h, i) => <i key={i} style={{ '--h': h, '--i': i }} />)}</span>;
  return r.thumb ? <img src={r.thumb} alt="" loading="lazy" /> : <span className="asf-cube" aria-hidden="true">🧊</span>;
}

export function AssetShelf({ cat, work, kinds = ['image', 'video', 'audio', 'model'], onUse, useKinds = null, useWord = 'Use', title = 'ASSETS', onDragUse = null }) {   // 🖐 onDragUse: drag a card onto the editor (2026-11-17)
  const [side, setSide] = useState('find'); const [kind, setKind] = useState(kinds[0]); const [q, setQ] = useState(''); const [found, setFound] = useState(null); const [down, setDown] = useState(false);
  const [mine, setMine] = useState(null); const [busy, setBusy] = useState(''); const [err, setErr] = useState(''); const [said, setSaid] = useState(''); const [hear, setHear] = useState(null); const audio = useRef(null);
  const list = useCallback(() => work(cat.id, { op: 'assets_list' }).then(setMine).catch(e => setErr(e.message)), [work, cat.id]);
  const find = useCallback((k = kind, text = q) => { setFound(null); setDown(false); return work(cat.id, { op: 'assets_find', job: k, text }).then(j => { setFound(j.rows || []); setDown(!!j.down); if (!text) setQ(j.q || ''); }).catch(e => { setErr(e.message); setFound([]); }); }, [work, cat.id, kind, q]);
  useEffect(() => { list(); find(kinds[0], ''); }, [cat.id]);   // eslint-disable-line react-hooks/exhaustive-deps
  const pick = k => { setKind(k); if (side === 'find') find(k, ''); };
  const keep = async r => { setBusy(r.id); setErr(''); try { const j = await work(cat.id, { op: 'assets_keep', tools: { url: r.url, name: r.name, lic: r.lic, by: r.by, src: r.src } }); setMine(j); setSaid(`Kept ${j.row.name} in My files.`); setBusy(''); return j.row; } catch (e) { setErr(e.message); setBusy(''); return null; } };
  const use = async (r, fromMine) => { if (!onUse) return; setErr('');
    if (r.lib) { setBusy(r.id); try { await onUse({ ...r, lib: true }); setSaid(`Added ${r.name}.`); } catch (e) { setErr(e.message); } setBusy(''); return; }
    const row = fromMine ? r : await keep(r); if (!row) return;
    setBusy(row.id); try { await onUse(row, fileUrl(cat.id, row.id)); setSaid(`${row.name} is in.`); } catch (e) { setErr(e.message); } setBusy(''); };
  const upload = async files => { for (const f of files) { setBusy('up'); setErr(''); try { const j = await work(cat.id, { op: 'assets_put', tools: { name: f.name, b64: await b64Of(f) } }); setMine(j); setSaid(`Uploaded ${j.row.name}.`); } catch (e) { setErr(e.message); } } setBusy(''); setSide('mine'); };
  const play = (id, src) => { if (hear === id) { audio.current?.pause(); setHear(null); return; } if (audio.current) { audio.current.src = src; audio.current.play().catch(() => {}); } setHear(id); };
  const rows = side === 'find' ? found : (mine?.rows || []).filter(r => r.kind === kind || (kind === 'model' && r.kind === 'file'));
  return <section className="asf" data-testid="asset-shelf" aria-label="Assets">
    <header className="asf-h"><b>{title}</b>
      <span className="m-seg" role="tablist" aria-label="Where">{[['find', 'Discover'], ['mine', `My files${mine?.rows ? ` · ${mine.rows.length}` : ''}`]].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={side === k} className={side === k ? 'active' : ''} onClick={() => setSide(k)} data-testid={`asf-${k}`}>{l}</button>)}</span>
      <span className="m-seg" role="group" aria-label="Kind">{kinds.map(k => <button key={k} type="button" aria-pressed={kind === k} className={kind === k ? 'active' : ''} onClick={() => pick(k)} data-testid={`asf-kind-${k}`}>{WORD[k]}</button>)}</span>
      <label className="m-btn asf-up" data-tip="Images, video, sound, 3D models, fonts and game files up to 25 MB each. They stay in this agent's files"><input type="file" multiple hidden onChange={e => { upload([...e.target.files]); e.target.value = ''; }} data-testid="asf-upload" />{busy === 'up' ? 'Uploading…' : '⬆ Upload'}</label></header>
    {side === 'find' ? <form className="asf-q" onSubmit={e => { e.preventDefault(); find(kind, q); }}><input className="m-input" value={q} onChange={e => setQ(e.target.value)} placeholder={`Search free ${NOUN[kind]}…`} aria-label="Search" data-testid="asf-q" /><button type="submit" className="m-btn">Search</button>
      <small>{kind === 'audio' ? 'Openverse · Freesound and more' : kind === 'model' ? 'CC0 3D library' : 'Wikimedia Commons'} · licence shown on each</small></form>
      : <p className="asf-use m-num">{mine?.max ? `${mb(mine.used)} of ${mb(mine.max)} used` : ''}</p>}
    {err ? <p className="asf-err" role="alert">⚠ {err}</p> : said ? <p className="asf-said" role="status">{said}</p> : null}
    {down && side === 'find' ? <p className="asf-err">That library is not answering right now. Try again in a minute.</p> : null}
    {rows == null ? <p className="asf-none">Searching…</p> : rows.length ? <ul className="asf-grid" data-testid="asf-grid">{rows.slice(0, 40).map((r, i) => { const src = side === 'mine' ? fileUrl(cat.id, r.id) : r.url; return <motion.li key={r.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(i, 16) * 0.02 }} data-testid="asf-row">
      <button type="button" className="asf-face" {...(onDragUse && onUse && (side === 'mine' || r.url || r.lib) && (r.lib || (useKinds || kinds).includes(r.kind)) ? { draggable: true, onDragStart: onDragUse(() => use(r, side === 'mine')) } : {})} onClick={() => (r.kind === 'audio' ? play(r.id, src) : r.page ? window.open(r.page, '_blank', 'noopener') : null)} data-tip={r.kind === 'audio' ? (hear === r.id ? 'Stop' : 'Listen') : r.page ? 'Open its page, with the full licence' : r.name}><Face r={r} src={src} />{r.kind === 'audio' ? <em>{hear === r.id ? '■' : '▶'}{r.secs ? ` ${r.secs}s` : ''}</em> : null}</button>
      <b title={r.name}>{r.name}</b><small title={`${r.lic} · ${r.by}`}>{[r.lic, r.by || r.src].filter(Boolean).join(' · ')}{side === 'mine' ? ` · ${mb(r.size)}` : ''}</small>
      <span className="asf-acts">{onUse && (side === 'mine' || r.url || r.lib) && (r.lib || (useKinds || kinds).includes(r.kind)) ? <button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => use(r, side === 'mine')} data-testid="asf-use">{busy === r.id ? '…' : useWord}</button> : null}
        {side === 'find' && r.url ? <button type="button" className="m-btn" disabled={!!busy} onClick={() => keep(r)} data-tip="Save a copy to My files" data-testid="asf-keep">Keep</button> : null}
        {side === 'mine' ? <><a className="m-btn" href={fileUrl(cat.id, r.id, true)} download={r.name} data-tip="Download to this computer" data-testid="asf-dl">⬇</a><button type="button" className="m-btn danger" disabled={!!busy} onClick={async () => { setMine(await work(cat.id, { op: 'assets_drop', text: r.id })); }} aria-label={`Delete ${r.name}`}>✕</button></> : null}</span></motion.li>; })}</ul>
      : <p className="asf-none">{side === 'mine' ? `No ${NOUN[kind]} in My files yet. Upload one, or Keep one from Discover.` : 'Nothing found. Try another word.'}</p>}
    <audio ref={audio} onEnded={() => setHear(null)} hidden />
  </section>;
}
