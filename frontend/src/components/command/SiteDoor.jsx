import React, { useCallback, useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { Ic3 } from '../../lib/icon3d';
import { agentAuthQuery } from '../../lib/chatSession';
import '../../styles/siteDoor.css';

// 🌐 THE SITE DOOR (owner 2026-11-04): every proof folder has an address bar. Type a site, sign in by hand in its live window, hit Scan.
// The scan files a manual from the site's own pages, and a site that is both read and signed in earns its own command ("file a pump pow").
const WORD = { pow: 'PoW', pop: 'PoP', pob: 'bid' };
const HINT = { pow: 'pump.fun, axiom.trade', pop: 'hyperliquid.xyz, coinglass.com', pob: 'polymarket.com, kalshi.com' };
const STATE = {
  read: ['READ', 'Its terms were read. No bot ban or region rule stood out'],
  caution: ['CAUTION', 'Its own terms ban bots or limit regions. Read those tabs first'],
  thin: ['NO TERMS FOUND', 'It read some pages but found no terms page'],
  unread: ['NOT READ', 'No page could be read. Usually a human check'],
};
const BOTS = { banned: ['BOTS BANNED', 0.12], mentioned: ['BOTS MENTIONED', 0.55], silent: ['NOT STATED', 0.35] };
const TABS = [['do', 'Do'], ['dont', "Don't"], ['withdraw', 'Withdraw'], ['fees', 'Fees'], ['bots', 'Bots'], ['regions', 'Regions'], ['risk', 'Risk'], ['pages', 'Pages']];
const EMPTY = {
  do: 'Its pages list nothing you must do.', dont: 'Its pages list no ban.', fees: 'Its pages state no fee numbers. Check before you trade.',
  withdraw: "Its pages don't say how money comes out. Find that out before you deposit.", bots: 'Its pages say nothing about bots.', regions: 'Its pages name no region limit.', risk: 'Its pages state no risk warning.',
};
const safeHref = u => (/^https?:\/\//i.test(String(u || '')) ? u : undefined);
const agoOf = t => { const s = Math.max(0, Date.now() / 1000 - (t || 0)); return s < 90 ? 'just now' : s < 5400 ? `${Math.round(s / 60)}m ago` : s < 129600 ? `${Math.round(s / 3600)}h ago` : `${Math.round(s / 86400)}d ago`; };
const IconTick = () => <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8.5l3.2 3.2L13 5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>;
const IconCross = () => <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" /></svg>;
const IconDot = () => <svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="3" fill="currentColor" /></svg>;

// One sign-in window everywhere: the Vault's Signed-in sites and each proof folder's door.
// ⌨ Typing inside a cloud window is slow and paste often fails, so this box sends your words straight into whichever box you selected in the window. Never stored, never sent to a model.
export function TypeBar({ cat, work, d, op = 'signin_type', extra = null }) {
  const [text, setText] = useState(''); const [hide, setHide] = useState(false); const [busy, setBusy] = useState(''); const [note, setNote] = useState(''); const email = d?.mailbox?.address;
  const [mine, setMine] = useState(() => { try { return localStorage.getItem('feeless.my.email') || ''; } catch { return ''; } });
  const keepMine = v => { setMine(v); try { if (v) localStorage.setItem('feeless.my.email', v); else localStorage.removeItem('feeless.my.email'); } catch { /* private window */ } };
  const send = async (body, label = 'send') => { setBusy(label); setNote(''); try { await work(cat.id, { op, ...extra, ...body }); if (body.text) setNote('Sent into the selected box.'); return true; } catch (e) { setNote(e.message); return false; } finally { setBusy(''); } };
  const paste = async () => { try { const t = await navigator.clipboard.readText(); if (t) setText(t.trim()); else setNote('Nothing is copied.'); } catch { setNote('Your browser blocked it. Press ⌘V or Ctrl+V in this box.'); } };
  const code = async () => { setBusy('code'); setNote(''); try { const j = await work(cat.id, { op: 'mail_read' }); const c = (j.mail || []).find(m => m.code)?.code; if (c) await send({ text: String(c) }, 'code'); else setNote('No code in its mail yet. Wait a moment, then try again.'); } catch (e) { setNote(e.message); } finally { setBusy(''); } };
  return <form className="sd-type" onSubmit={async e => { e.preventDefault(); if (text && await send({ text })) setText(''); }} data-testid="sd-type">
    <small><b>1</b> Click a box in the window. <b>2</b> Type or paste here. <b>3</b> Send.</small>
    <div className="sd-type-row"><input className="m-input" type={hide ? 'password' : 'text'} value={text} onChange={e => setText(e.target.value)} placeholder="Type or paste here" autoComplete="off" spellCheck="false" aria-label="Words to send into the window" data-testid="sd-type-text" />
      <button type="button" className="m-btn" onClick={() => setHide(h => !h)} aria-pressed={hide} data-tip="Hide what you type, for a password">{hide ? 'Show' : 'Hide'}</button>
      <button type="button" className="m-btn" onClick={paste} data-tip="Paste what you copied" data-testid="sd-type-paste">Paste</button>
      <button type="submit" className="m-btn m-go" disabled={!text || !!busy} data-tip="Sends it into the box you selected in the window" data-testid="sd-type-send">{busy === 'send' ? 'Sending…' : 'Send'}</button></div>
    <div className="sd-type-row is-keys">{[['Tab', 'Next box'], ['Enter', 'Enter'], ['Backspace', '⌫ Delete']].map(([k, l]) => <button key={k} type="button" className="m-btn" disabled={!!busy} onClick={() => send({ job: k }, k)} data-tip={`Presses ${k} in the window`} data-testid={`sd-key-${k}`}>{l}</button>)}
      {email ? <button type="button" className="m-btn" disabled={!!busy} onClick={() => send({ text: email }, 'email')} data-tip={`Sends ${email} into the selected box`} data-testid="sd-type-email"><Ic3 e="📧" size="18px" /> Its email</button> : null}
      {email ? <button type="button" className="m-btn" disabled={!!busy} onClick={code} data-tip="Reads its mail and sends the newest code into the selected box" data-testid="sd-type-code"><Ic3 e="🔑" size="18px" /> {busy === 'code' ? 'Reading…' : 'Newest code'}</button> : null}
      {mine ? <button type="button" className="m-btn" disabled={!!busy} onClick={() => send({ text: mine }, 'mine')} data-tip={`Sends ${mine} into the selected box. Kept on this device only`} data-testid="sd-type-mine"><Ic3 e="✉️" size="18px" /> Your email</button> : null}
      {mine ? <button type="button" className="m-btn" onClick={() => keepMine('')} aria-label="Forget your email on this device" data-tip="Forget your email on this device" data-testid="sd-type-forget">✕</button> : null}
      {!mine && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text.trim()) ? <button type="button" className="m-btn" onClick={() => keepMine(text.trim())} data-tip="Keeps this address on this device for one-click use. Never on our server" data-testid="sd-type-keep">Keep as your email</button> : null}
      {note ? <small role="status" className="sd-type-note">{note}</small> : null}</div></form>;
}
export function SignInFrame({ live, cat, work, d }) {
  return <>{cat && work ? <TypeBar cat={cat} work={work} d={d} /> : null}<SignInView live={live} /></>;
}
export function SignInView({ live }) {
  return <iframe title={`Sign in to ${live.site}`} src={live.live} referrerPolicy="no-referrer" sandbox="allow-scripts allow-same-origin allow-forms allow-popups" allow="clipboard-read; clipboard-write" data-testid="cwb-signed-frame" />;
}

// 🛒 "buy $1 of $BONK on pump": the question on a card, the same door as typing yes or no.
export function SiteTradeCard({ cat, d, setD, work }) {
  const c = d?.siteTrade; const [busy, setBusy] = useState(false); const [msg, setMsg] = useState('');
  if (!c) return null;
  const go = async job => { setBusy(true); setMsg(''); try { const j = await work(cat.id, { op: 'site_trade', job }); setD?.(x => ({ ...x, ...j })); } catch (e) { setMsg(e.message); } finally { setBusy(false); } };
  return <section className="tpc stc m-glass" aria-label={`Order on ${c.site}`} data-testid="site-trade-card"><header><Ic3 e="🛒" size="26px" /><span><b>{c.side === 'buy' ? `Buy $${Number(c.usd).toFixed(2)} of $${c.sym}` : `Sell ${c.pct}% of $${c.sym}`} on {c.site}</b><small>From its account there. Its window presses the site's own button once.</small></span></header>
    {c.side === 'buy' ? <p className="stc-facts m-num"><span>Pool ${Number(c.pool).toLocaleString()}</span><span>{Math.round((c.ageS || 0) / 3600)} h old</span><span>{Number(c.run1h || 0).toFixed(0)}% in 1 h</span></p> : null}
    <div className="tpc-row"><button type="button" className="m-btn m-go" disabled={busy} onClick={() => go('yes')} data-tip="Starts its window on this one order" data-testid="site-trade-yes">{busy ? 'Starting…' : 'Yes, place it'}</button><button type="button" className="m-btn" disabled={busy} onClick={() => go('no')} data-testid="site-trade-no">No</button></div>
    {msg ? <small className="kd-err" role="alert">⚠ {msg}</small> : null}</section>;
}
const TRADE_STATE = { confirmed: ['CONFIRMED', 'The chain shows the balance moved'], checking: ['CHECKING', 'Reading the chain'], unverified: ['UNVERIFIED', 'Its window says so. Its wallet on this site is not known yet, so the chain was not checked'], failed: ['NOT DONE', 'The chain shows no change'] };
function SiteTrades({ cat, d, setD, work, m, signed }) {
  const rows = (d?.siteTrades || []).filter(r => r.site === m.site).slice(0, 5); const auto = !!d?.siteTradeAuto; const [err, setErr] = useState('');
  if (!signed) return null;
  const flip = async on => { setErr(''); try { const j = await work(cat.id, { op: 'site_trade_auto', on }); setD?.(x => ({ ...x, ...j })); } catch (e) { setErr(e.message); } };
  return <section className="sd-trades m-glass" data-testid="sd-trades"><header><Ic3 e="🛒" size="26px" /><span><b>It can trade on its {m.site} account</b><small>Say <code>buy $1 of $BONK on {m.slug}</code> or <code>sell all $BONK on {m.slug}</code>. Buys: $0.50 to $25, pool, age and already-ran guards, $50 a day.</small></span>
    <div className="m-seg" role="radiogroup" aria-label="When it may place an order"><button type="button" role="radio" aria-checked={!auto} className={auto ? '' : 'active'} onClick={() => flip(false)} data-tip="It asks yes or no on every order" data-testid="sd-trade-ask">Asks first</button><button type="button" role="radio" aria-checked={auto} className={auto ? 'active' : ''} onClick={() => flip(true)} data-tip="Your typed orders run with no question. Every guard and cap stays" data-testid="sd-trade-auto">No question</button></div></header>
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}
    {rows.length ? <ul>{rows.map(r => <li key={r.id}><b>{r.side === 'buy' ? `Buy $${Number(r.usd).toFixed(2)}` : `Sell ${r.pct}%`} ${r.sym}</b><small>{r.said}</small><em className={`is-${r.state}`} data-tip={TRADE_STATE[r.state]?.[1]}>{TRADE_STATE[r.state]?.[0]}</em></li>)}</ul> : null}</section>;
}

function Rule({ r, i, tone }) {
  return <li className={`sd-rule is-${tone}`} style={{ '--i': i }} data-tip={r.q}>
    <i aria-hidden="true">{tone === 'do' ? <IconTick /> : tone === 'dont' ? <IconCross /> : <IconDot />}</i>
    <span>{r.t}</span>
    <a className="sd-src" href={safeHref(r.src)} target="_blank" rel="noopener noreferrer" data-tip={`Read it on ${r.page}: ${r.src}`}>{r.page}</a></li>;
}

function Withdraw({ rows, ordered }) {
  if (!ordered) return <ul className="sd-rules" data-testid="sd-withdraw">{rows.map((r, i) => <Rule key={r.q} r={r} i={i} tone="info" />)}</ul>;
  return <ol className="sd-steps" data-testid="sd-withdraw"><b aria-hidden="true" className="sd-steps-pulse" />{rows.map((r, i) => <li key={r.q} style={{ '--i': i }} data-tip={r.q}>
    <em className="m-num">{i + 1}</em><span>{r.t}</span><a className="sd-src" href={safeHref(r.src)} target="_blank" rel="noopener noreferrer" data-tip={r.src}>{r.page}</a></li>)}</ol>;
}

function Manual({ m, cat, kind, signed, busy, onScan, onOpen, onDrop, onClose, onFile, onTopup, topups, said }) {
  const first = m.state === 'unread' ? 'pages' : m.dont?.length ? 'dont' : 'do';
  const [tab, setTab] = useState(first);
  const [label, stateTip] = STATE[m.state] || STATE.unread;
  const [botLabel, botV] = BOTS[m.botSay] || BOTS.silent;
  const rows = tab === 'pages' ? [] : m[tab] || [];
  const read = (m.pages || []).filter(p => p.ok);
  const meters = [
    ['PAGES READ', `${read.length}/${(m.pages || []).length}`, (m.pages || []).length ? read.length / m.pages.length : 0, 'Pages the scan got through out of those it tried'],
    ['RULES FOUND', `${(m.do?.length || 0) + (m.dont?.length || 0)}`, Math.min(1, ((m.do?.length || 0) + (m.dont?.length || 0)) / 12), "Do and don't lines from its own pages"],
    ['MONEY OUT', m.withdraw?.length ? 'STATED' : 'NOT FOUND', m.withdraw?.length ? 1 : 0.06, 'Whether its pages say how a withdrawal works'],
    ['AUTOMATION', botLabel, botV, 'What its own pages say about bots'],
  ];
  const cmd = `file a ${m.slug} ${WORD[kind].toLowerCase()}`;
  return <article className={`sd-manual is-${m.state}`} data-testid={`sd-manual-${m.site}`}>
    <header className="sd-mhead">
      <span className="sd-mtitle"><b>{m.site}</b><small>{agoOf(m.at)} · {m.model ? `worded by ${m.model}` : 'its own words'}{m.cost ? ` · $${Number(m.cost).toFixed(4)}` : ''}</small></span>
      <em className={`sd-state is-${m.state}`} data-tip={stateTip} data-testid="sd-state">{label}</em>
      <span className="sd-macts">
        <button type="button" className="m-btn" disabled={!!busy} onClick={() => onScan(m.url)} data-tip="Read its pages again" data-testid="sd-rescan">↻ Rescan</button>
        <button type="button" className="m-btn" onClick={() => onDrop(m.site)} data-tip="Delete this manual. A saved sign-in stays" data-testid="sd-drop">Delete</button>
        <button type="button" className="m-btn" onClick={onClose} aria-label="Close the manual" data-tip="Back to the sites" data-testid="sd-close">✕</button></span></header>
    {m.state === 'unread' ? <p className="sd-wall" role="status" data-testid="sd-wall"><b>{m.wall || 'No page answered.'}</b><span>Open it, clear the check by hand and save. Its next scan reads it with your sign-in.</span>
      <button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => onOpen(m.url)} data-tip="Opens it in a live window. Only you click there" data-testid="sd-wall-open">Open + sign in</button></p> : null}
    <div className="sd-mtop">
      <figure className={`sd-snap${m.shot ? '' : ' is-none'}`}>{m.shot ? <img src={apiUrl(`/api/cats/${cat.id}/sitesnap/${m.shot}?${agentAuthQuery()}`)} alt={`${m.site} when it was scanned`} loading="lazy" onError={e => { e.currentTarget.hidden = true; }} data-testid="sd-shot" /> : <figcaption>{m.browserWhy ? `No snapshot: ${m.browserWhy}` : 'No snapshot'}</figcaption>}<i className="sd-sweep" aria-hidden="true" /></figure>
      <div className="sd-meters">{meters.map(([k, v, f, tip], i) => <span key={k} className="sd-meter" style={{ '--i': i, '--v': f }} data-tip={tip}><em>{k}</em><b className="m-num">{v}</b><u aria-hidden="true"><i /></u></span>)}</div></div>
    <div className="m-seg sd-tabs" role="tablist" aria-label={`${m.site} manual`}>{TABS.map(([k, l]) => { const n = k === 'pages' ? (m.pages || []).length : (m[k] || []).length;
      return <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-tip={`${n} from its pages`} data-testid={`sd-tab-${k}`}>{l}{n ? <small className="m-num">{n}</small> : null}</button>; })}</div>
    <div key={tab} className="sd-pane" role="tabpanel">
      {tab === 'pages' ? <ul className="sd-pages" data-testid="sd-pages">{(m.pages || []).map((p, i) => <li key={`${p.url}${i}`} className={p.ok ? 'is-ok' : 'is-no'} style={{ '--i': i }}><i aria-hidden="true">{p.ok ? <IconTick /> : <IconCross />}</i><b>{p.kind}</b><a href={safeHref(p.url)} target="_blank" rel="noopener noreferrer" data-tip={p.url}>{p.title || p.url}</a><small className="m-num">{p.ok ? `${Math.round(p.chars / 1000)}K · ${p.via}` : 'not read'}</small></li>)}</ul>
        : !rows.length ? <p className="sd-empty">{EMPTY[tab]}</p>
          : tab === 'withdraw' ? <Withdraw rows={rows} ordered={!!m.model} />
            : <ul className="sd-rules" data-testid={`sd-rows-${tab}`}>{rows.map((r, i) => <Rule key={r.q} r={r} i={i} tone={tab === 'do' ? 'do' : tab === 'dont' || tab === 'bots' ? 'dont' : 'info'} />)}</ul>}
    </div>
    {m.state !== 'unread' ? <p className="sd-tip" data-testid="sd-fund-tip"><Ic3 e="💡" size="18px" /><span><b>Funding {m.site}:</b> it is easier and cheaper to fund your account there yourself. Its agents read it signed in and buy through FEELESS from their own wallet.</span></p> : null}
    <Loaded rows={topups} site={m.site} />
    <footer className="sd-cmd" data-testid="sd-cmd">{m.state === 'unread' ? null : signed
      ? <button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => onFile(cmd)} data-tip={`Its windows go to ${m.site} first, signed in, and only read there`} data-testid="sd-file">“{cmd}”</button>
      : <><button type="button" className="m-btn" disabled={!!busy} onClick={() => onOpen(m.url)} data-tip="Sign in by hand to unlock its command" data-testid="sd-unlock">Sign in to unlock</button><code>{cmd}</code></>}
      {said ? <small role="status">{said}</small> : <small>From its own pages, not legal advice.</small>}
      {m.state !== 'unread' && signed ? <button type="button" className="m-btn" disabled={!!busy} onClick={onTopup} data-tip={`Asks first: finds your ${m.site} deposit address, then you say yes, no or an amount`} data-testid="sd-topup">Top up…</button> : null}</footer>
  </article>;
}

// 💸 "Top up your pump account?" Yes, no, or an amount. A send happens only from this card or your typed yes, and the chain's balance shows what landed.
export function TopupCard({ cat, d, setD, work }) {
  const c = d?.topup; const [usd, setUsd] = useState(''); const [four, setFour] = useState(''); const [addr, setAddr] = useState(''); const [busy, setBusy] = useState(false); const [msg, setMsg] = useState('');
  useEffect(() => { setUsd(c?.usd ? String(c.usd) : ''); setFour(''); setMsg(''); }, [c?.id, c?.usd]);
  if (!c) return null;
  const merge = j => setD?.(x => ({ ...x, topup: j.topup, topups: j.topups ?? x?.topups }));
  const go = async body => { setBusy(true); setMsg(''); try { merge(await work(cat.id, { op: 'topup', ...body })); } catch (e) { setMsg(e.message); } finally { setBusy(false); } };
  const needFour = c.source === 'read' && c.address; const ready = c.address && Number(usd) > 0 && (!needFour || four.trim().length === 4);
  return <section className="tpc m-glass" aria-label={`Top up ${c.site}`} data-testid="topup-card"><header><Ic3 e="💸" size="26px" /><span><b>Top up your {c.site} account</b><small>{c.address ? 'From its own wallet, one transfer in SOL. Only on your yes.' : c.state === 'reading' ? 'Its window is looking for your deposit address.' : 'Paste your deposit address from the site.'}</small></span></header>
    <p className="sd-tip" data-testid="topup-tip"><Ic3 e="💡" size="18px" /><span><b>Easier and cheaper:</b> fund your {c.site} wallet yourself from your own wallet. An agent send adds a second transfer and a second network fee.</span></p>
    {c.state === 'reading' ? <p className="sd-scanning" role="status" data-testid="topup-reading"><i aria-hidden="true" /><span>Reading <b>{c.site}</b>…</span></p> : null}
    {c.address ? <code className="tpc-addr m-num" data-testid="topup-address" data-tip={c.source === 'read' ? 'It read this from the page. Compare it on the site before you answer' : 'The address you gave it'}>{c.address}</code>
      : c.state !== 'reading' ? <form className="tpc-row" onSubmit={e => { e.preventDefault(); if (addr.trim()) go({ job: 'address', text: addr.trim() }); }}><input className="m-input" value={addr} onChange={e => setAddr(e.target.value)} placeholder="Its Solana deposit address" aria-label="Deposit address" spellCheck="false" data-testid="topup-paste" /><button type="submit" className="m-btn" disabled={!addr.trim() || busy} data-testid="topup-paste-go">Use it</button></form> : null}
    {c.address ? <div className="tpc-row"><label className="tpc-usd"><span aria-hidden="true">$</span><input className="m-input" inputMode="decimal" value={usd} onChange={e => setUsd(e.target.value.replace(/[^0-9.]/g, ''))} placeholder="1.50" aria-label="Dollars to send" data-tip="$0.50 to $25 a send" data-testid="topup-usd" /></label>
      {needFour ? <input className="m-input tpc-four m-num" value={four} maxLength={4} onChange={e => setFour(e.target.value)} placeholder="Last 4" aria-label="Last 4 characters of the address" data-tip="A page could show the wrong address. Type its last 4 after checking it on the site" data-testid="topup-four" /> : null}
      <button type="button" className="m-btn m-go" disabled={!ready || busy} onClick={() => go({ job: 'yes', cap: Number(usd), text: four.trim() })} data-tip="Its wallet signs one transfer to this address" data-testid="topup-yes">{busy ? 'Sending…' : `Yes, send${Number(usd) > 0 ? ` $${Number(usd).toFixed(2)}` : ''}`}</button>
      <button type="button" className="m-btn" disabled={busy} onClick={() => go({ job: 'no' })} data-testid="topup-no">No</button></div> : <div className="tpc-row"><button type="button" className="m-btn" disabled={busy} onClick={() => go({ job: 'no' })} data-testid="topup-no">Cancel</button></div>}
    {msg ? <small className="kd-err" role="alert">⚠ {msg}</small> : null}</section>;
}
// 📧 Its own mailbox: make it once, read its mail as plain text, copy a code.
export function MailApp({ cat, d, setD, work }) {
  const box = d?.mailbox; const [rows, setRows] = useState(null); const [busy, setBusy] = useState(''); const [err, setErr] = useState(''); const [open, setOpen] = useState(null);
  const read = useCallback(async () => { setBusy('read'); setErr(''); try { setRows((await work(cat.id, { op: 'mail_read' })).mail || []); } catch (e) { setErr(e.message); } finally { setBusy(''); } }, [cat.id, work]);
  useEffect(() => { if (!box?.address) return undefined; read(); const t = setInterval(() => { if (!document.hidden) read(); }, 30000); return () => clearInterval(t); }, [box?.address, read]);
  const make = async () => { setBusy('make'); setErr(''); try { const j = await work(cat.id, { op: 'mail_make' }); setD?.(x => ({ ...x, mailbox: j.mailbox, logins: j.logins ?? x?.logins })); } catch (e) { setErr(e.message); } finally { setBusy(''); } };
  const m = rows?.find(x => x.id === open);
  return <div className="mbx" data-testid="dsk-mail">
    {box?.address ? <header className="mbx-top m-glass"><Ic3 e="📧" size="30px" /><span><b data-testid="mail-address">{box.address}</b><small>Its password is sealed in the Vault. Some sites refuse free mailboxes.</small></span><button type="button" className="m-btn" disabled={!!busy} onClick={read} data-tip="Read its mail now" data-testid="mail-refresh">{busy === 'read' ? 'Reading…' : '↻'}</button></header>
      : <header className="mbx-top m-glass"><Ic3 e="📧" size="30px" /><span><b>Give it its own email</b><small>A free mail.tm mailbox, no CAPTCHA, so it can sign up and read its own codes.</small></span><button type="button" className="m-btn m-go" disabled={!!busy} onClick={make} data-tip="Makes one mailbox on mail.tm and seals its password" data-testid="mail-make">{busy === 'make' ? 'Making…' : 'Make its email'}</button></header>}
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}
    {m ? <article className="mbx-open" data-testid="mail-open"><button type="button" className="m-btn" onClick={() => setOpen(null)} aria-label="Back to its inbox" data-tip="Back">↑</button><b>{m.subject || '(no subject)'}</b><small>{m.from}</small>{m.code ? <code className="m-num" data-testid="mail-code">{m.code}</code> : null}<p>{m.text}</p></article>
      : box?.address ? (rows && !rows.length ? <p className="dsk-note">Its inbox is empty.</p> : <ul className="mbx-list">{(rows || []).map((x, i) => <li key={x.id} style={{ '--i': i }}><button type="button" onClick={() => setOpen(x.id)} data-tip="Read it" data-testid={`mail-${x.id}`}><b>{x.subject || '(no subject)'}</b><small>{x.from}</small>{x.code ? <code className="m-num">{x.code}</code> : null}</button></li>)}</ul>) : null}
  </div>;
}
// What landed: its balance on the chain before and after each send.
function Loaded({ rows, site }) {
  const r = (rows || []).filter(x => x.site === site); if (!r.length) return null; const last = r[0];
  return <div className="tpc-loaded" data-testid="topup-loaded"><span><em>LOADED ON {site.toUpperCase()}</em><b className="m-num" key={last.after}>{last.after > 0 ? `${last.after} SOL` : last.after === -1 ? 'Not read' : 'Reading…'}</b><small className="m-num">{last.before != null ? `was ${last.before} SOL · ` : ''}sent ${Number(last.usd).toFixed(2)} {agoOf(last.at)}. On-chain balance of its deposit address, not the site's own figure.</small></span>
    <a className="m-btn" href={`https://solscan.io/tx/${encodeURIComponent(last.sig)}`} target="_blank" rel="noopener noreferrer" data-tip="See the transfer on-chain">tx ↗</a></div>;
}

export function SiteDoor({ kind, cat, d, setD, work }) {
  const [text, setText] = useState(''); const [live, setLive] = useState(null); const [busy, setBusy] = useState(''); const [err, setErr] = useState(''); const [open, setOpen] = useState(''); const [said, setSaid] = useState('');
  const scanning = d?.siteScan; const signed = new Set((d?.signedIn || []).map(r => r.site));
  const rows = Object.values(d?.siteManuals || {}).filter(m => (m.kinds || []).includes(kind)).sort((a, b) => (b.at || 0) - (a.at || 0));
  const manual = rows.find(m => m.site === open);
  const merge = useCallback(j => setD?.(x => ({ ...x, siteManuals: j.siteManuals ?? x?.siteManuals, siteScan: j.siteScan, signedIn: j.signedIn ?? x?.signedIn, commands: j.commands ?? x?.commands })), [setD]);
  useEffect(() => { if (!scanning) return undefined; const t = setInterval(() => { if (!document.hidden) work(cat.id, { op: 'state' }).then(merge).catch(() => {}); }, 3000); return () => clearInterval(t); }, [scanning, cat.id, work, merge]);
  const run = async (op, body, then) => { setBusy(op); setErr('');
    try { const j = await work(cat.id, { op, ...body }); then?.(j); return j; } catch (e) { setErr(e.message); return null; } finally { setBusy(''); } };
  const scan = async u => { const j = await run('site_scan', { text: u, job: kind }); if (j) { setD?.(x => ({ ...x, siteScan: j.siteScan })); setOpen(j.siteScan); setText(''); } };
  const openSite = u => run('signin_open', { text: u }, j => setLive({ ...j, url: u, at: Date.now() }));
  const save = async () => { const j = await run('signin_save', {}); if (!j) return; merge(j); const u = live?.url; setLive(null); if (u) scan(u); };
  const drop = site => run('site_drop', { text: site }, j => { merge(j); setOpen(''); });
  const file = c => run('site_file', { text: c }, j => setSaid(j.say));
  const go = text.trim();
  return <section className="sd m-glass" aria-label={`Sites for its ${WORD[kind]}`} data-testid={`site-door-${kind}`}>
    <form className="sd-bar" onSubmit={e => { e.preventDefault(); if (go && !scanning) scan(go); }}>
      <svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.2" fill="none" stroke="currentColor" strokeWidth="1.4" /><path d="M2 8h12M8 1.8c2 2 2.6 4 2.6 6.2S10 12.2 8 14.2C6 12.2 5.4 10.2 5.4 8S6 3.8 8 1.8z" fill="none" stroke="currentColor" strokeWidth="1.1" /></svg>
      <input className="m-input" value={text} onChange={e => setText(e.target.value)} placeholder={`Its ${WORD[kind]} site, e.g. ${HINT[kind]}`} aria-label={`Site for its ${WORD[kind]}`} autoCapitalize="none" autoCorrect="off" spellCheck="false" data-tip="Any public site. You sign in yourself, and it never sees your password" data-testid={`sd-input-${kind}`} />
      <button type="button" className="m-btn" disabled={!go || !!busy} onClick={() => openSite(go)} data-tip="Opens it in a live window. Only you click there, and Save keeps the sign-in sealed for its windows" data-testid={`sd-open-${kind}`}>{busy === 'signin_open' ? 'Opening…' : 'Open + sign in'}</button>
      <button type="submit" className="m-btn m-go" disabled={!go || !!busy || !!scanning} data-tip="Reads its terms, fees and help pages and files a manual" data-testid={`sd-scan-${kind}`}>{busy === 'site_scan' ? 'Starting…' : 'Scan'}</button></form>
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}
    <TopupCard cat={cat} d={d} setD={setD} work={work} />
    {scanning ? <p className="sd-scanning" role="status" data-testid="sd-scanning"><i aria-hidden="true" /><span>Reading <b>{scanning}</b>: terms, fees, help, snapshot…</span></p> : null}
    {live ? <div className="cwb-signed-live sd-live" data-testid="sd-live"><span><em>LIVE · sign in to {live.site} yourself</em>
      <button type="button" className="m-btn" disabled={!!busy} onClick={() => setLive(null)} data-tip="Close without saving">Cancel</button>
      <button type="button" className="m-btn m-go" disabled={!!busy} onClick={save} data-tip="Keeps this sign-in sealed for its windows, then scans the site" data-testid="sd-save">{busy === 'signin_save' ? 'Saving…' : '✓ Signed in, save + scan'}</button></span><SignInFrame live={live} cat={cat} work={work} d={d} /></div> : null}
    {manual ? <SiteTrades cat={cat} d={d} setD={setD} work={work} m={manual} signed={signed.has(manual.site)} /> : null}
    {manual ? <Manual key={`${manual.site}${manual.at}`} m={manual} cat={cat} kind={kind} signed={signed.has(manual.site)} busy={busy || scanning} onScan={scan} onOpen={openSite} onDrop={drop} onClose={() => { setOpen(''); setSaid(''); }} onFile={file} onTopup={() => run('ask', { text: `top up ${manual.slug}` }, () => work(cat.id, { op: 'state' }).then(j => setD?.(x => ({ ...x, topup: j.topup, chat: j.chat ?? x?.chat }))))} topups={d?.topups} said={said} />
      : rows.length ? <ul className="sd-sites" data-testid={`sd-sites-${kind}`}>{rows.map((m, i) => <li key={m.site} style={{ '--i': i }}><button type="button" onClick={() => setOpen(m.site)} data-tip={`Open the ${m.site} manual: ${(STATE[m.state] || STATE.unread)[1]}`} data-testid={`sd-site-${m.site}`}><i className={`sd-dot is-${m.state}`} aria-hidden="true" /><b>{m.site}</b><small>{(STATE[m.state] || STATE.unread)[0]}{signed.has(m.site) ? ' · SIGNED IN' : ''}</small></button></li>)}</ul> : null}
  </section>;
}

// 👁 WATCH A WALLET's folders (owner 2026-11-04): each address its browser reported, the lines about it, and one check on the chain. A model can name an address that was never a trader.
const short = a => `${a.slice(0, 5)}…${a.slice(-5)}`;
function ChainTag({ w, checked }) {
  if (!checked) return <em className="wf-tag">CHECKING…</em>;
  if (w.txs == null) return <em className="wf-tag is-warn" data-tip="The chain check did not answer. Open it on Solscan">NOT CHECKED</em>;
  if (!w.txs) return <em className="wf-tag is-bad" data-tip="This address has no history on the chain. The model may have misread it">NO HISTORY</em>;
  return <em className="wf-tag is-good" data-tip={`${w.txs}${w.txs >= 20 ? '+' : ''} recent transactions on the chain`}>ON CHAIN {w.txs}{w.txs >= 20 ? '+' : ''}{w.lastAt ? ` · ${agoOf(w.lastAt)}` : ''}</em>;
}
export function WatchFolders({ rows = [] }) {
  const [open, setOpen] = useState(''); const f = rows.find(x => x.id === open);
  if (!rows.length) return null;
  return <section className="wf m-glass" aria-label="Wallet watches" data-testid="watch-folders"><header className="wf-head"><b>👁 WALLET WATCHES</b><small className="m-num">{rows.length}</small>{f ? <button type="button" className="m-btn" onClick={() => setOpen('')} aria-label="Up one folder" data-tip="Up one folder">↑</button> : null}</header>
    {!f ? <ul className="sd-sites">{rows.map((x, i) => <li key={x.id} style={{ '--i': i }}><button type="button" onClick={() => setOpen(x.id)} data-tip={`Open Watch #${x.n}`} data-testid={`watch-${x.id}`}><i className={`sd-dot is-${x.wallets?.length ? 'read' : 'unread'}`} aria-hidden="true" /><b>Watch #{x.n}</b><small>{x.wallets?.length || 0} WALLETS · {agoOf(x.at)}</small></button></li>)}</ul>
      : <div className="wf-body sd-manual" data-testid="watch-folder">
        {f.sites?.length ? <p className="wf-sites">Opened {f.sites.join(' · ')}{f.cost ? ` · $${Number(f.cost).toFixed(4)}` : ''}</p> : <p className="wf-sites">It opened no site{f.why ? `: ${f.why}` : ''}.</p>}
        {f.wallets?.length ? <ul className="wf-rows">{f.wallets.map((w, i) => <li key={w.address} style={{ '--i': i }} className="sd-rule is-info"><div className="wf-row"><span className="wf-addr"><a className="m-num" href={`https://solscan.io/account/${encodeURIComponent(w.address)}`} target="_blank" rel="noopener noreferrer" data-tip={`Open ${w.address} on Solscan`}>{short(w.address)} ↗</a><ChainTag w={w} checked={f.checked} /></span>{(w.lines || []).map((l, k) => <small key={`${k}${l}`}>{l}</small>)}</div></li>)}</ul>
          : <p className="sd-empty">No wallet address came back, so nothing was filed as a result.{f.answer ? ` It said: ${f.answer.slice(0, 200)}` : ''}</p>}</div>}
  </section>;
}
