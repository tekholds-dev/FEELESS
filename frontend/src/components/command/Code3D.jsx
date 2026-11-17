import React, { useEffect, useMemo, useRef, useState } from 'react';
import '../../styles/code3d.css';
import { ModelTo } from './ModelTo';

// 💻 The 3D code playground (owner 2026-11-07: "a real 3D playground like GPT's, not just artifacts"). Real three.js you or its minds write,
// running live beside the code in the same locked sandbox a filed page uses: three.js loads, nothing else does. File it and it is a PoStatic.
const THREE_TAG = '<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/"}}</script>';
// 🪦 a real model's files load only from the hosts the server allows (asset_packs.SAFE_URL), and only when the code really names one
const HOSTS = [['https://dl.polyhaven.org/', 'https://dl.polyhaven.org'], ['https://raw.githubusercontent.com/ToxSam/', 'https://raw.githubusercontent.com/ToxSam/'], ['https://raw.githubusercontent.com/nasa/', 'https://raw.githubusercontent.com/nasa/'], ['https://huggingface.co/datasets/allenai/objaverse/', 'https://huggingface.co https://*.hf.co https://*.huggingface.co']];
const cspOf = code => { const on = HOSTS.filter(([seen]) => String(code || '').includes(seen)).map(([, allow]) => ` ${allow}`).join(''); return `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data: blob:${on}; style-src 'unsafe-inline'; script-src 'unsafe-inline' https://cdn.jsdelivr.net/npm/three@0.170.0/; connect-src blob: data:${on}">`; };
const oneLine = t => String(t || '').replace(/\s+/g, ' ').slice(0, 60);
export const modelCode = (a, height = 1.6) => `
// 🪦 ${oneLine(a.name)}: a real model (${a.lic === 'by' ? `CC BY, by ${oneLine(a.by)}` : 'CC0'}). Move, size or restyle it here, or ask its minds.
import('three/addons/loaders/GLTFLoader.js').then(({ GLTFLoader }) => {
  const files = ${JSON.stringify(a.files || {})}, lm = new THREE.LoadingManager();
  lm.setURLModifier(u => files[decodeURI(u.split('/').pop().split('?')[0])] || u);
  new GLTFLoader(lm).load(${JSON.stringify(a.url)}, g => {
    const m = g.scene, box = new THREE.Box3().setFromObject(m), k = ${height} / (box.getSize(new THREE.Vector3()).y || 1);
    m.scale.setScalar(k); m.position.y = -box.min.y * k; m.name = ${JSON.stringify(oneLine(a.name))}; scene.add(m);
  });
});
`;
// 🛡 the preview's watcher: crashes, AND a page that never drew (owner 2026-11-12, AGT-17: NOVA "opened black" and nothing said why). WebGL keeps its
// last frame here (preview only) so it can be looked at: no canvas, or almost nothing lit after 6 s, is reported as black instead of "running".
const ERR = "<script>function say(t,m){try{parent.postMessage({t:t,m:String(m||'').slice(0,240)},'*')}catch(_){}}addEventListener('error',function(e){say('p3c-err',e.message+(e.lineno?' (line '+Math.max(1,e.lineno-1)+')':''))});addEventListener('unhandledrejection',function(e){say('p3c-err',e.reason&&e.reason.message||e.reason)});"
  + "var gc=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(k,o){if(/webgl/.test(k))o=Object.assign({},o,{preserveDrawingBuffer:true});return gc.call(this,k,o)};"
  + "function look(last){var c=document.querySelector('canvas');if(!c){if(last)say('p3c-dark','No canvas: the code never added its renderer to the page.');return}try{var g=document.createElement('canvas');g.width=48;g.height=48;var x=g.getContext('2d');x.drawImage(c,0,0,48,48);var d=x.getImageData(0,0,48,48).data,lit=0;for(var i=0;i<d.length;i+=4){if(d[i]+d[i+1]+d[i+2]>90)lit++}if(lit>11){say('p3c-ok');return true}if(last)say('p3c-dark','It drew almost nothing in 6 seconds: the page looks black.')}catch(_){say('p3c-ok');return true}}"
  + "setTimeout(function(){if(!look(false))setTimeout(function(){look(true)},3500)},2500);"
  // ⏱ real frame rate, measured inside the page on this machine's GPU (AGT-17 "real FPS"): frames per second + the slowest frame, once a second
  + "(function(){var n=0,t0=0,w=0,l=0;function f(t){if(!t0)t0=t;if(l&&t-l>w)w=t-l;l=t;n++;if(t-t0>=1000){say('p3c-fps',Math.round(n*1000/(t-t0))+'|'+Math.round(w));n=0;t0=t;w=0}requestAnimationFrame(f)}requestAnimationFrame(f)})()</script>";
export const pageOf = code => `<!doctype html><html><head><meta charset="utf-8">${cspOf(code)}${THREE_TAG}${ERR}<style>html,body{margin:0;height:100%;overflow:hidden;background:#05070a}canvas{display:block}</style></head><body><script type="module">\n${String(code || '').replace(/<\/script/gi, '<\\/script')}\n</script></body></html>`;

const BASE = (body, loop) => `import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.1, 200);
camera.position.set(0, 2, 7);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
addEventListener('resize', () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });
const pointer = new THREE.Vector2();
addEventListener('pointermove', e => pointer.set(e.clientX / innerWidth * 2 - 1, -(e.clientY / innerHeight) * 2 + 1));
${body}
const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const t = clock.getElapsedTime();
${loop}
  controls.update();
  renderer.render(scene, camera);
});
`;
export const STARTERS = [
  ['Blank', 'An empty stage: write your own, ask its minds, or add a real model', BASE(`scene.background = new THREE.Color('#05070a');
const ground = new THREE.Mesh(new THREE.CircleGeometry(12, 64), new THREE.MeshStandardMaterial({ color: '#3a4d44', roughness: 0.9 }));
ground.rotation.x = -Math.PI / 2; scene.add(ground);
scene.add(new THREE.GridHelper(24, 24, '#4f6b5e', '#2a3a33'));
scene.add(new THREE.HemisphereLight('#ffffff', '#223344', 1.4));
const sun = new THREE.DirectionalLight('#ffffff', 2.5); sun.position.set(3, 6, 4); scene.add(sun);`, '')],
  ['Glow knot', 'A metal knot under two coloured lights', BASE(`scene.background = new THREE.Color('#05070a');
const knot = new THREE.Mesh(new THREE.TorusKnotGeometry(1.2, 0.38, 220, 32), new THREE.MeshStandardMaterial({ color: '#d7fbe8', metalness: 0.9, roughness: 0.18 }));
scene.add(knot);
const a = new THREE.PointLight('#9b6bff', 60, 20); a.position.set(3, 2, 3); scene.add(a);
const b = new THREE.PointLight('#5b7cff', 60, 20); b.position.set(-3, -1, 2); scene.add(b);
scene.add(new THREE.AmbientLight('#ffffff', 0.15));`, `  knot.rotation.set(t * 0.3 + pointer.y * 0.6, t * 0.4 + pointer.x * 0.6, 0);
  a.position.x = Math.sin(t) * 4; b.position.z = Math.cos(t * 0.7) * 4;`)],
  ['Galaxy', '40,000 particles in a spiral', BASE(`const N = 40000, pos = new Float32Array(N * 3), col = new Float32Array(N * 3);
const inner = new THREE.Color('#ffb36b'), outer = new THREE.Color('#3b6cff');
for (let i = 0; i < N; i++) {
  const r = Math.random() * 5, arm = (i % 3) / 3 * Math.PI * 2, spin = r * 1.1;
  const rx = Math.pow(Math.random(), 3) * (Math.random() < 0.5 ? 1 : -1) * 0.5;
  const rz = Math.pow(Math.random(), 3) * (Math.random() < 0.5 ? 1 : -1) * 0.5;
  pos.set([Math.cos(arm + spin) * r + rx, (Math.random() - 0.5) * 0.25, Math.sin(arm + spin) * r + rz], i * 3);
  const c = inner.clone().lerp(outer, r / 5); col.set([c.r, c.g, c.b], i * 3);
}
const g = new THREE.BufferGeometry();
g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('color', new THREE.BufferAttribute(col, 3));
const stars = new THREE.Points(g, new THREE.PointsMaterial({ size: 0.025, vertexColors: true, depthWrite: false, blending: THREE.AdditiveBlending }));
scene.add(stars); camera.position.set(0, 4, 7);`, `  stars.rotation.y = t * 0.08 + pointer.x * 0.3;`)],
  ['Wave field', 'A shader terrain that breathes', BASE(`scene.background = new THREE.Color('#03060a');
const mat = new THREE.ShaderMaterial({ wireframe: true, uniforms: { uT: { value: 0 } },
  vertexShader: 'uniform float uT; varying float vH; void main(){ vec3 p = position; p.z = sin(p.x*1.4+uT)*0.35 + cos(p.y*1.1+uT*0.8)*0.35; vH = p.z; gl_Position = projectionMatrix*modelViewMatrix*vec4(p,1.0); }',
  fragmentShader: 'varying float vH; void main(){ gl_FragColor = vec4(mix(vec3(0.05,0.4,0.25), vec3(0.3,1.0,0.6), vH+0.5), 1.0); }' });
const field = new THREE.Mesh(new THREE.PlaneGeometry(14, 14, 120, 120), mat);
field.rotation.x = -Math.PI / 2.4; scene.add(field);`, `  mat.uniforms.uT.value = t + pointer.x;`)],
];

export function Code3D({ cat, work, initial = '', minds = [], chat: chat0 = [], proof = null, builds = [] }) {
  const [code, setCode] = useState(initial || STARTERS[0][2]); const [run, setRun] = useState(initial || STARTERS[0][2]); const [err, setErr] = useState(''); const [ok, setOk] = useState(false); const [fps, setFps] = useState(null);
  const [who, setWho] = useState('both'); const [chat, setChat] = useState(chat0); const [prev, setPrev] = useState(''); const log = useRef(null);
  useEffect(() => { log.current?.scrollTo?.({ top: 1e6 }); }, [chat.length]);
  const [ask, setAsk] = useState(''); const [busy, setBusy] = useState(''); const [said, setSaid] = useState(''); const [name, setName] = useState('3D playground'); const frame = useRef(null);
  useEffect(() => { if (code === run) return undefined; const t = setTimeout(() => { setErr(''); setOk(false); setFps(null); setRun(code); }, 700); return () => clearTimeout(t); }, [code, run]);
  useEffect(() => { const on = e => { if (e.source !== frame.current?.contentWindow) return; if (e.data?.t === 'p3c-err') { setErr(e.data.m); setOk(false); } if (e.data?.t === 'p3c-dark') { setErr(o => o || `It opened black. ${e.data.m}`); setOk(false); } if (e.data?.t === 'p3c-ok') setOk(o => o || true); if (e.data?.t === 'p3c-fps') { const [f, w] = String(e.data.m).split('|').map(Number); setFps({ f, w }); } }; window.addEventListener('message', on); return () => window.removeEventListener('message', on); }, []);
  const page = useMemo(() => pageOf(run), [run]); const lines = code.split('\n').length;
  const go = async (op, extra) => { setBusy(op); setSaid(''); try { const j = await work(cat.id, { op, ...extra }); return j; } catch (e) { setSaid(`⚠ ${e.message}`); return null; } finally { setBusy(''); } };
  const askMinds = async (e, said0) => { e?.preventDefault?.(); const q = (said0 || ask).trim(); if (!q) return; const j = await go('play3d_code', { text: q, job: code, to: who }); if (j?.code) { setPrev(code); setCode(j.code); setRun(j.code); setErr(''); setAsk(''); if (j.chat) setChat(j.chat); setSaid(`${j.by}${j.model ? ` (${j.model})` : ''} wrote it · $${Number(j.usd || 0).toFixed(4)}`); } };
  const undo = () => { if (!prev) return; setCode(prev); setRun(prev); setPrev(''); setErr(''); setSaid('Back to the code before that change.'); };
  const save = async () => { const j = await go('play3d_code_save', { job: code }); if (j) setSaid('Saved with this agent.'); };
  const file = async () => { const j = await go('play3d_code_file', { job: code, text: name }); if (j?.filed) setSaid(j.into ? `Saved into ${j.into} as its newest page, filed as PoStatic #${j.filed.n}.` : `Filed as PoStatic #${j.filed.n}. It runs as its own page.`); };
  // 🪦 a real model from the shelf goes into the code (its minds can tweak it), and from here to a build that uses it throughout the site
  const [shelf, setShelf] = useState(false); const [q, setQ] = useState(''); const [rows, setRows] = useState([]); const [models, setModels] = useState([]); const [adding, setAdding] = useState('');
  useEffect(() => { if (!shelf) return undefined; let on = true; const t = setTimeout(() => { Promise.resolve().then(() => work(cat.id, { op: 'play3d_assets', job: 'model', text: q })).then(j => { if (on) setRows((j.rows || []).slice(0, 24)); }).catch(e => on && setSaid(`⚠ ${e.message}`)); }, 250); return () => { on = false; clearTimeout(t); }; }, [shelf, q, cat.id, work]);
  const addModel = async r => { setAdding(r.id); setSaid(''); try { const { asset } = await work(cat.id, { op: 'play3d_assets', job: 'model', to: r.id }); const next = `${code.replace(/\s+$/, '')}\n${modelCode(asset)}`; setCode(next); setRun(next); setErr(''); setModels(ms => [...ms.filter(m => m.asset.id !== asset.id), { id: `code-${asset.id}`, shape: 'model', name: asset.name, asset, pos: [0, 0, 0], rot: [0, 0, 0], scale: [1, 1, 1], height: 1.6, spin: 0 }]); setSaid(`${asset.name} is in the code. Move or restyle it there, or ask its minds.`); } catch (e) { setSaid(`⚠ ${e.message}`); } setAdding(''); };
  return <div className="p3c" data-testid="p3c">
    <section className="p3c-code"><header className="p3c-bar"><span className="m-seg" role="group" aria-label="Starters">{STARTERS.map(([t, tip, c]) => <button key={t} type="button" className={code === c ? 'active' : ''} onClick={() => { setCode(c); setRun(c); setErr(''); }} data-tip={tip} data-testid={`p3c-start-${t}`}>{t}</button>)}</span><small className="m-num" data-tip="Lines of code">{lines} lines</small></header>
      <div className="p3c-edit"><pre className="p3c-gut" aria-hidden="true">{Array.from({ length: lines }, (_, i) => i + 1).join('\n')}</pre><textarea value={code} onChange={e => setCode(e.target.value)} spellCheck={false} aria-label="three.js code" data-testid="p3c-input" onKeyDown={e => { if (e.key === 'Tab') { e.preventDefault(); const el = e.target; const s = el.selectionStart; setCode(code.slice(0, s) + '  ' + code.slice(el.selectionEnd)); requestAnimationFrame(() => { el.selectionStart = el.selectionEnd = s + 2; }); } if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { setErr(''); setRun(code + ' '); } }} /></div>
      {err ? <p className="p3c-err" role="alert" data-testid="p3c-err"><span>⚠ {err}</span>{minds.length ? <button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => askMinds(null, `The page fails: ${err} Find the cause and fix it. Keep everything else as it is.`)} data-tip="Sends this exact error to its minds and asks for the fix. One model call" data-testid="p3c-fixit">{busy === 'play3d_code' ? 'Fixing…' : 'Fix it with its minds'}</button> : null}</p> : null}
      {chat.length ? <ol className="p3c-chat" ref={log} aria-label="What you asked and what its minds said" data-testid="p3c-chat">{chat.map((m, i) => <li key={i} className={m.by === 'you' ? 'is-you' : ''}><small>{m.by === 'you' ? 'YOU' : `${m.by.toUpperCase()}${m.model ? ` · ${m.model}` : ''}`}{m.usd ? <em> · ${Number(m.usd).toFixed(4)}</em> : null}</small><p>{m.text}</p></li>)}</ol> : null}
      {minds.length ? <span className="m-seg p3c-who" role="radiogroup" aria-label="Which mind writes">{[...minds.map((m, i) => [String(i), `${'AB'[i]} · ${m}`, `Only Mind ${'AB'[i]} (${m}) writes the next change`]), ...(minds.length > 1 ? [['both', 'Take turns', 'Mind A and Mind B lead in turn']] : [])].map(([k, l, tip]) => <button key={k} type="button" role="radio" aria-checked={who === k} className={who === k ? 'active' : ''} onClick={() => setWho(k)} data-tip={tip} data-testid={`p3c-who-${k}`}>{l}</button>)}</span> : <p className="p3c-said">Pick this agent's models on its desk (Minds) to ask for code.</p>}
      <form className="p3c-ask" onSubmit={askMinds}><input className="m-input" value={ask} onChange={e => setAsk(e.target.value)} placeholder="Ask its minds: add bloom, make it rain, turn it into a planet…" aria-label="Ask its minds to change the code" data-testid="p3c-ask" /><button type="submit" className="m-btn m-go" disabled={!!busy || !ask.trim()} data-tip="One model call. With two minds they take turns" data-testid="p3c-send">{busy === 'play3d_code' ? 'Writing…' : 'Ask'}</button><button type="button" className="m-btn" disabled={!prev || !!busy} onClick={undo} data-tip="Back to the code before the last change" data-testid="p3c-undo">Undo</button></form></section>
    <section className="p3c-run"><header className="p3c-bar"><span className={`p3c-dot${err ? ' is-bad' : ok ? ' is-ok' : ''}`} aria-hidden="true" /><b>{err ? 'STOPPED' : ok ? 'RUNNING' : 'STARTING'}</b><small>three.js 0.170 · locked sandbox</small>{fps && !err ? <span className={`p3c-fps m-num ${fps.f >= 50 ? 'is-ok' : fps.f >= 30 ? 'is-warn' : 'is-bad'}`} data-tip={`Real frames per second on this machine's GPU, measured inside the page. Slowest frame in the last second: ${fps.w} ms`} data-testid="p3c-fps">{fps.f} FPS</span> : null}<button type="button" className="m-btn" onClick={() => { setErr(''); setRun(code + ' '); }} data-tip="Run it again (Cmd/Ctrl + Enter)" data-testid="p3c-run">↻ Run</button></header>
      <iframe ref={frame} key={page.length + run.slice(-8)} title="3D playground" sandbox="allow-scripts" srcDoc={page} data-testid="p3c-frame" />
      <footer className="p3c-foot"><input className="m-input" value={name} maxLength={40} onChange={e => setName(e.target.value)} aria-label="Page name" /><button type="button" className="m-btn" aria-pressed={shelf} onClick={() => setShelf(v => !v)} data-tip="Real models from the 3D library, put into this code" data-testid="p3c-models">Add a model</button><button type="button" className="m-btn" disabled={!!busy} onClick={save} data-tip={proof ? `Keeps this code with ${proof.name}` : 'Keeps this code until you leave'} data-testid="p3c-save">Save</button><button type="button" className="m-btn m-go" disabled={!!busy || !!err} onClick={file} data-tip={proof ? `Makes a real page of it and adds it to ${proof.name}` : 'Makes a real page of it and files it as a new PoStatic'} data-testid="p3c-file">{proof ? 'Save to this proof' : 'File as PoStatic'}</button></footer>
      {shelf ? <div className="p3c-models" data-testid="p3c-shelf"><input className="m-input" value={q} onChange={e => setQ(e.target.value)} placeholder="tombstone, chair, camera…" aria-label="Find a real model" data-testid="p3c-q" /><div className="p3c-mrows">{rows.map(r => <button key={r.id} type="button" disabled={!!adding} onClick={() => addModel(r)} data-tip={`${r.name} · ${r.lic || 'CC0'}`} data-testid={`p3c-m-${r.id}`}>{r.thumb ? <img src={r.thumb} alt="" loading="lazy" /> : null}<span>{adding === r.id ? 'Adding…' : r.name}</span></button>)}{!rows.length ? <small>No model by that word. Try another.</small> : null}</div>
        {models.map(m => <div key={m.id} className="p3c-mto"><b>{m.name}</b><ModelTo obj={m} builds={builds} proof={proof} cat={cat} work={work} onSaid={setSaid} onErr={t => t && setSaid(`⚠ ${t}`)} /></div>)}</div> : null}
      {said ? <p className="p3c-said" role="status" data-testid="p3c-said">{said}</p> : null}</section>
  </div>;
}
