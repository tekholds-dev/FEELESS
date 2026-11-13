import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useWallet } from '../hooks/useWallet';
import { clearAllChatSessions, getChatSession } from '../lib/chatSession';
import { apiUrl } from '../lib/api';
import { LEGAL_NEEDED, LEGAL_VERSION, forgetLegal, legalStatus, markAccepted } from '../lib/legal';
import '../styles/legal.css';

export { LEGAL_VERSION };
export const LEGAL_CONTACT = 'the FEELESS team via the official FEELESS channels';
const KEY = 'feeless:legal-consent';
let memoryAccepted = false; // fallback when browser storage is blocked, so we never nag within a visit

// ISO 3166-1 alpha-2 (+ XK, which CDNs use for Kosovo). Names come from the browser (Intl.DisplayNames), so no name list ships.
export const COUNTRIES = ('AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ '
  + 'DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR '
  + 'KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO '
  + 'RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS XK YE YT ZA ZM ZW').split(' ');
export function countryName(code) {
  try { return new Intl.DisplayNames([navigator.language || 'en', 'en'], { type: 'region' }).of(code) || code; } catch { return code; }
}

function visitorAccepted() {
  if (memoryAccepted) return true;
  try { return JSON.parse(localStorage.getItem(KEY) || 'null')?.v === LEGAL_VERSION; } catch { return false; }
}

export const LEGAL_DOCS = [['terms', 'Terms', 'What FEELESS is, what it isn\'t, and the deal between us'], ['risk', 'Risk', 'How you can lose money here — read before you sign'], ['privacy', 'Privacy', 'What we keep, what we never keep, and your data controls']];

// ⚖ The wallet's statement (LEGAL-1): its country, 18+, not sanctioned / not in a restricted place / no VPN. Signed with the wallet's chat
// session, stored per wallet with this terms version (backend/legal.py). Opens on a wallet's first connect and whenever a signing point is
// held for it (`feeless:legal-needed`). A visitor with no wallet gets the short notice only.
export function LegalConsent() {
  const { wallet, signMessage } = useWallet() || {};
  const address = wallet && !wallet.readOnly ? wallet.address : '';
  const [notice, setNotice] = useState(() => !visitorAccepted());
  const [open, setOpen] = useState(false);
  const [why, setWhy] = useState('');
  const [st, setSt] = useState(null);

  useEffect(() => {   // a newly connected wallet that hasn't accepted THIS version → ask once
    let live = true; setSt(null);
    if (!address) { setOpen(false); return undefined; }
    legalStatus(address).then(s => { if (!live) return; setSt(s); if (s?.accepted) markAccepted(address); else setOpen(true); }).catch(() => {});
    return () => { live = false; };
  }, [address]);
  useEffect(() => {
    const on = e => { const f = e?.detail?.feature; setWhy(f && f !== 'site' ? f : ''); setOpen(true); };
    window.addEventListener(LEGAL_NEEDED, on); return () => window.removeEventListener(LEGAL_NEEDED, on);
  }, []);
  const done = useCallback(() => { memoryAccepted = true; try { localStorage.setItem(KEY, JSON.stringify({ v: LEGAL_VERSION, at: new Date().toISOString() })); } catch { /* storage blocked */ } setNotice(false); setOpen(false); }, []);

  if (open && address) return <AcceptWindow address={address} signMessage={signMessage} st={st} feature={why} onDone={done} onLater={() => setOpen(false)} />;
  if (open && !address) return <div className="lgl-scrim" role="dialog" aria-modal="true" aria-labelledby="lgl-t" data-testid="legal-modal"><section className="lgl-win"><header><span className="m-label">TERMS · {LEGAL_VERSION}</span><h2 id="lgl-t">Connect a wallet first</h2></header><p className="lgl-lede">Your wallet states you're 18+ and where you live, once. Connect it, then try again.</p><footer><button type="button" className="m-btn" onClick={() => setOpen(false)} data-testid="legal-later">OK</button></footer></section></div>;
  if (!notice || address) return null;
  return <div className="legal-consent" role="dialog" aria-modal="false" aria-labelledby="legal-title" data-testid="legal-consent">
    <b id="legal-title">Before you trench 🌿</b>
    <p>FEELESS is a non-custodial crypto terminal. Nothing here is financial advice; crypto is high-risk and you can lose everything. We never hold your keys or funds. You must be 18+ and allowed to use crypto where you live — your wallet confirms that once when you connect.</p>
    <div><span className="lgl-links"><Link to="/terminal/terms">Terms</Link><Link to="/terminal/risk">Risk</Link><Link to="/terminal/privacy">Privacy</Link></span><button type="button" className="btn-primary" onClick={done} data-testid="legal-accept">Got it</button></div>
  </div>;
}

const FEATURE_WORD = { swap: 'swap', perps: 'trade perps', agents: 'run agents that trade', launch: 'launch a coin', games: 'play for points and prizes', brokers: 'link a broker' };

function AcceptWindow({ address, signMessage, st, feature, onDone, onLater }) {
  const blocked = useMemo(() => new Set(st?.sanctioned || ['CU', 'IR', 'KP', 'SY']), [st]);
  const list = useMemo(() => COUNTRIES.map(c => [c, countryName(c)]).sort((a, b) => a[1].localeCompare(b[1])), []);
  const [country, setCountry] = useState(() => st?.stated || (st?.country && COUNTRIES.includes(st.country) ? st.country : ''));
  const [adult, setAdult] = useState(false); const [clear, setClear] = useState(false);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState('');
  useEffect(() => { if (!country && st?.country && COUNTRIES.includes(st.country)) setCountry(st.country); }, [st, country]);
  const min = st?.minAge || 18;
  const ready = !!country && !blocked.has(country) && adult && clear && !busy;
  const submit = async e => {
    e.preventDefault(); if (!ready) return; setBusy(true); setErr('');
    try {
      const session = await getChatSession(address, signMessage);
      const r = await fetch(apiUrl('/api/reputation/legal/accept'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ wallet: address, session, version: LEGAL_VERSION, country, adult, notRestricted: clear }) });
      const b = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(b.detail || `Could not save (${r.status}).`);
      markAccepted(address); forgetLegal(address); onDone();
    } catch (x) { setErr(x?.message || 'Could not save — try again.'); } finally { setBusy(false); }
  };
  const seen = st?.country; const steps = [!!country && !blocked.has(country), adult, clear];
  return <div className="lgl-scrim" role="dialog" aria-modal="true" aria-labelledby="lgl-t" data-testid="legal-modal">
    <form className="lgl-win" onSubmit={submit}>
      <header><span className="m-label">TERMS · {LEGAL_VERSION}</span><h2 id="lgl-t">{feature ? `One step before you ${FEATURE_WORD[feature] || feature}` : 'Three things, once'}</h2>
        <ol className="lgl-steps" aria-label="Done so far">{steps.map((on, i) => <li key={i} className={on ? 'is-on' : ''} style={{ '--i': i }} />)}</ol></header>
      <p className="lgl-lede">FEELESS is an interface: you keep your keys and sign every trade. Like every on-chain app, we ask your wallet to state this once per terms version.</p>
      <label className="lgl-field"><span className="m-label">WHERE YOU LIVE</span>
        <select className="m-input" value={country} onChange={e => setCountry(e.target.value)} required data-testid="legal-country" data-tip="The country you live in. Some features are closed in some places.">
          <option value="">Pick your country…</option>
          {list.map(([c, n]) => <option key={c} value={c} disabled={blocked.has(c)}>{n}{blocked.has(c) ? ' — not available' : ''}</option>)}
        </select>
        {seen ? <small className="lgl-seen m-num">Your connection looks like {countryName(seen)} ({seen}).</small> : null}
      </label>
      <label className="lgl-check"><input type="checkbox" checked={adult} onChange={e => setAdult(e.target.checked)} data-testid="legal-adult" /><span><b>I'm {min} or older</b> (and an adult where I live).</span></label>
      <label className="lgl-check"><input type="checkbox" checked={clear} onChange={e => setClear(e.target.checked)} data-testid="legal-clear" /><span><b>I'm not a sanctioned person and not in a restricted place</b>, and I won't use a VPN to get around that.</span></label>
      <p className="lgl-read">By accepting you agree to the <Link to="/terminal/terms" target="_blank" rel="noopener noreferrer">Terms</Link>, have read the <Link to="/terminal/risk" target="_blank" rel="noopener noreferrer">Risk disclosure</Link> and the <Link to="/terminal/privacy" target="_blank" rel="noopener noreferrer">Privacy notice</Link>. Nothing here is financial advice.</p>
      {err ? <p className="lgl-err" role="alert" data-testid="legal-err">{err}</p> : null}
      <footer><button type="button" className="m-btn" onClick={onLater} data-testid="legal-later" data-tip="Close this. Trading stays held until you accept.">Not now</button>
        <button type="submit" className="m-btn m-go" disabled={!ready} data-testid="legal-submit" data-tip="Your wallet signs a sign-in message (no funds move), then we save these three answers with this terms version.">{busy ? 'Check your wallet…' : 'Accept and continue'}</button></footer>
    </form>
  </div>;
}

// 📜 Terms / Risk / Privacy: the ONE copy lives in public/legal/*.md (the lawyer edits those). [BRACKETS] are blanks the owner fills.
const inline = (s, k = 0) => s.split(/(\*\*[^*]+\*\*|\[[^\]]+\])/g).filter(Boolean).map((p, i) => (p.startsWith('**') ? <b key={`${k}-${i}`}>{p.slice(2, -2)}</b>
  : /^\[[^\]]+\]$/.test(p) ? <mark key={`${k}-${i}`} className="lgl-blank" data-tip="Not filled in yet">{p.slice(1, -1)}</mark> : p));
export function renderLegalMd(md) {
  const out = []; let list = null; let kind = '';
  const flush = () => { if (list) out.push(kind === 'ol' ? <ol key={out.length}>{list}</ol> : <ul key={out.length}>{list}</ul>); list = null; };
  String(md || '').split('\n').forEach((line, i) => {
    const t = line.trim(); let m;
    if (!t) { flush(); return; }
    if ((m = /^#\s+(.*)$/.exec(t))) { flush(); out.push(<h1 key={`h${i}`}>{m[1].replace(/\s+—\s+DRAFT.*$/i, '')}</h1>); return; }
    if ((m = /^\d+\.\s+(.*)$/.exec(t))) { if (kind !== 'ol') flush(); kind = 'ol'; (list ||= []).push(<li key={i}>{inline(m[1], i)}</li>); return; }
    if ((m = /^[-*]\s+(.*)$/.exec(t))) { if (kind !== 'ul') flush(); kind = 'ul'; (list ||= []).push(<li key={i}>{inline(m[1], i)}</li>); return; }
    flush(); out.push(<p key={i}>{inline(t, i)}</p>);
  });
  flush(); return out;
}

export function LegalPage({ doc = 'terms' }) {
  const d = LEGAL_DOCS.find(x => x[0] === doc) ? doc : 'terms';
  const [md, setMd] = useState(null);
  useEffect(() => { let live = true; setMd(null); fetch(`/legal/${d}.md`).then(r => (r.ok ? r.text() : Promise.reject())).then(t => live && setMd(t)).catch(() => live && setMd('')); return () => { live = false; }; }, [d]);
  const draft = /DRAFT/i.test((md || '').split('\n')[0] || '');
  return <article className="legal-page lgl-page" data-testid="legal-page">
    <nav className="m-seg lgl-tabs" aria-label="Legal pages">{LEGAL_DOCS.map(([id, t, tip]) => <Link key={id} to={`/terminal/${id}`} className={id === d ? 'active' : ''} aria-current={id === d ? 'page' : undefined} data-tip={tip} data-testid={`legal-tab-${id}`}>{t}</Link>)}</nav>
    <p className="legal-meta m-num">VERSION {LEGAL_VERSION}{draft ? ' · DRAFT — blanks marked are being filled in' : ''}</p>
    {md === null ? <p className="lgl-wait">Loading…</p> : md ? <div className="lgl-body" data-testid={`legal-doc-${d}`}>{renderLegalMd(md)}</div> : <p className="lgl-err">This page didn't load. Try again in a moment.</p>}
    {d === 'privacy' ? <p className="lgl-read">Export or delete your data yourself: <Link to="/terminal/settings#your-data">Settings › Your data</Link>.</p> : null}
  </article>;
}

const GONE_WORD = { profile: 'Profile', follows: 'Follows', notifications: 'Inbox', push: 'Phone push', dmPrefs: 'Message settings', identities: 'Linked accounts', dms: 'DMs you sent', chat: 'Chat posts', sessions: 'Sign-ins' };
// 👤 Settings › Your data (LEGAL-1): download everything FEELESS holds off-chain for this wallet, or delete the personal / social part.
export function MyDataCard() {
  const { wallet, signMessage } = useWallet() || {};
  const address = wallet && !wallet.readOnly ? wallet.address : '';
  const [busy, setBusy] = useState(''); const [msg, setMsg] = useState(''); const [typed, setTyped] = useState(''); const [gone, setGone] = useState(null);
  useEffect(() => {   // /terminal/settings#your-data (from the Privacy page): router navigation ignores the hash, so scroll here once mounted
    if (window.location.hash !== '#your-data') return undefined;
    const go = () => document.getElementById('your-data')?.scrollIntoView({ block: 'start' });   // again once the cards above have loaded and pushed it down
    const ts = [300, 1200, 2500].map(ms => setTimeout(go, ms)); return () => ts.forEach(clearTimeout);
  }, []);
  const run = async kind => {
    setBusy(kind); setMsg(''); setGone(null);
    try {
      const session = await getChatSession(address, signMessage, kind === 'delete' ? { own: true, fresh: true } : {});
      const r = await fetch(apiUrl(kind === 'delete' ? '/api/reputation/legal/delete' : '/api/reputation/legal/export'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ wallet: address, session, ...(kind === 'delete' ? { confirm: typed } : {}) }) });
      const b = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(b.detail || `Failed (${r.status}).`);
      if (kind === 'export') {
        const url = URL.createObjectURL(new Blob([JSON.stringify(b, null, 2)], { type: 'application/json' }));
        const a = document.createElement('a'); a.href = url; a.download = `feeless-data-${address.slice(0, 6)}-${new Date().toISOString().slice(0, 10)}.json`; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 2000);
        setMsg(`Downloaded: ${Object.keys(b.data || {}).length} kinds of data.`);
      } else {
        setGone(b); setTyped('');
        clearAllChatSessions();
      }
    } catch (x) { setMsg(`✗ ${x?.message || 'Something went wrong.'}`); } finally { setBusy(''); }
  };
  return <section id="your-data" className="m-card lgl-data" data-testid="my-data">
    <header><span className="m-label">YOUR DATA</span><h3>Download or delete what we hold</h3></header>
    {!address ? <p className="lgl-lede">Connect your wallet to see these controls.</p> : <>
      <div className="lgl-data-row"><span><b>Download everything</b><small>One JSON file: profile, follows, inbox, chat, DMs, receipts, points, consent. Secrets are never in it.</small></span>
        <button type="button" className="m-btn" disabled={!!busy} onClick={() => run('export')} data-testid="data-export" data-tip="Your wallet signs a sign-in message (no funds move), then the file downloads.">{busy === 'export' ? 'Preparing…' : 'Download'}</button></div>
      <div className="lgl-data-row is-danger"><span><b>Delete my data</b><small>Removes profile, follows, inbox, push, DMs you sent, chat posts, linked accounts and sessions. Kept: proof you accepted the terms, money receipts, points ledgers, security logs. On-chain data can't be deleted by anyone.</small></span>
        <span className="lgl-del"><input className="m-input" value={typed} onChange={e => setTyped(e.target.value)} placeholder="Type DELETE" aria-label="Type DELETE to confirm" data-testid="data-confirm" />
          <button type="button" className="m-btn lgl-btn-danger" disabled={typed !== 'DELETE' || !!busy} onClick={() => run('delete')} data-testid="data-delete" data-tip="Needs a sign-in from the last 24 hours. Cannot be undone.">{busy === 'delete' ? 'Deleting…' : 'Delete'}</button></span></div>
      {msg ? <p className={msg.startsWith('✗') ? 'lgl-err' : 'lgl-msg'} role="status" data-testid="data-msg">{msg}</p> : null}
      {gone ? <div className="lgl-gone" role="status" data-testid="data-gone"><b>Deleted. You're signed out.</b><ul>{Object.entries(gone.removed || {}).map(([k, n]) => <li key={k} className={n ? '' : 'is-zero'}><span>{GONE_WORD[k] || k}</span><i className="m-num">{n}</i></li>)}</ul></div> : null}
    </>}
  </section>;
}
