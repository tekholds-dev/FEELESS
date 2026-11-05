import React, { useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'sonner';
import { readMyCat, saveMyCat, DEFAULT_CAT } from '../../lib/myCat';
import { ALL_CHARACTERS, STYLES, load2d, peopleFile, thumbOf } from '../../lib/wireface';
import { goTo } from './FeeCatShell';
import { Ic3 } from '../../lib/icon3d';
import '../../styles/character.css';
import '../../styles/catBuilder.css';

// 🎭 BUILD AN AGENT (owner 2026-11-04: "new build a agent not cat"): pick who it is on a live stage, give it a name and a backdrop, then give it a job. A look only: nothing is signed or bought. Camera, voice and going live are in its Character folder once it exists.
export const PATTERNS = [['stripes', 'Stripes'], ['spots', 'Spots'], ['patch', 'Patch']];   // Fee's own desk still uses these
export const BACKDROPS = [['night', 'Night', '#0a1030'], ['neon', 'Neon', '#10291c'], ['violet', 'Violet', '#1d1138'], ['ember', 'Ember', '#2c1208'], ['ice', 'Ice', '#0d2733']];
const LINES = ['Who is on the desk today?', 'Ready when you are.', 'Show me the chart.', 'Let us prove it.'];
export function surprise(rnd = Math.random) {
  const pick = a => a[Math.floor(rnd() * a.length) % a.length];
  return { face: pick(ALL_CHARACTERS)[0], backdrop: pick(BACKDROPS)[0] };
}
export function CatBuilder() {
  const saved0 = readMyCat(); const [me, setMe] = useState(() => ({ face: saved0?.face || 'sarah', backdrop: saved0?.backdrop || 'night', name: saved0?.name || '' }));
  const [style, setStyle] = useState('All'); const [saved, setSaved] = useState(!!saved0?.face); const [fail, setFail] = useState(''); const stage = useRef(null); const faceRef = useRef(null); const sdkRef = useRef(null);
  const set = p => { setMe(m => ({ ...m, ...p })); setSaved(false); };
  const shown = ALL_CHARACTERS.find(c => c[0] === me.face) || ALL_CHARACTERS[0]; const bg = (BACKDROPS.find(b => b[0] === me.backdrop) || BACKDROPS[0])[2];
  const rows = useMemo(() => ALL_CHARACTERS.filter(c => style === 'All' || c[2] === style), [style]);
  const wear = async id => { const f = faceRef.current; if (!f) return; try { if (peopleFile(id)) await f.useCharacter(await sdkRef.current.loadCharacter(peopleFile(id))); else await f.useCharacter(id); f.express(['happy', 'amused', 'surprised', 'calm'][id.length % 4], 3); } catch { setFail('The character could not load.'); } };
  useEffect(() => { let dead = false; (async () => { try { const sdk = await load2d(); if (dead) return; sdkRef.current = sdk; faceRef.current = sdk.createFace2d(stage.current); await wear(me.face); } catch { if (!dead) setFail('This browser cannot show moving characters.'); } })(); return () => { dead = true; faceRef.current?.destroy(); faceRef.current = null; }; }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  const pick = id => { set({ face: id }); wear(id); };
  const keep = () => { saveMyCat({ ...DEFAULT_CAT, ...(readMyCat() || {}), ...me }); setSaved(true); toast.success(`${me.name || shown[1]} is your agent`); };
  const job = () => { saveMyCat({ ...DEFAULT_CAT, ...(readMyCat() || {}), ...me }); goTo('/terminal/feecat/agents?create=1'); };
  const roll = () => { const s = surprise(); set(s); wear(s.face); };
  return <section className="abx" data-testid="agent-builder" style={{ '--bg': bg }}>
    <div className="abx-studio"><i className="abx-beam" aria-hidden="true" /><div className="abx-frame"><canvas ref={stage} aria-label={`${shown[1]}, live`} data-testid="abx-canvas" />{fail ? <span className="chr-wait" role="alert">{fail}</span> : null}<span className="chr-tag"><b>{me.name || shown[1]}</b><em>{shown[2]}</em></span></div>
      <p className="abx-say" key={me.face}>“{LINES[me.face.length % LINES.length]}”</p>
      <div className="abx-acts"><button type="button" className="m-btn" onClick={roll} data-tip="A random character and backdrop" data-testid="abx-roll">Surprise me</button><button type="button" className="m-btn" onClick={keep} disabled={saved} data-testid="abx-keep">{saved ? 'Saved' : 'Make it mine'}</button><button type="button" className="m-btn m-go" onClick={job} data-tip="Create the agent with this character" data-testid="abx-job">Give it a job</button></div></div>
    <div className="abx-bench"><h2>Build an agent</h2>
      <label className="abx-name"><span className="m-label">NAME</span><input className="m-input" maxLength={32} value={me.name} onChange={e => set({ name: e.target.value })} placeholder={shown[1]} data-testid="abx-name" /></label>
      <div><span className="m-label">BACKDROP</span><div className="m-seg abx-seg" role="group" aria-label="Backdrop">{BACKDROPS.map(([k, l]) => <button key={k} type="button" className={me.backdrop === k ? 'active' : ''} onClick={() => set({ backdrop: k })} data-testid={`abx-bg-${k}`}>{l}</button>)}</div></div>
      <div className="chr-chips" role="group" aria-label="Art style">{STYLES.map(s => <button key={s} type="button" className={`m-chip${style === s ? ' is-on' : ''}`} aria-pressed={style === s} onClick={() => setStyle(s)}>{s}</button>)}</div>
      <div className="chr-grid">{rows.map(([id, n, s]) => <button key={id} type="button" className={`chr-tile${me.face === id ? ' is-on' : ''}`} onClick={() => pick(id)} aria-pressed={me.face === id} data-tip={`${n}, ${s}`} data-testid={`abx-${id}`}><img src={thumbOf(id)} alt="" loading="lazy" /><em>{s}</em><b>{n}</b></button>)}</div>
      <p className="chr-note"><Ic3 e="🎭" /> Your own picture, camera, voice and going live are in its Character folder.</p></div>
  </section>;
}
