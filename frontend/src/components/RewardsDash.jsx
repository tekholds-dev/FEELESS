import { useCountUp } from '../lib/useCountUp';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { Link } from 'react-router-dom';
import '../styles/rewardsDash.css';
import { apiUrl } from '../lib/api';
import { useWallet } from '../hooks/useWallet';
import { getChatSession } from '../lib/chatSession';
import { Ic3 } from '../lib/icon3d';
import { useQuests, Season, BadgeDetail } from './QuestBoard';
import { BadgeArt } from './BadgeArt';
import { ShaderWall } from './command/DeskShell';

// 🎁 THE REWARDS DASH (owner 2026-11-04): one stop for points, badges, the shop and the family bank. Every number and button is the server's own (rewards, quests, shop): nothing here is promised that the server does not do.
const REWARD_ICON = { daily: '📅', profile: '🎨', post: '💬', 'call-hit': '📣', invite: '🚀', 'fee-holder': '🪙', link: '🔗' };
const REWARD_GO = { profile: '/terminal/settings', post: '/terminal/chat', 'call-hit': '/terminal/chat', invite: '/terminal/settings', 'fee-holder': '/terminal/fee', link: '/terminal/settings' };
const METRIC_GO = [[/trade|swap|volume|buy|sell/i, '/terminal/trade'], [/call/i, '/terminal/chat'], [/post|chat|message/i, '/terminal/chat'], [/fuse|card/i, '/terminal/fuse'], [/launch/i, '/terminal/launch'], [/fee|hold/i, '/terminal/fee'], [/crew|family|familia/i, '/terminal/familia']];
const goFor = t => METRIC_GO.find(([re]) => re.test(`${t?.metric || ''} ${t?.label || ''}`))?.[1] || '/terminal';
const tierOrder = ['legendary', 'epic', 'rare', 'uncommon', 'common'];

const postJson = async (url, body) => {
  const r = await fetch(apiUrl(url), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || 'That did not go through.');
  return j;
};


function LevelRing({ level }) {
  const xp = Number(level?.xp || 0); const next = Number(level?.next || 0); const pct = next ? Math.min(1, xp / next) : 1; const C = 2 * Math.PI * 46;
  return <div className="rwd-ring" data-tip={next ? `${xp.toLocaleString()} of ${next.toLocaleString()} XP to the next level` : 'Top level'} data-testid="rwd-level"><svg viewBox="0 0 108 108" aria-hidden="true"><circle cx="54" cy="54" r="46" /><circle cx="54" cy="54" r="46" className="is-fill" strokeDasharray={`${pct * C} ${C}`} /></svg>
    <span><b className="m-num">{level?.level ?? 1}</b><small>{level?.name || 'Rookie'}</small></span></div>;
}

function Streak({ n }) {
  return <div className="rwd-streak" aria-label={`${n} day streak`} data-tip="Claim the daily check-in every day. Each day in a row adds +5 points, up to +50" data-testid="rwd-streak">{Array.from({ length: 7 }, (_, i) => <i key={i} className={i < (n % 7 || (n ? 7 : 0)) ? 'is-lit' : ''} style={{ '--i': i }}><Ic3 e="🔥" size="100%" /></i>)}<small><b className="m-num">{n}</b> day streak</small></div>;
}

function ClaimOrb({ it, busy, onClaim, i }) {
  const go = REWARD_GO[it.id];
  const face = <><i className="rwd-orb-art"><Ic3 e={REWARD_ICON[it.id] || '🎁'} size="44px" /></i><b>{it.label}</b><em className="m-num">+{it.amount}</em></>;
  if (it.claimable) return <button type="button" className="rwd-orb is-ready" style={{ '--i': i }} disabled={!!busy} onClick={() => onClaim(it.id)} data-tip={`${it.how} Ready: tap to claim`} data-testid={`rwd-claim-${it.id}`}>{face}<small>{busy === it.id ? 'Claiming…' : 'Claim'}</small></button>;
  const done = it.once ? !!it.claimed : !!it.claimed && !go;
  return go && !done ? <Link className="rwd-orb" style={{ '--i': i }} to={go} data-tip={it.how} data-testid={`rwd-go-${it.id}`}>{face}<small>How to earn</small></Link>
    : <div className={`rwd-orb${done || it.claimed ? ' is-done' : ''}`} style={{ '--i': i }} data-tip={it.how} data-testid={`rwd-wait-${it.id}`}>{face}<small>{it.claimed ? 'Claimed' : 'Not yet'}</small></div>;
}

function FamilyBank({ items, balance, busy, onBuy }) {
  if (!items.length) return null;
  return <section className="rwd-panel rwd-bank" data-testid="rwd-bank"><header><Ic3 e="🏦" size="30px" /><span><h3>DEPOSIT POINTS</h3><small>Into your family's bank as MP. Weekly cap applies. You need a family first.</small></span></header>
    <div className="rwd-slots">{items.map((it, i) => { const short = balance < it.cost; return <button key={it.id} type="button" className="rwd-slot" style={{ '--i': i }} disabled={short || !!busy} onClick={() => onBuy(it)} data-tip={short ? `You need ${(it.cost - balance).toLocaleString()} more points` : `${it.label}: spends ${it.cost.toLocaleString()} points`} data-testid={`rwd-deposit-${it.id}`}><i aria-hidden="true"><u /><Ic3 e="🪙" size="30px" /></i><b className="m-num">{it.cost.toLocaleString()}</b><small>{it.label}</small></button>; })}</div></section>;
}

function Shop({ items, unlocks, balance, busy, onBuy }) {
  if (!items.length) return null;
  const owned = it => Object.keys(unlocks || {}).some(k => (it.grant?.badge ? k === `badge:${it.grant.badge}` : Object.entries(it.grant || {}).some(([a, b]) => k === `${a}:${b}`)));
  return <section className="rwd-panel rwd-shop" data-testid="rwd-shop"><header><Ic3 e="🛍" size="30px" /><span><h3>SPEND POINTS</h3><small>Boosts, raffle tickets, chat styles and badges.</small></span></header>
    <div className="rwd-shelf">{items.map((it, i) => { const have = owned(it); const short = balance < it.cost; return <button key={it.id} type="button" className={`rwd-item${have ? ' is-have' : ''}`} style={{ '--i': i }} disabled={have || short || !!busy} onClick={() => onBuy(it)} data-tip={it.desc || it.how || it.label} data-testid={`rwd-buy-${it.id}`}><b>{it.label}</b><em className="m-num">{have ? 'Owned' : it.cost.toLocaleString()}</em></button>; })}</div></section>;
}

function BadgeHunt({ q, onOpen }) {
  const next = useMemo(() => {
    const byId = Object.fromEntries((q?.badges || []).map(b => [b.id, b]));
    const picks = (q?.next || []).map(id => byId[id]).filter(Boolean);
    return (picks.length ? picks : (q?.badges || []).filter(b => !b.earned).sort((a, b) => (b.pct || 0) - (a.pct || 0))).slice(0, 3);
  }, [q]);
  if (!next.length) return null;
  const C = 2 * Math.PI * 40;
  return <section className="rwd-panel rwd-hunt" data-testid="rwd-hunt"><header><Ic3 e="🎯" size="30px" /><span><h3>THE HUNT</h3><small>The badges you are closest to. Do the task, the badge lands by itself.</small></span></header>
    <div className="rwd-targets">{next.map((b, i) => { const t = (b.tasks || []).find(x => !x.done) || b.tasks?.[0]; return <article key={b.id} className="rwd-target" style={{ '--i': i }}>
      <button type="button" className="rwd-target-art" onClick={() => onOpen(b)} data-tip={`${b.name}: ${b.pct || 0}% there. Open it`} data-testid={`rwd-target-${b.id}`}><svg viewBox="0 0 92 92" aria-hidden="true"><circle cx="46" cy="46" r="40" /><circle cx="46" cy="46" r="40" className="is-fill" strokeDasharray={`${((b.pct || 0) / 100) * C} ${C}`} /></svg><BadgeArt art={b.art} name={b.name} locked size="sm" /></button>
      <b>{b.name}</b><em className="m-num">{b.pct || 0}%</em><small>{t?.label || 'Keep going'}</small><Link className="m-btn" to={goFor(t)} data-tip="Go where this task gets done">Go</Link></article>; })}</div></section>;
}

function TrophyWall({ q, onOpen }) {
  const [lens, setLens] = useState('all');
  const rows = useMemo(() => [...(q?.badges || [])].filter(b => (lens === 'all' ? true : lens === 'earned' ? b.earned : !b.earned)).sort((a, b) => (b.earned - a.earned) || (tierOrder.indexOf(a.tier) - tierOrder.indexOf(b.tier)) || ((b.pct || 0) - (a.pct || 0))), [q, lens]);
  return <section className="rwd-panel rwd-wall" data-testid="rwd-wall"><header><Ic3 e="🏆" size="30px" /><span><h3>TROPHY WALL</h3><small><b className="m-num">{q?.earned || 0}</b> of {q?.total || 0} earned. The first {q?.editionCap || 100} to earn one are numbered forever.</small></span>
    <div className="m-seg" role="group" aria-label="Which badges">{[['all', 'All'], ['earned', 'Earned'], ['left', 'To earn']].map(([k, l]) => <button key={k} type="button" className={lens === k ? 'active' : ''} aria-pressed={lens === k} onClick={() => setLens(k)} data-testid={`rwd-wall-${k}`}>{l}</button>)}</div></header>
    {rows.length ? <div className="rwd-medals">{rows.map((b, i) => <button key={b.id} type="button" className={`rwd-medal is-${b.tier || 'common'}${b.earned ? ' is-earned' : ''}`} style={{ '--i': Math.min(i, 14) }} onClick={() => onOpen(b)} data-tip={`${b.name}${b.earned ? ' · earned' : ` · ${b.pct || 0}%`}${q?.rarity?.[b.id] != null ? ` · ${q.rarity[b.id]}% of wallets have it` : ''}`} data-testid={`rwd-medal-${b.id}`}><BadgeArt art={b.art} name={b.name} locked={!b.earned} size="sm" /><small>{b.name}</small></button>)}</div>
      : <p className="rwd-none">{lens === 'earned' ? 'None yet. Start with The Hunt above.' : 'You earned them all.'}</p>}</section>;
}

function Board({ me }) {
  const [rows, setRows] = useState([]);
  useEffect(() => { let on = true; fetch(apiUrl('/api/reputation/rewards-board?limit=5')).then(r => (r.ok ? r.json() : null)).then(j => on && j && setRows(j.rows || [])).catch(() => {}); return () => { on = false; }; }, []);
  if (!rows.length) return null;
  const top = Math.max(1, ...rows.map(r => r.points));
  return <section className="rwd-panel rwd-board" data-testid="rwd-board"><header><Ic3 e="👑" size="30px" /><span><h3>TOP POINTS</h3></span></header>
    <ol>{rows.map((r, i) => <li key={r.address} className={r.address === me ? 'is-me' : ''} style={{ '--i': i, '--w': `${Math.max(6, (r.points / top) * 100)}%` }}><b className="m-num">{i + 1}</b><span>{r.handle || `${String(r.address).slice(0, 4)}…`}</span><i aria-hidden="true" /><em className="m-num">{r.points.toLocaleString()}</em></li>)}</ol></section>;
}

export function RewardsDash() {
  const { wallet, signMessage, connect } = useWallet() || {}; const address = wallet?.address;
  const [q, reloadQ] = useQuests(address); const [r, setR] = useState(null); const [shop, setShop] = useState(null); const [busy, setBusy] = useState(''); const [open, setOpen] = useState(null); const [pop, setPop] = useState(null);
  const load = useCallback(() => { if (!address) return;
    fetch(apiUrl(`/api/reputation/rewards/${address}`)).then(x => (x.ok ? x.json() : null)).then(j => j && setR(j)).catch(() => {});
    fetch(apiUrl(`/api/reputation/shop?address=${address}`)).then(x => (x.ok ? x.json() : null)).then(j => j && setShop(j)).catch(() => {}); }, [address]);
  useEffect(() => { load(); }, [load]);
  const balance = Number(shop?.points ?? r?.total ?? 0) - Number(shop?.spent ?? 0); const shown = useCountUp(balance);
  const ready = (r?.items || []).filter(i => i.claimable);
  const session = () => getChatSession(wallet.address, signMessage);
  const claim = async id => { setBusy(id); try { const j = await postJson('/api/reputation/rewards/claim', { address, session: await session(), reward: id }); setPop({ n: j.gained, at: Date.now() }); toast.success(`+${j.gained} points${j.streak > 1 ? ` · ${j.streak} day streak` : ''}`); load(); reloadQ(); } catch (e) { toast.error(e.message); } finally { setBusy(''); } };
  const claimAll = async () => { setBusy('all'); let total = 0; try { const s = await session(); for (const it of ready) { const j = await postJson('/api/reputation/rewards/claim', { address, session: s, reward: it.id }); total += j.gained; } if (total) { setPop({ n: total, at: Date.now() }); toast.success(`+${total} points`); } } catch (e) { toast.error(e.message); } finally { setBusy(''); load(); reloadQ(); } };
  const buy = async it => { setBusy(it.id); try { await postJson('/api/reputation/shop/buy', { address, session: await session(), item: it.id }); toast.success(it.kind === 'mp' ? `Deposited ${it.cost.toLocaleString()} points` : `Got ${it.label}`); load(); } catch (e) { toast.error(e.message); } finally { setBusy(''); } };
  if (!address) return <section className="rwd rwd-out" data-testid="rewards-dash"><ShaderWall mood="colony" /><div><Ic3 e="🎁" size="84px" /><h2>Your points, badges and rewards</h2><p>Connect your wallet to see what you can claim today.</p><button type="button" className="m-btn m-go" onClick={() => connect?.()} data-testid="rwd-connect">Connect wallet</button></div></section>;
  const items = shop?.items || [];
  return <section className="rwd" data-testid="rewards-dash"><ShaderWall mood="colony" />
    <header className="rwd-hero"><div className="rwd-bal"><small>YOUR POINTS TO SPEND</small><b className="m-num" data-testid="rwd-balance">{r || shop ? shown.toLocaleString() : '…'}{pop ? <em key={pop.at} className="rwd-pop">+{pop.n}</em> : null}</b>
      <span className="rwd-kpis"><span data-tip="Your place among all wallets, by points earned"><small>RANK</small><b className="m-num">{r?.rank ? `#${r.rank}` : '…'}</b></span><span data-tip="Points you have earned in total"><small>EARNED</small><b className="m-num">{Number(r?.total || 0).toLocaleString()}</b></span><span data-tip="Boost credits and raffle tickets you own"><small>BOOSTS · TICKETS</small><b className="m-num">{shop?.boosts ?? 0} · {shop?.tickets ?? 0}</b></span></span></div>
      <Streak n={r?.streak || 0} /><LevelRing level={q?.level} /></header>
    <section className="rwd-panel rwd-claims" data-testid="rwd-claims"><header><Ic3 e="🎁" size="30px" /><span><h3>CLAIM TODAY</h3><small>{ready.length ? `${ready.length} ready to claim` : 'Nothing waiting. Come back tomorrow, or earn one below.'}</small></span>{ready.length > 1 ? <button type="button" className="m-btn m-go" disabled={!!busy} onClick={claimAll} data-tip="Claims everything that is ready" data-testid="rwd-claim-all">{busy === 'all' ? 'Claiming…' : `Claim all ${ready.reduce((s, i) => s + i.amount, 0)}`}</button> : null}</header>
      <div className="rwd-orbs">{(r?.items || []).map((it, i) => <ClaimOrb key={it.id} it={it} i={i} busy={busy} onClaim={claim} />)}</div></section>
    <div className="rwd-two"><BadgeHunt q={q} onOpen={setOpen} /><FamilyBank items={items.filter(i => i.kind === 'mp')} balance={balance} busy={busy} onBuy={buy} /></div>
    <TrophyWall q={q} onOpen={setOpen} />
    <div className="rwd-two"><Shop items={items.filter(i => i.kind !== 'mp')} unlocks={shop?.unlocks} balance={balance} busy={busy} onBuy={buy} /><Board me={r?.address} /></div>
    <Season me={q} />
    {open ? <BadgeDetail b={open} rarity={q?.rarity?.[open.id]} edition={q?.editions?.[open.id]} editionCap={q?.editionCap} onClose={() => setOpen(null)} /> : null}
  </section>;
}
