import React, { Suspense, lazy, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Map as MapIcon, Crown, Swords, Trophy, Radio } from 'lucide-react';
import { loadFamilia } from '../lib/familiaLoad';
import { useWallet } from '../hooks/useWallet';
import { useCrewBoard } from './CrewCard';
import { sharedJson } from '../lib/sharedJson';
import { FamiliaBackdrop, SCENES } from './FamiliaBackdrop';
import '../styles/familiaBackdrop.css';
import '../styles/familiaApp.css';

// 🌹 LA FAMILIA — ITS OWN APP (owner, 2026-10-23, F0.4: "Familia as its own application in FEELESS: its own bundle, own shell + nav, everything
// done inside it … fun and addicting, not sending people everywhere"). /familia/* is a full-screen app of its own: no terminal sidebar or top
// bars — a noir-gold shell with the drawn night scene of the tab you are on, the five places as its nav (deep links: /familia/city · family ·
// wars · board · live, the back button works), the city's live pulse (families, wars burning), your wallet, and one way out. The app inside
// is the same lazy Familia chunk (lib/familiaLoad) — trading, pools, perps and the streets all open IN here (the Familia trade dock).
const Crews = lazy(() => loadFamilia().then(m => ({ default: m.Crews })));
export const FA_NAV = [['home', 'city', 'Fee City', MapIcon, 'The city — every building is a real tool'], ['family', 'family', 'My family', Crown, 'Your family: block, HQ, seats, badge'],
  ['wars', 'wars', 'Wars', Swords, 'Family wars and raids — live'], ['board', 'board', 'Board', Trophy, 'The weekly family board + its room'], ['feed', 'live', 'Live', Radio, 'Everything happening in the families right now']];
const TAB_OF = Object.fromEntries(FA_NAV.map(([k, p]) => [p, k]));
const PATH_OF = Object.fromEntries(FA_NAV.map(([k, p]) => [k, p]));

function useLiveWars() {
  const [n, setN] = useState(0);
  useEffect(() => { let on = true; let t = null;
    const go = () => sharedJson('/api/reputation/crew-wars', { maxAge: 10000 }).then(x => on && x && setN((x.wars || []).filter(w => w.state === 'live').length)).catch(() => {})
      .finally(() => { if (on) t = setTimeout(go, document.hidden ? 45000 : 15000); });
    go(); return () => { on = false; clearTimeout(t); }; }, []);
  return n;
}

// 📲 La Familia installs as its own app (public/familia.webmanifest: start /familia/city, its own rose icon, standalone): the shell swaps in
// that manifest + theme colour while it is open and shows ⬇ INSTALL only when the browser offers it (beforeinstallprompt).
export function useFamiliaInstall() {
  const [ask, setAsk] = useState(null);
  useEffect(() => {
    const head = document.head; const made = [];
    const put = (sel, make) => { let el = head.querySelector(sel); const was = el ? { el, attrs: [...el.attributes].map(a => [a.name, a.value]) } : null; if (!el) { el = make(); head.appendChild(el); made.push(el); } return [el, was]; };
    const [mf, mfWas] = put('link[rel="manifest"]', () => Object.assign(document.createElement('link'), { rel: 'manifest' }));
    mf.setAttribute('href', '/familia.webmanifest');
    const [tc, tcWas] = put('meta[name="theme-color"]', () => Object.assign(document.createElement('meta'), { name: 'theme-color' }));
    tc.setAttribute('content', '#0b0806');
    const [ai] = put('link[rel="apple-touch-icon"]', () => Object.assign(document.createElement('link'), { rel: 'apple-touch-icon' }));
    ai.setAttribute('href', '/assets/familia/icon-192.png');
    const on = e => { e.preventDefault(); setAsk(() => e); };
    window.addEventListener('beforeinstallprompt', on);
    return () => { window.removeEventListener('beforeinstallprompt', on); made.forEach(el => el.remove());
      [[mf, mfWas], [tc, tcWas]].forEach(([el, was]) => { if (was) { [...el.attributes].forEach(a => el.removeAttribute(a.name)); was.attrs.forEach(([k, v]) => el.setAttribute(k, v)); } }); };
  }, []);
  const install = async () => { if (!ask) return; ask.prompt(); try { await ask.userChoice; } catch { /* dismissed */ } setAsk(null); };
  return [!!ask, install];
}

function Loading() {
  return <div className="fam-load" role="status" data-testid="familia-loading"><i className="fam-load-rose" aria-hidden="true" /><b>OPENING LA FAMILIA</b><small>the city, your block, the rooms…</small><u aria-hidden="true"><s /></u></div>;
}

// the drawn rose mark (petals + stem), the app's own sign — not an emoji
const Rose = () => <svg className="fa-rose" viewBox="0 0 32 32" aria-hidden="true"><path className="st" d="M16 31 C15 25 17 21 16 16" /><path className="lf" d="M16 24 C11 23 9 20 10 18 C13 18 15 20 16 24 Z" />
  <circle className="p3" cx="16" cy="11" r="7.5" /><path className="p2" d="M10 11 C10 6 13 4 16 5 C19 4 22 6 22 11 C19 9 13 9 10 11 Z" /><path className="p1" d="M13 10 C13 7.5 15 6.5 16 7.5 C17 6.5 19 7.5 19 10 C17 9 15 9 13 10 Z" /></svg>;

export default function FamiliaApp() {
  const nav = useNavigate(); const seg = (useParams()['*'] || '').split('/')[0];
  const tab = TAB_OF[seg] || 'home'; const setTab = k => nav(`/familia/${PATH_OF[k] || 'city'}`);
  const [scene, setScene] = useState('home');
  const { wallet, connect } = useWallet() || {}; const board = useCrewBoard(); const wars = useLiveWars(); const [canInstall, install] = useFamiliaInstall();
  useEffect(() => { const was = document.title; document.title = 'La Familia · FEELESS'; document.body.classList.add('in-familia');
    return () => { document.title = was; document.body.classList.remove('in-familia'); }; }, []);
  const short = a => (a ? `${a.slice(0, 4)}…${a.slice(-4)}` : '');
  const tabs = cls => FA_NAV.map(([k, , label, Icon, tip], i) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={`${cls} ${tab === k ? 'active' : ''}`} style={{ '--i': i }}
    onClick={() => setTab(k)} data-tip={tip} data-testid={`${cls}-${k}`}><Icon size={15} aria-hidden="true" /><span>{label}</span>{k === 'wars' && wars ? <b className="fa-badge">{wars}</b> : null}</button>);
  return <div className={`fa radar-page is-familia s-${scene}`} data-testid="familia-app">
    <FamiliaBackdrop scene={scene} />
    <header className="fa-bar">
      <Link to="/terminal" className="fa-exit" data-tip="Back to the FEELESS terminal" data-testid="fa-exit">← FEELESS</Link>
      <span className="fa-brand"><Rose /><span><b>LA FAMILIA</b><small key={scene}>{SCENES[scene]?.[0] || 'Fee City'}</small></span></span>
      <nav className="fa-nav" role="tablist" aria-label="La Familia">{tabs('fa-tab')}</nav>
      <span className="fa-pulse" data-tip="The families right now: how many there are and how many wars are burning">
        <span><i className="fa-dot" /><b className="m-num" key={board?.total}>{board?.total ?? '—'}</b><small>FAMILIES</small></span>
        <span className={wars ? 'is-hot' : ''}><b className="m-num" key={wars}>{wars}</b><small>WARS LIVE</small></span></span>
      {canInstall ? <button type="button" className="fa-install" onClick={install} data-tip="Install La Familia as its own app — its own icon, opens straight into Fee City" data-testid="fa-install">⬇ INSTALL</button> : null}
      {wallet?.address ? <span className="fa-wallet" data-tip={`Signed with ${wallet.name || 'your wallet'} · ${wallet.address}`} data-testid="fa-wallet"><i />{short(wallet.address)}</span>
        : <button type="button" className="fa-wallet is-off" onClick={() => connect?.('solana')} data-tip="Connect your Solana wallet — your family, your block and your trades live here" data-testid="fa-connect">Connect</button>}
    </header>
    <main className="fa-main"><Suspense fallback={<Loading />}><Crews bare tab={tab} onTab={setTab} onScene={setScene} /></Suspense></main>
    <nav className="fa-dock" role="tablist" aria-label="La Familia">{tabs('fa-dock-tab')}</nav>
  </div>;
}
