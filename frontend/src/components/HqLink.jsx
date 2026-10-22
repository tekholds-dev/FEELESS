import React, { useEffect, useState } from 'react';
import QRCode from 'qrcode';
import { apiUrl } from '../lib/api';
import { PAIRED_KEY, SESSION_KEY } from '../lib/hqPaired';
import '../styles/hqLink.css';

// 📱 SCAN TO SIGN IN TO HQ (owner, 2026-10-21: "create a scan to sign in real quick, like Trust Wallet, so I can connect my Phantom").
// ONE page, two sides: on the COMPUTER (/hq-link) it shows a one-time QR and waits; on the PHONE (/hq-link?c=CODE, opened inside Phantom by
// that QR) it signs the normal HQ message — a message, never a transaction — and hands it to the computer once (backend/hq_pair.py).
// The computer then keeps the session like a normal sign-in and HQ opens for this wallet for ~24h.
const b64 = bytes => btoa(String.fromCharCode(...bytes));

// pure: the link the QR carries — Phantom's universal link opens our page INSIDE Phantom's browser (the wallet is right there)
export function pairLink(lan, port, code) {
  const site = `http://${lan}:${port}`;
  return `https://phantom.app/ul/browse/${encodeURIComponent(`${site}/hq-link?c=${code}`)}?ref=${encodeURIComponent(site)}`;
}

function Desk() {
  const [st, setSt] = useState({ phase: 'make' });
  const make = async () => {
    setSt({ phase: 'make' });
    try {
      const r = await fetch(apiUrl('/api/reputation/hq/pair'), { method: 'POST' }); const d = await r.json();
      if (!d.lan) throw new Error('This computer has no Wi-Fi address — connect it to the same Wi-Fi as your phone.');
      const link = pairLink(d.lan, window.location.port || '51367', d.code);
      const s = await QRCode.toString(link, { type: 'svg', margin: 1, color: { dark: '#04130b', light: '#e9fff2' } });
      setSt({ phase: 'wait', code: d.code, ttl: d.ttl, svg: s, lan: d.lan });
    } catch (e) { setSt({ phase: 'err', why: e.message }); }
  };
  useEffect(() => { make(); }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (st.phase !== 'wait') return undefined;
    const t = setInterval(async () => {
      try {
        const d = await (await fetch(apiUrl(`/api/reputation/hq/pair/${st.code}`))).json();
        if (d.status === 'expired') make();
        if (d.status === 'signed') { localStorage.setItem(SESSION_KEY, JSON.stringify(d.session)); localStorage.setItem(PAIRED_KEY, d.session.address); setSt({ phase: 'done', address: d.session.address }); }
      } catch { /* the next poll tries again */ }
    }, 2000);
    return () => clearInterval(t);
  }, [st.phase, st.code]);   // eslint-disable-line react-hooks/exhaustive-deps
  return <section className="hql" data-testid="hq-link">
    <header><b>📱 SCAN TO OPEN HQ</b><small>Phantom on your phone signs once — a message, never a transaction. Same Wi-Fi as this computer.</small></header>
    {st.phase === 'wait' ? <div className="hql-qr"><div className="hql-code" role="img" aria-label="QR code to sign in with Phantom" dangerouslySetInnerHTML={{ __html: st.svg }} />   {/* the SVG is drawn here by the qrcode library, never from the network */}<i className="hql-scan" aria-hidden="true" /></div> : null}
    {st.phase === 'wait' ? <ol className="hql-steps"><li>Open your phone's camera (or Phantom › scan) and point it here.</li><li>It opens FEELESS inside Phantom — tap <b>Sign</b>.</li><li>This page opens HQ by itself.</li></ol> : null}
    {st.phase === 'make' ? <p className="hql-note">Making a one-time code…</p> : null}
    {st.phase === 'err' ? <p className="hql-note is-bad">{st.why} <button type="button" className="m-btn" onClick={make}>Try again</button></p> : null}
    {st.phase === 'done' ? <div className="hql-done" data-testid="hq-link-done"><b>✅ HQ unlocked for {st.address.slice(0, 4)}…{st.address.slice(-4)}</b><small>~24h on this computer · trades still ask your phone wallet</small>
      <a className="m-btn m-go" href="/terminal">Open FEELESS → HQ</a></div> : null}
  </section>;
}

function Phone({ code }) {
  const [st, setSt] = useState({ phase: 'ready' });
  const sign = async () => {
    const ph = window.phantom?.solana || window.solana;
    if (!ph) { setSt({ phase: 'err', why: 'Open this link inside Phantom (scan the QR with Phantom, or tap "Open in Phantom").' }); return; }
    setSt({ phase: 'busy' });
    try {
      const { publicKey } = await ph.connect(); const address = publicKey.toString(); const ts = Math.floor(Date.now() / 1000);
      const r = await ph.signMessage(new TextEncoder().encode(`FEELESS HQ\naddress:${address}\nts:${ts}`), 'utf8');
      const res = await fetch(apiUrl(`/api/reputation/hq/pair/${code}`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address, ts, sig: b64(r?.signature || r) }) });
      const j = await res.json().catch(() => ({})); if (!res.ok) throw new Error(j.detail || 'Refused.');
      setSt({ phase: 'done' });
    } catch (e) { setSt({ phase: 'err', why: e?.code === 4001 ? 'Signature declined.' : e.message }); }
  };
  return <section className="hql is-phone" data-testid="hq-link-phone">
    <header><b>👑 FEELESS HQ</b><small>Sign once to open HQ on your computer. This is a message — no transaction, no funds move.</small></header>
    {st.phase === 'done' ? <div className="hql-done"><b>✅ Signed — look at your computer</b><small>You can close this.</small></div>
      : <button type="button" className="m-btn m-go hql-sign" disabled={st.phase === 'busy'} onClick={sign} data-testid="hq-link-sign">{st.phase === 'busy' ? 'Check Phantom…' : 'Sign with Phantom'}</button>}
    {st.phase === 'err' ? <p className="hql-note is-bad">{st.why}</p> : null}
  </section>;
}

export default function HqLink() {
  const code = new URLSearchParams(window.location.search).get('c');
  return <main className="hql-page">{code ? <Phone code={code} /> : <Desk />}</main>;
}
