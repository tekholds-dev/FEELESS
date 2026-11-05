import React, { useEffect, useState } from 'react';
import '../../styles/setupDeck.css';
import { Ic3 } from '../../lib/icon3d';
import { PEOPLE, thumbOf } from '../../lib/wireface';
import { RecoveryKit } from './RecoveryKit';
import '../../styles/character.css';

// 🚀 PRIORITY SETUP (owner 2026-11-04): a new agent starts with its asks, one slide each. The desktop stays lit with how many are left. Its answers live on the server (agent_setup.py):
// a step is done by the real thing (a mailbox, a signed colony share) or by the owner saying later. Nothing here moves money.
const USES = [['trade', '📈', 'Trade coins', 'Research, buy and hold on its own wallet or your site account'], ['bids', '🎲', 'Bids + predictions', 'Sports and markets, researched with snapshots'], ['content', '🎨', 'Make content', 'The only job allowed to post'], ['research', '🔎', 'Research', 'Reads the web and reports back'], ['all', '🧬', 'All of it', 'Every folder, every first step']];
const SHARES = [0, 5, 10, 15, 20, 25];
// Where a person does the part only a person can do. Found in searches on 2026-11-04, none of them connected to FEELESS yet: these are links, nothing runs through them.
const SOURCES = {
  trade: [['Instant buy with a card', [['MoonPay', 'https://www.moonpay.com/'], ['Onramper', 'https://www.onramper.com/'], ['Coinbase', 'https://www.coinbase.com/']], 'They check your ID once. Send it to the site or its wallet after.']],
  bids: [['Instant buy with a card', [['MoonPay', 'https://www.moonpay.com/'], ['Onramper', 'https://www.onramper.com/']], 'They check your ID once. Fund the site yourself, it is cheaper.']],
  content: [['Open to bots, free', [['Bluesky', 'https://bsky.app/'], ['Mastodon', 'https://joinmastodon.org/']], 'Both welcome accounts run by software through their open APIs.'], ['Posting services for X, LinkedIn and more', [['Postiz', 'https://postiz.com/'], ['Blotato', 'https://www.blotato.com/'], ['Zernio', 'https://zernio.com/'], ['Ayrshare', 'https://www.ayrshare.com/']], 'They post through each network’s official API. Paid plans: check each price.']],
  research: [['Open data', [['CoinGecko', 'https://www.coingecko.com/'], ['DexScreener', 'https://dexscreener.com/']], 'Readable without a sign-in.']],
};
SOURCES.all = [SOURCES.trade[0], SOURCES.content[0]];
export const TERMS = [
  ['Your agent, your call', 'You own this agent and answer for what you ask it to do. Use it only where that is legal for you.'],
  ['Real money can be lost', 'Coins, bids and trades can go to zero. Nothing an agent says is financial advice, and past proofs do not promise future results.'],
  ['Paper is paper', 'A PoP and a topic PoB stake nothing. Their results are research, not earnings.'],
  ['Other sites have their own rules', 'You agree to each site’s terms when you sign in. Some ban software. The scan’s manual shows what it found, and an account a site closes is on you to resolve.'],
  ['Checks stay human', 'A CAPTCHA, phone code or ID check is always yours. FEELESS never tries to pass one.'],
  ['It posts only if you say', 'Only an agent with the content job can post or reply. You answer for what it publishes.'],
  ['Collective share is your choice', 'It is off until you sign it, from 5% to 25% of each winning trade’s profit. You can turn it off at any time.'],
  ['Your character', 'Use only a picture you have the right to use and never pass yourself off as someone else. A stream follows the rules of the channel it goes to, and what you say on it is yours.'],
  ['Keys and sign-ins', 'They are sealed for this agent, and only your wallet controls it. Lose your wallet and your recovery PIN, and nobody can open them for you.'],
];
export const securityFacts = (cat, d) => [
  ['🔐', 'Sealed per agent', `${(d?.logins || []).length + (d?.signedIn || []).length} logins and sign-ins`, 'Encrypted with a key only this agent’s seal can open. The master key lives outside the data, so a copied database opens nothing.'],
  ['👛', 'Your wallet only', 'Signature on every door', 'Every control asks for your wallet’s signed session from the last 24 h. Revealing a password asks for a new signature each time.'],
  ['🙈', 'It never sees a password', 'Placeholders only', 'Its models type a placeholder. The real password is filled in by FEELESS, never shown to a model or a page.'],
  ['🔒', 'Secure sites only', 'HTTPS, public addresses', 'Plain http, private networks and addresses with a login in them are refused on every page it opens.'],
  ['🕶', 'Visitors see no accounts', 'Signed-in pages hidden', 'A window on a site you signed in to never shows on its public monitors, and those snapshots are yours alone, sealed on disk.'],
  ['📣', 'It answers you', 'Posts only on content', 'Only you can give it work. Only the content job may post or reply. Web pages are data, never orders.'],
];

function Slide({ art, kicker, title, sub, children }) {
  return <div className="stp-slide"><div className="stp-art" aria-hidden="true"><Ic3 e={art} size="100%" /></div>
    <div className="stp-body"><em className="stp-kick">{kicker}</em><h3>{title}</h3>{sub ? <span className="stp-sub">{sub}</span> : null}{children}</div></div>;
}

export function SetupDeck({ cat, d, setD, work, onOpen, kit }) {
  const s = d?.setup; const steps = s?.steps || []; const first = steps.findIndex(x => !x.done);
  const [at, setAt] = useState(first < 0 ? 0 : first); const [busy, setBusy] = useState(''); const [err, setErr] = useState(''); const [pick, setPick] = useState(null); const [pct, setPct] = useState(10); const [copied, setCopied] = useState(false);
  const [share, , signShare, canSign] = kit?.useShare ? kit.useShare(cat) : [{}, null, null, false];
  useEffect(() => { if (at >= steps.length && steps.length) setAt(steps.length - 1); }, [at, steps.length]);
  if (!s) return null;
  const step = steps[at]; const k = step?.k;
  const run = async (key, fn, thenNext = true) => { setBusy(key); setErr(''); try { await fn(); if (thenNext) setAt(n => Math.min(n + 1, steps.length - 1)); } catch (e) { setErr(e.message || 'That did not go through.'); } finally { setBusy(''); } };
  const answer = async (job, text) => { const j = await work(cat.id, { op: 'setup', job, text }); setD?.(x => ({ ...x, setup: j.setup })); return j; };
  const done = () => run('done', () => answer('done', k));
  const later = <button type="button" className="m-btn" disabled={!!busy} onClick={done} data-tip="Marks this done. You can do it from its folder any time" data-testid="stp-later">Later</button>;
  const address = cat?.agentWallet?.address || d?.address;
  const copy = async t => { try { await navigator.clipboard.writeText(t); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* the address stays on screen */ } };
  let slide = null;
  if (k === 'use') slide = <Slide art="🧭" kicker="FIRST THINGS" title="What will this agent be used for?" sub="This decides what you set up next.">
    <div className="stp-cards">{USES.map(([v, ic, t, x], i) => <button key={v} type="button" className={`stp-card${s.use === v ? ' is-on' : ''}`} style={{ '--i': i }} disabled={!!busy} aria-pressed={s.use === v} onClick={() => run('use', () => answer('use', v))} data-testid={`stp-use-${v}`}><Ic3 e={ic} size="46px" /><b>{t}</b><small>{x}</small></button>)}</div></Slide>;
  if (k === 'face') slide = <Slide art="🎭" kicker="WHO IT IS" title="Pick its character" sub="Free: real people, anime, cartoon and more. Camera, voice and going live are in its Character folder, and all off until you turn them on.">
    <div className="stp-faces">{PEOPLE.slice(0, 8).map(([id, n, st]) => <button key={id} type="button" className={`chr-tile${cat?.face?.id === id ? ' is-on' : ''}`} disabled={!!busy} onClick={() => run('face', async () => { await work(cat.id, { op: 'face', text: id }); await done(); })} data-tip={`${n}, ${st}`} data-testid={`stp-face-${id}`}><img src={thumbOf(id)} alt="" loading="lazy" /><em>{st}</em><b>{n}</b></button>)}</div>
    <div className="stp-row"><button type="button" className="m-btn" onClick={() => onOpen?.('character')} data-testid="stp-face-more">See all, or use your picture</button>{later}</div></Slide>;
  if (k === 'email') slide = <Slide art="📧" kicker="ITS OWN EMAIL" title={d?.mailbox?.address ? 'It has its own email' : 'Give it its own email'} sub="It signs up to sites with this and reads its own codes.">
    {d?.mailbox?.address ? <button type="button" className="stp-pill m-num" onClick={() => copy(d.mailbox.address)} data-tip="Copy it" data-testid="stp-email">{d.mailbox.address}{copied ? ' · copied' : ''}</button> : null}
    <div className="stp-row">{d?.mailbox?.address ? <button type="button" className="m-btn m-go" onClick={() => setAt(at + 1)} data-testid="stp-next-email">Next</button> : <button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => run('mail', async () => { const j = await work(cat.id, { op: 'mail_make' }); setD?.(x => ({ ...x, mailbox: j.mailbox, logins: j.logins ?? x?.logins })); const v = await work(cat.id, { op: 'setup' }); setD?.(x => ({ ...x, setup: v.setup })); })} data-testid="stp-make-email">{busy === 'mail' ? 'Making it…' : 'Make its email'}</button>}{d?.mailbox?.address ? null : later}</div></Slide>;
  if (k === 'sites') slide = <Slide art="🌐" kicker="QUICK SIGN-UPS" title="Sign in to what it needs" sub={s.sites.length ? 'Tap a site. You sign in by hand. It stays sealed for this agent.' : 'Pick what it is for first.'}>
    {pick ? <div className="stp-live">{kit?.renderSites?.(pick, () => { setPick(null); work(cat.id, { op: 'setup' }).then(j => setD?.(x => ({ ...x, setup: j.setup }))).catch(() => {}); })}<button type="button" className="m-btn" onClick={() => setPick(null)} data-testid="stp-sites-back">Back to the list</button></div>
      : <><div className="stp-cards is-sites">{s.sites.map(([site, why], i) => { const has = (d?.signedIn || []).some(x => x.site === site); return <button key={site} type="button" className={`stp-card${has ? ' is-on' : ''}`} style={{ '--i': i }} onClick={() => setPick(site)} data-testid={`stp-site-${site}`}><b>{site}</b><small>{why}</small><em className="m-num">{has ? 'Signed in' : 'Sign in'}</em></button>; })}</div>
        {(SOURCES[s.use] || []).map(([h, links, x]) => <details key={h} className="stp-more"><summary>{h}</summary><span className="stp-links">{links.map(([l, u]) => <a key={l} className="m-btn" href={u} target="_blank" rel="noopener noreferrer">{l}</a>)}</span><small>{x}</small></details>)}
        <div className="stp-row">{later}</div></>}</Slide>;
  if (k === 'fund') slide = <Slide art="👛" kicker="ITS MONEY" title="Fund it" sub="Its wallet pays for its buys and model calls. For a site like pump or stake.us, funding the site yourself is easier and cheaper.">
    {address ? <button type="button" className="stp-pill m-num" onClick={() => copy(address)} data-tip="Copy its wallet address" data-testid="stp-address">{address.slice(0, 8)}…{address.slice(-8)}{copied ? ' · copied' : ''}</button> : <small className="stp-hint">It has no wallet yet. Open Wallet to make one.</small>}
    <div className="stp-row">{onOpen ? <button type="button" className="m-btn m-go" onClick={() => onOpen('wallet')} data-testid="stp-open-wallet">Open Wallet</button> : null}{later}</div></Slide>;
  if (k === 'limits') slide = <Slide art="🎚" kicker="ITS LIMITS" title="The most one task may spend" sub="Hard exits always run. The full list is in Limits.">
    <div className="m-seg stp-seg" role="radiogroup" aria-label="The most a task may spend">{(kit?.caps || []).map(c => <button key={c} type="button" role="radio" aria-checked={Math.abs(Number(d?.cap) - c) < 1e-9} className={Math.abs(Number(d?.cap) - c) < 1e-9 ? 'active' : ''} disabled={!!busy} onClick={() => run('cap', async () => { const j = await work(cat.id, { op: 'cap', cap: c }); setD?.(x => ({ ...x, ...j })); }, false)} data-testid={`stp-cap-${c}`}>${c}</button>)}</div>
    <div className="stp-row"><button type="button" className="m-btn m-go" disabled={!!busy} onClick={done} data-testid="stp-limits-ok">That works</button></div></Slide>;
  if (k === 'colony') slide = <Slide art="💧" kicker="THE COLLECTIVE" title="Send part of its winnings to the Collective?" sub="Only from winning trades on its own wallet. The Collective airdrops back to the agents who share. Your wallet signs, with no transaction.">
    <div className="stp-dial" role="radiogroup" aria-label="Share of each win">{SHARES.map(p => <button key={p} type="button" role="radio" aria-checked={pct === p} className={pct === p ? 'is-on' : ''} onClick={() => setPct(p)} data-testid={`stp-share-${p}`}><b className="m-num">{p}%</b></button>)}</div>
    {share?.on ? <small className="stp-hint">It shares {share.pct}% now.</small> : null}
    <div className="stp-row"><button type="button" className="m-btn m-go" disabled={!!busy || (pct > 0 && !canSign)} onClick={() => run('share', async () => { if (pct > 0) await signShare(true, pct); else if (share?.on) await signShare(false); await answer('done', 'colony'); })} data-testid="stp-share-go">{pct > 0 ? `Sign ${pct}% of each win` : 'No share for now'}</button></div></Slide>;
  if (k === 'post') slide = <Slide art="📣" kicker="POSTING" title="May it post for you?" sub="Only an agent with the content job can post or reply. Every other job is refused.">
    <div className="stp-row"><button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => run('post', async () => { const j = await work(cat.id, { op: 'tools', job: 'content' }); setD?.(x => ({ ...x, ...j })); await answer('done', 'post'); })} data-testid="stp-post-yes">Yes, give it the content job</button><button type="button" className="m-btn" disabled={!!busy} onClick={done} data-testid="stp-post-no">No posting</button></div></Slide>;
  if (k === 'trades') slide = <Slide art="🛒" kicker="SITE TRADES" title="Should it ask before a site trade?" sub="When you say “buy $1 of $BONK on pump”. The caps and guards stay on either way.">
    <div className="stp-row"><button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => run('t', async () => { const j = await work(cat.id, { op: 'site_trade_auto', on: false }); setD?.(x => ({ ...x, ...j })); await answer('done', 'trades'); })} data-testid="stp-trade-ask">Ask me every time</button><button type="button" className="m-btn" disabled={!!busy} onClick={() => run('t', async () => { const j = await work(cat.id, { op: 'site_trade_auto', on: true }); setD?.(x => ({ ...x, ...j })); await answer('done', 'trades'); })} data-testid="stp-trade-auto">Run my typed orders with no question</button></div></Slide>;
  if (k === 'security') slide = <Slide art="🛡" kicker="ITS SECURITY" title="How it is locked down">
    <div className="stp-tiles">{securityFacts(cat, d).map(([ic, t, v, x], i) => <span key={t} className="stp-tile" style={{ '--i': i }} data-tip={x}><Ic3 e={ic} size="30px" /><b>{t}</b><small>{v}</small></span>)}</div>
    <div className="stp-row"><button type="button" className="m-btn m-go" disabled={!!busy} onClick={done} data-testid="stp-security-ok">Got it</button></div></Slide>;
  if (k === 'terms') slide = <Slide art="📃" kicker="THE TERMS" title="Agree to run this agent" sub="Always open in Terms & security on its desktop.">
    <div className="stp-terms">{TERMS.map(([t, x]) => <details key={t}><summary>{t}</summary><small>{x}</small></details>)}</div>
    <div className="stp-row">{s.termsAt ? <small className="stp-hint" data-testid="stp-terms-ok">Agreed {new Date(s.termsAt * 1000).toLocaleDateString()}</small> : <button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => run('terms', () => answer('terms', ''))} data-testid="stp-terms-go">I agree</button>}</div></Slide>;
  return <section className="stp" data-testid="am-setup">
    <header className="stp-top"><b>{s.left ? `${s.left} of ${s.total} left` : 'All set'}</b><ol aria-label="Setup steps">{steps.map((x, i) => <li key={x.k}><button type="button" className={`${x.done ? 'is-done' : ''}${i === at ? ' is-at' : ''}`} onClick={() => { setPick(null); setAt(i); }} aria-label={`Step ${i + 1}: ${x.k}${x.done ? ', done' : ''}`} aria-current={i === at ? 'step' : undefined} data-testid={`stp-dot-${x.k}`}><i aria-hidden="true" /></button></li>)}</ol></header>
    <div key={k} className="stp-stage">{slide}</div>
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}
    <nav className="stp-nav"><button type="button" className="m-btn" disabled={!at} onClick={() => { setPick(null); setAt(at - 1); }} data-testid="stp-back">← Back</button><button type="button" className="m-btn" disabled={at >= steps.length - 1} onClick={() => { setPick(null); setAt(at + 1); }} data-testid="stp-skip">Next →</button></nav>
  </section>;
}

// 🛡 Terms & security: always one click from its desktop.
export function TermsFolder({ cat, d, setD, work }) {
  const s = d?.setup; const [err, setErr] = useState('');
  const agree = async () => { setErr(''); try { const j = await work(cat.id, { op: 'setup', job: 'terms', text: '' }); setD?.(x => ({ ...x, setup: j.setup })); } catch (e) { setErr(e.message); } };
  return <div className="stp-folder" data-testid="dsk-terms">
    <section className="stp-secure"><h3><Ic3 e="🛡" size="26px" /> ITS SECURITY</h3><div className="stp-tiles is-big">{securityFacts(cat, d).map(([ic, t, v, x], i) => <details key={t} className="stp-tile" style={{ '--i': i }}><summary><Ic3 e={ic} size="40px" /><b>{t}</b><small>{v}</small></summary><span>{x}</span></details>)}</div></section>
    <RecoveryKit cat={cat} view={d?.recoveryView} />
    <section className="stp-terms-pane"><h3><Ic3 e="📃" size="26px" /> THE TERMS</h3><div className="stp-terms">{TERMS.map(([t, x]) => <details key={t}><summary>{t}</summary><small>{x}</small></details>)}</div>
      {s?.termsAt ? <small className="stp-hint" data-testid="terms-agreed">You agreed on {new Date(s.termsAt * 1000).toLocaleDateString()}.</small> : <button type="button" className="m-btn m-go" onClick={agree} data-testid="terms-agree">I agree</button>}
      {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</section></div>;
}
