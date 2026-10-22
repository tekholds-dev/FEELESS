import React, { useEffect, useState } from 'react';
import QRCode from 'qrcode';
import { apiUrl } from '../lib/api';
import { PAIRED_KEY, SESSION_KEY } from '../lib/hqPaired';
import '../styles/hqLink.css';

// 📱 SCAN TO SIGN IN TO HQ (owner, 2026-10-21: "create a scan to sign in real quick, like Trust Wallet, so I can connect my Phantom").
// ONE page, two sides. On the COMPUTER (/hq-link) it shows a one-time QR and waits. The QR is a PHANTOM DEEPLINK (the in-app browser froze on
// a plain-http page): the Phantom app opens on Connect, answers to this page on the phone's browser (/hq-link?c=CODE&s=connect…), which asks
// the service for the Sign-Message deeplink of the normal HQ message (a message, never a transaction); Phantom answers again (&s=sign…) and
// the service hands that verified session to the computer once (backend/hq_pair.py).
// The computer then keeps the session like a normal sign-in and HQ opens for this wallet for ~24h.

function Desk() {
  const [st, setSt] = useState({ phase: 'make' });
  const make = async () => {
    setSt({ phase: 'make' });
    try {
      const r = await fetch(apiUrl(`/api/reputation/hq/pair?port=${window.location.port || 51367}`), { method: 'POST' }); const d = await r.json();
      if (!d.link) throw new Error('This computer has no Wi-Fi address — connect it to the same Wi-Fi as your phone.');
      const link = d.link;
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
    {st.phase === 'wait' ? <ol className="hql-steps"><li>Point your phone's camera here (same Wi-Fi).</li><li>Phantom opens: tap <b>Connect</b>, then <b>Sign</b> the HQ message.</li><li>This page opens HQ by itself.</li></ol> : null}
    {st.phase === 'make' ? <p className="hql-note">Making a one-time code…</p> : null}
    {st.phase === 'err' ? <p className="hql-note is-bad">{st.why} <button type="button" className="m-btn" onClick={make}>Try again</button></p> : null}
    {st.phase === 'done' ? <div className="hql-done" data-testid="hq-link-done"><b>✅ HQ unlocked for {st.address.slice(0, 4)}…{st.address.slice(-4)}</b><small>~24h on this computer · trades still ask your phone wallet</small>
      <a className="m-btn m-go" href="/terminal">Open FEELESS → HQ</a></div> : null}
  </section>;
}

// the phone's side: relays Phantom's two answers (connect → the sign-message deeplink; sign → done). Phantom sends errorCode on a "no".
function Phone({ code }) {
  const q = new URLSearchParams(window.location.search); const step = q.get('s');
  const [st, setSt] = useState({ phase: step ? 'busy' : 'scan' });
  useEffect(() => {
    if (!step) return;
    if (q.get('errorCode')) { setSt({ phase: 'err', why: q.get('errorMessage') || 'Phantom said no.' }); return; }
    const body = { nonce: q.get('nonce') || '', data: q.get('data') || '', pub: q.get('phantom_encryption_public_key') || '', port: Number(window.location.port || 51367) };
    fetch(apiUrl(`/api/reputation/hq/pair/${code}/${step === 'connect' ? 'connect' : 'signed'}`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(async r => { const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || 'Refused.'); return j; })
      .then(j => { if (step === 'connect') window.location.href = j.link; else setSt({ phase: 'done' }); })
      .catch(e => setSt({ phase: 'err', why: e.message }));
  }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  return <section className="hql is-phone" data-testid="hq-link-phone">
    <header><b>👑 FEELESS HQ</b><small>One HQ message to sign in Phantom — no transaction, no funds move.</small></header>
    {st.phase === 'done' ? <div className="hql-done" data-testid="hq-link-ok"><b>✅ Signed — look at your computer</b><small>You can close this.</small></div> : null}
    {st.phase === 'busy' ? <p className="hql-note" data-testid="hq-link-busy">{step === 'connect' ? 'Connected — opening Phantom to sign…' : 'Checking the signature…'}</p> : null}
    {st.phase === 'scan' ? <p className="hql-note">Scan the QR on your computer with this phone's camera — Phantom opens by itself.</p> : null}
    {st.phase === 'err' ? <p className="hql-note is-bad" data-testid="hq-link-err">{st.why} Scan a fresh QR on the computer.</p> : null}
  </section>;
}

export default function HqLink() {
  const code = new URLSearchParams(window.location.search).get('c');
  return <main className="hql-page">{code ? <Phone code={code} /> : <Desk />}</main>;
}
