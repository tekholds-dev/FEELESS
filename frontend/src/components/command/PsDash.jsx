import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { boxRef } from '../../lib/boxRef';
import { FolderRidge } from './ProofKit';
import { TestTag } from './TrueRecord';
import '../../styles/psDash.css';

// 💻 THE PoStatic DESK DASHBOARD (Slice 27 · the desk bar, RULINGS 2026-11-20: "each proof type will have a user in it for hours"). A builder's
// dashboard, its own look (an editor: the live page big in a browser frame on a blueprint grid, versions as a timeline under it, the folder
// switcher, kits and the three checks beside it), never a copy of PoB / PoP / PoC. Inspect, the code and the 3D studio are one tap from the
// page. Every number is read from its folders (ws_open / ws_version / psFolders); a check that never ran says so instead of showing a score.
const TAB_KEY = 'feeless.psdTab'; const PICK_KEY = 'feeless.psdPick';
const TABS = [['folders', 'Folders'], ['filed', 'Filed'], ['parts', 'Parts'], ['kit', 'Kit']];
const box = boxRef([640, 980]);
const read = (k, d) => { try { return localStorage.getItem(k) || d; } catch { return d; } };
const keep = (k, v) => { try { localStorage.setItem(k, v); } catch { /* private window: it just forgets */ } };
const ago = s => { const m = Math.max(0, (Date.now() / 1000 - Number(s || 0)) / 60); return !s ? '' : m < 1 ? 'now' : m < 60 ? `${Math.round(m)}m` : m < 1440 ? `${Math.round(m / 60)}h` : `${Math.round(m / 1440)}d`; };
const slug = s => String(s || 'page').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'page';
const DEV = [['desktop', 'Desktop'], ['phone', 'Phone']];

/** Pure: each PoStatic folder with its filed rows (newest first), newest activity first. */
export function psFolders(folders, statics) {
  const rows = (statics || []).filter(Boolean);
  return (folders || []).filter(w => w && w.kind === 'build').map(w => {
    const mine = rows.filter(f => f.ws === w.id).sort((a, b) => (b.at || 0) - (a.at || 0));
    return { ...w, rows: mine, last: mine[0] || null, works: mine.filter(f => f.graded === 'right').length, top: Math.max(0, ...mine.map(f => Number(f.version) || 0)), seen: Math.max(Number(w.at) || 0, ...mine.map(f => Number(f.at) || 0)) };
  }).sort((a, b) => b.seen - a.seen);
}

/** Pure: a filed PoStatic's three checks (unique · clean · progress), each { ok, pct, val, why } or null when that check never ran on it. */
export function psChecks(f) {
  const u = f?.unique; const foot = f?.foot; const cc = f?.codeCheck; const kp = f?.keep;
  const unique = u ? { ok: !u.copy, pct: Math.round((1 - Number(u.like || 0)) * 100), val: `${Math.round(Number(u.like || 0) * 100)}% like`, why: `Closest earlier build: PoStatic #${u.nearest ?? '—'} (${Math.round(Number(u.like || 0) * 100)}% alike). ${u.briefNew ? 'A new brief' : 'A reused brief'}${u.centre ? `, centrepiece ${u.centre}` : ''}${u.layout ? `, layout ${u.layout}` : ''}.` }
    : foot ? { ok: !foot.repeat, pct: Number(foot.pct) || 0, val: foot.repeat ? 'a repeat' : `${foot.pct}% new`, why: foot.repeat ? `Its footprint repeats PoStatic #${foot.nearest} (filed before the uniqueness gate).` : `${foot.pct}% new footprint.` } : null;
  const failed = (cc?.failed || (cc?.checks || []).filter(c => !c.pass).map(c => c.id) || []);
  const clean = cc ? { ok: !failed.length, pct: Number(cc.pct) || (cc.total ? Math.round(100 * cc.passed / cc.total) : 0), val: `${cc.passed}/${cc.total}`, why: failed.length ? `The hidden code check failed: ${failed.join(', ')}.` : `All ${cc.total} hidden code checks passed${cc.seen?.phoneWidth ? `, on a ${cc.seen.phoneWidth}px phone` : ''}.` } : null;
  const progress = kp ? { ok: !(kp.lost || []).length, pct: kp.first ? 100 : kp.had ? Math.round(100 * kp.kept / kp.had) : 100, val: kp.first ? 'first page' : `${kp.kept}/${kp.had} kept`, why: kp.first ? `The first page: ${kp.parts} parts.` : (kp.lost || []).length ? `It lost ${kp.lost.join(', ')}, which page ${kp.from} had working.` : `Every part page ${kp.from} had is still working (${kp.parts} parts now).` } : null;
  return [['unique', 'UNIQUE', unique, 'Fingerprinted against every past build: a near-copy is refused before it files'], ['clean', 'CLEAN', clean, 'The hidden code check (never shown to the builders): overlaps, broken links, placeholders, a phone load'], ['progress', 'PROGRESS', progress, 'No back pedals: a new version may never lose a part the last one had working']]
    .map(([k, label, c, tip]) => ({ k, label, tip, c }));
}

function Checks({ f }) {
  const [open, setOpen] = useState(false); const rows = psChecks(f);
  return <div className={`psd-checks${open ? ' is-open' : ''}`} data-testid="psd-checks">
    <button type="button" className="psd-checks-row" aria-expanded={open} onClick={() => setOpen(o => !o)} data-tip={f ? `PoStatic #${f.n}'s checks. Tap for why` : 'Nothing filed from this folder yet'} data-testid="psd-checks-tg">
      {rows.map(({ k, label, c }) => <span key={k} className={`psd-ck ${!c ? 'is-none' : c.ok ? 'is-ok' : 'is-bad'}`} data-testid={`psd-ck-${k}`}>
        <i className="psd-ring" style={{ '--p': c ? c.pct / 100 : 0 }} aria-hidden="true" /><small>{label}</small><b className="m-num">{c ? c.val : 'not run'}</b></span>)}
      <em aria-hidden="true">{open ? '▴' : '▾'}</em></button>
    {open ? <ul className="psd-checks-why" data-testid="psd-checks-why">{rows.map(({ k, label, c, tip }) => <li key={k}><small>{label}</small><span>{c ? c.why : `Not run on ${f ? `PoStatic #${f.n}` : 'this folder'}: it was filed before this check existed, or nothing is filed yet. ${tip}.`}</span></li>)}</ul> : null}
  </div>;
}

function Kits({ doc }) {
  const used = (doc?.kitsUsed || []).filter(k => k && k.used !== false); const out = doc?.kitsOutside || [];
  return <div className="psd-kits" data-testid="psd-kits"><small className="psd-lab">KITS USED</small>
    {used.length ? used.map(k => <span key={k.id} className="psd-kit" data-tip={k.did || `${k.name} is in this page's code`}><i aria-hidden="true" />{k.name}</span>) : <span className="psd-mute">{doc ? 'no kit in this page' : '…'}</span>}
    {out.length ? <span className="psd-kit is-out" data-tip={`Not one of your kits: ${out.map(u => String(u).replace(/^(https?:)?\/\//, '').split('/')[0]).join(', ')}. Open the folder's issues tray for each`} data-testid="psd-kit-out">+{out.length} outside</span> : null}</div>;
}

function Stage({ cat, work, f, onOpen, onStudio }) {
  const [doc, setDoc] = useState(null); const [err, setErr] = useState(''); const [ver, setVer] = useState(null); const [dev, setDev] = useState('desktop');
  useEffect(() => { let on = true; setDoc(null); setVer(null); setErr(''); if (!f) return undefined;
    Promise.resolve(work(cat.id, { op: 'ws_open', text: f.id })).then(j => { if (on) setDoc(j?.doc || null); }).catch(e => { if (on) setErr(e.message || 'Could not open it.'); });
    return () => { on = false; }; }, [cat.id, f, work]);
  const pickV = async i => { if (!doc || i === doc.versions) { setVer(null); return; } setVer({ i, loading: true }); try { const j = await work(cat.id, { op: 'ws_version', text: f.id, i }); setVer({ i, ...j.version }); } catch (e) { setVer({ i, err: e.message || 'Could not read it.' }); } };
  const n = doc?.versions || 0; const filedAt = v => f?.rows.find(r => Number(r.version) === v);
  const page = ver?.preview || (ver ? null : doc?.preview); const by = ver ? ver.by : doc?.by;
  return <section className="psd-stage" data-testid="psd-stage">
    <header className="psd-chrome"><span className="psd-dots" aria-hidden="true"><i /><i /><i /></span>
      <span className="psd-url" data-tip="Its page runs here in a locked sandbox: no network, no keys">{slug(f?.name)}.static{n ? <em className="m-num"> · v{ver ? ver.i : n}{by ? ` · ${by}` : ''}</em> : null}</span>
      {ver ? <button type="button" className="psd-live" onClick={() => setVer(null)} data-tip="Back to its newest page" data-testid="psd-live">viewing v{ver.i} · back to v{n}</button> : n ? <span className="psd-livechip" data-testid="psd-latest"><i aria-hidden="true" />LATEST</span> : null}
      <span className="m-seg psd-dev" role="group" aria-label="Screen size">{DEV.map(([k, l]) => <button key={k} type="button" className={dev === k ? 'active' : ''} aria-pressed={dev === k} onClick={() => setDev(k)} disabled={!page} data-testid={`psd-dev-${k}`}>{l}</button>)}</span></header>
    <div className={`psd-screen is-${dev}`}>
      {page ? <iframe key={`${f?.id}-${ver?.i || 'n'}`} title={`${f?.name || 'page'} preview`} sandbox="allow-scripts" referrerPolicy="no-referrer" srcDoc={page} data-testid="psd-frame" />
        : <p className="psd-blank" data-testid="psd-blank">{err ? `⚠ ${err}` : !f ? 'No PoStatic folder yet. Name one above: the page you build shows here, big.' : !doc || ver?.loading ? 'Opening its page…' : ver?.err ? `⚠ ${ver.err}` : doc.busy ? 'Its minds are building the first page. It lands here.' : 'A blank screen. Open the folder and tell it what to make.'}</p>}
      {doc?.busy ? <span className="psd-busy" role="status" data-testid="psd-busy"><i aria-hidden="true" />{doc.busy.by || 'Building'} · {doc.busy.stage || 'working'}</span> : null}
    </div>
    <div className="psd-acts">
      <button type="button" className="m-btn m-go" onClick={() => onOpen(f, {})} disabled={!f} data-tip="Open the folder: the page, its chat and its tools side by side" data-testid="psd-open">Open to build</button>
      <button type="button" className="m-btn" onClick={() => onOpen(f, { inspect: true })} disabled={!doc?.preview || !!doc?.busy} data-tip="Opens the folder with inspect on: hover anything on the page (text, charts, 3D objects), click it to fix, edit or comment" data-testid="psd-inspect">⌖ Inspect</button>
      <button type="button" className="m-btn" onClick={() => onOpen(f, { view: 'code' })} disabled={!doc?.preview} data-tip="Its code: the file tree, what changed, the packages" data-testid="psd-code">{'</>'} Code</button>
      <button type="button" className="m-btn" onClick={() => onStudio(f)} disabled={!f} data-tip="This folder's 3D studio: tweak a model (size, turn, spin) and the next build uses that exact piece" data-testid="psd-studio">3D studio</button>
      <span className="psd-cost">{doc?.cost ? <><small>MINDS</small><b className="m-num">${Number(doc.cost).toFixed(doc.cost < 0.01 ? 4 : 2)}</b></> : null}</span>
    </div>
    {n ? <ol className="psd-vers" aria-label="Versions" data-testid="psd-vers">{Array.from({ length: n }, (_, k) => k + 1).map(i => { const r = filedAt(i); const on = ver ? ver.i === i : i === n;
      return <li key={i} style={{ '--i': Math.min(i, 20) }}><button type="button" className={`psd-v${on ? ' is-on' : ''}${r?.graded === 'right' ? ' is-good' : r?.graded === 'wrong' ? ' is-bad' : r ? ' is-filed' : ''}`} aria-pressed={on} onClick={() => pickV(i)}
        data-tip={`Page ${i}${r ? ` · filed as PoStatic #${r.n}${r.graded === 'right' ? ', it works' : r.graded === 'wrong' ? ', broken' : ', waiting for your mark'}` : ''}${i === n ? ' · the newest' : ''}`} data-testid={`psd-v-${i}`}><b className="m-num">v{i}</b>{r ? <i aria-hidden="true" /> : null}</button></li>; })}</ol> : null}
    <Kits doc={doc} />
  </section>;
}

/**
 * <PsDash cat work folders statics onOpen onStudio tiles filed parts kit />: the PoStatic home. onOpen(folder, {inspect, view}) opens the build
 * folder (inspect on / the code view), onStudio(folder) its 3D studio; tiles / filed / parts / kit are the folder's existing views, kept whole.
 */
export function PsDash({ cat, work, folders, statics, onOpen, onStudio, tiles = null, filed = null, parts = null, kit = null }) {
  const list = useMemo(() => psFolders(folders, statics), [folders, statics]);
  const [pick, setPick] = useState(() => read(PICK_KEY, '')); const [tab, setTab] = useState(() => read(TAB_KEY, 'folders'));
  const f = list.find(w => w.id === pick) || list.find(w => w.top) || list[0] || null;
  const choose = useCallback(id => { setPick(id); keep(PICK_KEY, id); }, []);
  const go = k => { setTab(k); keep(TAB_KEY, k); };
  const filedN = (statics || []).length; const works = (statics || []).filter(s => s.graded === 'right').length;
  return <section ref={box} className="psd" data-testid="psd">
    <div className="psd-top">
      <Stage cat={cat} work={work} f={f} onOpen={onOpen} onStudio={onStudio} />
      <aside className="psd-side" aria-label="Its folders and checks">
        <div className="psd-sum" data-testid="psd-sum"><span><small>FOLDERS</small><b className="m-num">{list.length}</b></span><span><small>FILED</small><b className="m-num">{filedN}</b></span>
          <span data-tip="Filed PoStatics you marked as working"><small>WORKS</small><b className="m-num">{works}<small>/{filedN}</small></b></span></div>
        <Checks f={f?.last || null} />
        <small className="psd-lab">ON THE STAGE · TAP A FOLDER</small>
        <ol className="psd-list" data-testid="psd-list">{list.slice(0, 8).map((w, i) => <li key={w.id} style={{ '--i': i }}><button type="button" className={`psd-row${f?.id === w.id ? ' is-on' : ''}`} aria-pressed={f?.id === w.id} onClick={() => choose(w.id)} onDoubleClick={() => onOpen(w, {})} data-tip={`Show ${w.name} on the stage (double-click opens it)`} data-testid={`psd-f-${w.id}`}>
          <FolderRidge fid={w.id} size={20} /><b>{w.name}</b><small className="m-num">{w.top ? `v${w.top}` : '—'}</small><em className="m-num" data-tip="Filed revisions you marked as working">{w.rows.length ? `${w.works}/${w.rows.length}` : ''}</em><TestTag f={w.last || {}} /><span className="psd-ago">{ago(w.seen)}</span></button></li>)}</ol>
        {list.length > 8 ? <button type="button" className="psd-more" onClick={() => go('folders')} data-testid="psd-all">All {list.length} folders ↓</button> : null}
      </aside>
    </div>
    <div className="m-seg psd-tabs" role="tablist" aria-label="PoStatic desk">{TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => go(k)} data-testid={`psd-tab-${k}`}>{l}{k === 'folders' ? <em className="m-num"> {list.length}</em> : k === 'filed' && filedN ? <em className="m-num"> {filedN}</em> : null}</button>)}</div>
    <div key={tab} className="psd-pane" role="tabpanel" data-testid={`psd-pane-${tab}`}>
      {tab === 'folders' ? tiles : tab === 'filed' ? (filed || <p className="psd-mute">Nothing filed yet. Every page its minds build files here as a PoStatic for your mark.</p>) : tab === 'parts' ? parts : kit}
    </div>
  </section>;
}
