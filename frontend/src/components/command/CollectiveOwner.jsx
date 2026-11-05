import React, { Suspense, lazy, useEffect, useState } from 'react';
import { Ic3 } from '../../lib/icon3d';
import { GrowthCalc, money } from './SplitFlow';
import { GrowthExample, NOT_PONZI } from './GrowthExample';
import { ColonyPot } from './HiveBoard';
import { StashWeb } from './StashWeb';
import { ProChart } from './ProChart';
import { Fx, NumCell, Presets, Roll } from './CollectiveSetup';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import '../../styles/boosts.css';

// 👑 THE OWNER'S COLLECTIVE FOLDER (owner 2026-11-04: "all the configs and hover to explain, cause the math kills me"): where the money stands, and every setting, each with its effect drawn live beside it. Server-gated to the owner.
const PLAN_ROWS = (n, l) => [[`${n}Days`, `${l}: days`, 'd', 1, 'locked', 'How long this plan takes to come back.'], [`${n}Back`, `${l}: comes back`, '%', 1, 'back', 'Of what locks, what comes back to the agent. The rest stays with the Collective.'], [`${n}Weight`, `${l}: fee pot weight`, 'x', 0.5, 'pot', 'How big a part of the fee pot this plan earns while its money works.'], [`${n}Room`, `${l}: earn limit`, 'x', 0.5, 'pot', 'It can earn from the pot up to this many times what it sent, fading by half every 30 days. It stops a late big send draining the pot.']];
const GROUPS = [
  ['From outside the members', [['sitePct', 'Swap fees to the pot', '%', 1, 'pot', 'Of FEELESS swap fees from regular traders, what you send to the fee pot. This is the only money that lets the average member come out ahead, and it comes out of FEELESS\'s own income.']]],
  ['Where a proof goes', [['skimPct', 'Collective keeps', '%', 1, 'kept', 'Taken the moment a proof is sent. Higher grows the wallet faster, but makes sending worth less to users.']]],
  ['1 week plan', PLAN_ROWS('week', '1 week')], ['30 day plan', PLAN_ROWS('month', '30 days')], ['90 day plan', PLAN_ROWS('quarter', '90 days')],
  ['The Vault', [['vaultWeight', 'Fee pot weight', 'x', 0.5, 'pot', 'What it sends never comes back, so it earns the biggest part of the pot. The claim fades by half every 45 days unless it keeps sending.'], ['vaultRoom', 'Earn limit', 'x', 0.5, 'pot', 'It can earn up to this many times what it sent, fading by half every 30 days.']]],
  ['The fee pot', [
    ['potPct', 'Trade fees to the pot', '%', 1, 'pot', 'Of real trade and task fees only, what goes to the pot members earn from. The rest is the Collective\'s to keep. Deposits and sends can never reach it, which is what keeps this from being a Ponzi.'],
    ['potPayDayPct', 'Pot pays per day', '%', 1, 'pot', 'How much of the pot pays out each day. It only ever pays a part of what is there, so it can\'t run dry or go negative.'],
    ['weightMaxX', 'Full boost weight', 'x', 0.1, 'pot', 'How much bigger a part of the pot a full boost takes. The pot still pays the same total.'],
    ['capPct', 'Most one owner gets', '%', 1, 'pot', 'A whale limit: the biggest part of the pot one owner can take, counting all its agents, once there are enough owners.'],
  ]],
  ['Boost points', [
    ['ptsBase', 'Points per send', '', 1, null, 'Every verified send earns this much before dollars count.'],
    ['ptsPerUsd', 'Points per dollar', '', 0.5, null, 'Added for each dollar sent, then graded by the print: 0.5x to 1.5x.'],
    ['ptsMaxSend', 'Most from one send', '', 5, null, 'So big money alone cannot buy a full boost.'],
    ['ptsPerDay', 'Points for 1 day sooner', '', 1, 'locked', 'What it costs to spend points on bringing a date closer. A date can never come closer than a third of its plan.'],
    ['boostBackPts', 'Full boost adds back', '%', 1, 'back', 'How much more comes back at a full boost.'],
    ['boostFadeDays', 'Points fade by half in', 'd', 1, null, 'Boost points lose half their worth in this many days, so an agent has to keep proving.'],
  ]],
  ['Agent fees', [
    ['depositPct', 'Deposit + top-up fee', '%', 1, null, 'Taken from every deposit into an agent, in the same transaction, straight to the Collective wallet.'],
    ['firstMinUsd', 'First deposit from', '$', 5, null, 'The least a new agent can start with.'],
    ['txnSmallPct', 'Small trade fee', '%', 0.5, null, 'For a trade under the small size. Small trades pay the most.'],
    ['txnSmallUsd', 'Small means under', '$', 1, null, 'The size where the small fee ends.'],
    ['txnMidPct', 'Middle trade fee', '%', 0.5, null, 'For a trade between the two sizes.'],
    ['txnBigUsd', 'Big means over', '$', 10, null, 'The size where the big fee starts.'],
    ['txnBigPct', 'Big trade fee', '%', 0.5, null, 'For a trade over the big size.'],
  ]],
];
const IN = { vault: 'Vault', deposit: 'First deposits', topup: 'Top-ups', txn: 'Trade fees', task: 'Task fees', proofs: 'Kept from proofs', release: 'From releases', pass: 'Agent Pass', gift: 'Gifts' };
function Trend({ hist }) {
  const rows = hist || []; if (rows.length < 2) return <p className="fch-nil">The Collective's growth chart starts after its second day.</p>;
  const S = [['keep', 'Keeps', '#4fb8ff'], ['pot', 'Fee pot', '#ff8bd8'], ['locked', 'Locked', '#a06bff'], ['owed', 'Agents earned', '#3ee58a']];
  return <figure className="ge-chart" data-testid="cof-trend"><figcaption>THE COLLECTIVE, DAY BY DAY</figcaption><ProChart height={190} testid="cof-trend-pro" label="The Collective day by day" fmt={money} stamps={false} lines={S.map(([k, name, color]) => ({ name, color, rows: rows.map(r => ({ at: r.at || r.t, v: r[k] || 0 })) }))} /><div className="cs-legend">{S.map(([k, l, c]) => <span key={k}><i style={{ background: c }} />{l}</span>)}</div></figure>;
}
// 🌍 Money from outside the members is what lets the average member come out ahead. Nothing moves by itself: you send it, and it counts once the chain shows it landed.
function Outside({ d, save, busy }) {
  const [sig, setSig] = useState(''); const site = d.site || {}; const pct = d.cfg?.sitePct ?? 20;
  return <section className="cof-site" data-testid="cof-site"><h4><Ic3 e="🌍" /> FROM OUTSIDE THE MEMBERS<small>{pct}% of FEELESS swap fees from regular traders goes to the fee pot</small></h4><div className="cof-site-t">{[['SWAP FEES SO FAR', money(site.feesUsd), 'Every fee in FEELESS\'s own ledger'], ['THE POT\'S SHARE', money((site.feesUsd || 0) * pct / 100), `${pct}% of that. Change it in Settings`], ['MOVED', money(site.movedUsd), 'Sent to the Collective wallet and seen on the chain'], ['STILL TO MOVE', money(site.owedUsd), 'Send this from the FEELESS fee wallet to the Collective wallet']].map(([k, v, t]) => <span key={k} data-tip={t}><small>{k}</small><b className="m-num">{v}</b></span>)}</div>
    <form className="cof-site-f" onSubmit={e => { e.preventDefault(); if (sig.trim()) { save(null, { siteSig: sig.trim() }); setSig(''); } }}><input className="m-input" value={sig} onChange={e => setSig(e.target.value)} placeholder="Paste the transaction after you send it" aria-label="Transaction" data-testid="cof-site-sig" /><button type="submit" className="m-btn m-go" disabled={busy || !sig.trim()} data-tip="It is read from the chain before it counts" data-testid="cof-site-add">Count it</button></form></section>;
}
function Validators({ d, save, busy }) {
  const held = d.held || [];
  return <section className="cof-val" data-testid="cof-validators"><h4><Ic3 e="⚖" /> THE FIVE VALIDATORS<small>{d.reviewed || 0} proofs checked · {held.length} held</small></h4><div className="cof-val-s">{[['Tally', 'The numbers add up'], ['Sherlock', 'The evidence is there'], ['Devil', 'It was not gamed'], ['Archivist', 'The record is in order'], ['Judge', 'The final call']].map(([n, t]) => <span key={n} data-tip={t}><b>{n}</b><small>{t}</small></span>)}</div>
    {held.length ? <ol className="cof-held">{held.map(h => <li key={h.id} data-testid={`cof-held-${h.id}`}><b>{h.name} · {h.sym ? `$${h.sym}` : 'Proof'}</b><small>{(h.review?.seats || []).filter(x => !x.ok && x.k !== 'judge').map(x => `${x.name}: ${x.why}`).join(' ')}</small><button type="button" className="m-btn" disabled={busy} onClick={() => save(null, { clear: { cat: h.cat, id: h.id } })} data-tip="You checked it yourself. It starts earning" data-testid={`cof-clear-${h.id}`}>Clear it</button></li>)}</ol> : <p className="fch-nil">Nothing held.</p>}</section>;
}
function Flow({ d, save, busy, part }) {
  const t = d.totals || {}; const u = t.usd || {}; const rows = Object.entries(t.in || {}).sort((a, b) => b[1] - a[1]); const most = Math.max(1e-9, ...rows.map(r => r[1])); const tanks = [['keep', 'THE COLLECTIVE KEEPS', u.keep, 'Yours: everything not promised to anyone.'], ['pot', 'FEE POT', u.pot, 'Paying out to agents with money locked, a part at a time.'], ['locked', 'COMING BACK', u.locked, 'Sent by agents, on its way back on its date.'], ['owed', 'AGENTS EARNED', u.owed, 'Released to agents. This must always be in the wallet.']];
  const chain = d.chain; const short = chain?.short?.length;
  if (part === 'top') return <div className="cof-flow"><div className="cof-tanks">{tanks.map(([k, l, v, tip]) => <span key={k} className={`cof-tank is-${k}`} data-tip={tip} data-testid={`cof-tank-${k}`}><small>{l}</small><Roll v={v || 0} fmt={money} /></span>)}</div>
    <div className={`cof-cover${short ? ' is-short' : chain ? ' is-ok' : ''}`} data-testid="cof-cover" data-tip="Every 5 minutes the real wallet is read and compared with what it must hold: fee pot + locked + earned."><b>{!chain ? 'NOT READ YET' : short ? `SHORT IN ${chain.short.join(' + ')}` : 'FULLY COVERED'}</b><small>{chain ? Object.entries(chain.tokens).map(([k, v]) => `${k}: holds ${(v.chain / (k === 'SOL' ? 1e9 : 1e6)).toFixed(k === 'SOL' ? 4 : 2)}, must hold ${(v.need / (k === 'SOL' ? 1e9 : 1e6)).toFixed(k === 'SOL' ? 4 : 2)}`).join(' · ') : 'The first read comes within 5 minutes.'}</small></div>
    <div className={`cof-cover${d.audit?.ok ? ' is-ok' : d.audit ? ' is-short' : ''}`} data-testid="cof-audit" data-tip="Every 5 minutes the whole chain is walked from the first dollar. It must equal what the ledger holds to the unit. An edited ledger refuses to load."><b>{!d.audit ? 'CHAIN NOT WALKED YET' : d.audit.ok ? `CHAIN UNBROKEN · ${d.links} LINKS` : 'CHAIN BROKEN'}</b><small>{d.audit && !d.audit.ok ? d.audit.why : `Head ${String(d.head || '').slice(0, 20)}…`}</small></div></div>;
  return <div className="cof-flow">
    <Trend hist={d.hist} />
    <Outside d={d} save={save} busy={busy} />
    <Validators d={d} save={save} busy={busy} />
    <section className="cof-in"><h4><Ic3 e="💸" /> MONEY IN<small>{t.agents || 0} agents have sent proofs · paying {money((t.ratePerSecUsd || 0) * 86400)} a day back</small></h4>
      {rows.length ? <ul>{rows.map(([k, v], i) => <li key={k} style={{ '--i': i }}><small>{IN[k] || k}</small><i aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, v / most)})` }} /></i><b className="m-num">{money(v)}</b></li>)}</ul> : <p className="fch-nil">No money counted yet. The ledger starts with the next deposit, fee or proof sent.</p>}</section>
    <section className="cof-why"><h4><Ic3 e="🛡" /> WHY IT IS NOT A PONZI</h4><ul>{NOT_PONZI.map(([h, t]) => <li key={h} data-tip={t}><b>✓</b> {h}</li>)}</ul></section>
    {d.agents?.length ? <section className="cof-top"><h4><Ic3 e="🤖" /> AGENTS</h4><ol>{d.agents.map(a => <li key={a.id}><b>{a.name || a.id}</b><small data-tip="Sent · locked · earned">{money(a.sentUsd)} · {money(a.lockedUsd)} · {money(a.owedUsd)}</small><em className="m-num" data-tip="Its fee pot boost right now">{a.levers?.weightX}x</em></li>)}</ol></section> : null}</div>;
}
const allRows = GROUPS.flatMap(g => g[1]); const rowOf = k => allRows.find(r => r[0] === k);
const BackLines = lazy(() => import('./MoneyCharts').then(m => ({ default: m.BackLines })));
const PLAN_COLS = [['1 week', 'week'], ['30 days', 'month'], ['90 days', 'quarter'], ['Vault', 'vault']];
const PLAN_ROWS_T = [['Days', 'Days', 'How long this plan takes to come back.'], ['Back', 'Comes back', 'Of what locks, what comes back to the agent. The rest stays with the Collective.'], ['Weight', 'Fee pot weight', 'How big a part of the fee pot this plan earns.'], ['Room', 'Earn limit', 'It can earn from the pot up to this many times what it sent, fading over time.']];
const SETTING_GROUPS = [['THE FEE POT', [...GROUPS.find(g => g[0] === 'The fee pot')[1], rowOf('sitePct')]], ['BOOST POINTS', GROUPS.find(g => g[0] === 'Boost points')[1]], ['AGENT FEES', GROUPS.find(g => g[0] === 'Agent fees')[1]]];
// How pay works, on one chart, from the settings as they stand: $100 of each kind of money, and where it ends up.
// 💵 Where each $100 goes, in words and numbers, one row per kind of money.
const SPLIT_COLORS = { 'Back to the agent': '#3ee58a', 'The Collective': '#57c7ff', 'Fee pot, to members': '#ff8bd8', FEELESS: '#8fa3cc' };
function SplitBars({ c }) {
  const kept = c.skimPct; const lock = 100 - kept; const back = lock * c.monthBack / 100;
  const rows = [['A proof sent', [['Back to the agent', back], ['The Collective', 100 - back]]], ['A member trade fee', [['Fee pot, to members', c.potPct], ['The Collective', 100 - c.potPct]]], ['An outside swap fee', [['Fee pot, to members', c.sitePct], ['FEELESS', 100 - c.sitePct]]]];
  return <ul className="cof-bars" data-testid="cof-bars">{rows.map(([t, parts]) => <li key={t}><b>{t}</b><span className="cof-bar">{parts.map(([k, v]) => <i key={k} style={{ width: `${v}%`, background: SPLIT_COLORS[k] }} data-tip={`${k}: $${v.toFixed(2)}`} />)}</span><small>{parts.map(([k, v]) => <span key={k}><u style={{ background: SPLIT_COLORS[k] }} />{k} <em className="m-num">${v.toFixed(2)}</em></span>)}</small></li>)}</ul>;
}
function Settings({ d, save, busy }) {
  const [c, setC] = useState(d.cfg); useEffect(() => setC(d.cfg), [d.cfg]);
  const dirty = Object.keys(c).filter(k => c[k] !== d.cfg[k]);
  const cell = (r, label, compact) => { if (!r || !d.bounds[r[0]]) return <em className="cs-na">—</em>; const [k, l, u, step, , tip] = r; const b = d.bounds[k]; return <NumCell k={k} label={label || l} u={u} step={step} lo={b[0]} hi={b[1]} v={c[k]} start={d.defaults[k]} tip={tip} compact={compact} onChange={v => setC(x => ({ ...x, [k]: v }))} />; };
  const wait = <div className="spf-wait" />;
  return <Fx><div className="cof-one">
    <div className="cof-col">
      <section className="cs-sec"><h5>WHERE AN AGENT COMES OUT <small>with these numbers, as FEELESS grows</small></h5><GrowthCalc cfg={c} testid="cof-growth" /></section>
      <section className="cs-sec"><h5>WHERE EACH $100 GOES <small>on the 30 day plan</small></h5><SplitBars c={c} /></section>
      <section className="cs-sec"><h5>WHEN IT COMES BACK</h5><Suspense fallback={wait}><BackLines c={c} /></Suspense></section>
    </div>
    <div className="cof-col">
      <section className="cs-sec"><h5>START FROM</h5><Presets c={c} d={d} onPick={t => setC(x => ({ ...x, ...t, boostMode: x.boostMode }))} /></section>
      <section className="cs-sec"><h5>PLANS</h5><Table className="cs-t cs-plans-t"><TableHeader><TableRow><TableHead />{PLAN_COLS.map(([l]) => <TableHead key={l}>{l}</TableHead>)}</TableRow></TableHeader><TableBody>{PLAN_ROWS_T.map(([suffix, label, tip]) => <TableRow key={suffix} className="cof-row" data-tip={tip}><TableCell>{label}</TableCell>{PLAN_COLS.map(([l, n]) => <TableCell key={n}>{cell(rowOf(`${n}${suffix}`), `${l}: ${label}`, true)}</TableCell>)}</TableRow>)}</TableBody></Table></section>
      {SETTING_GROUPS.map(([h, rows]) => <section className="cs-sec" key={h}><h5>{h}</h5><Table className="cs-t"><TableBody>{rows.filter(Boolean).map(r => <TableRow key={r[0]} className="cof-row" data-tip={r[5]}><TableCell>{r[1]}</TableCell><TableCell>{cell(r)}</TableCell></TableRow>)}</TableBody></Table></section>)}
      <section className="cs-sec"><h5>RULES</h5><Table className="cs-t"><TableBody>
        <TableRow className="cof-row" data-tip="Collective keeps: taken the moment a proof is sent."><TableCell>Collective keeps</TableCell><TableCell>{cell(rowOf('skimPct'))}</TableCell></TableRow>
        <TableRow className="cof-row" data-tip="Bigger payouts: boosts move the split, the speed and the fee pot weight. Rank only: boosts order the stage and change no money."><TableCell>Boost mode</TableCell><TableCell><span className="m-seg" role="group" aria-label="What a boost does">{[['payout', 'Bigger payouts'], ['rank', 'Rank only']].map(([k, l]) => <button key={k} type="button" className={c.boostMode === k ? 'active' : ''} aria-pressed={c.boostMode === k} onClick={() => setC(x => ({ ...x, boostMode: k }))} data-testid={`cof-mode-${k}`}>{l}</button>)}</span></TableCell></TableRow>
        <TableRow className="cof-row" data-tip="No payout code is switched on. It stays off until a lawyer has checked this and the payout wallet is set up." data-testid="cof-withdrawals"><TableCell>User withdrawals</TableCell><TableCell><b className="cof-lock">OFF</b></TableCell></TableRow></TableBody></Table></section>
      <div className="cof-acts"><button type="button" className="m-btn" disabled={busy} onClick={() => setC({ ...d.defaults })} data-tip="Put every number back to the start. Nothing changes until you save." data-testid="cof-defaults">Starting numbers</button><button type="button" className="m-btn m-go" disabled={busy || !dirty.length} onClick={() => save(c)} data-tip="New money and the next minute use these. Nothing already earned shrinks." data-testid="cof-save">{busy ? 'Saving…' : dirty.length ? `Save ${dirty.length} change${dirty.length > 1 ? 's' : ''}` : 'Saved'}</button></div>
      {d.log?.length ? <ol className="cof-log">{d.log.slice(0, 5).map(x => <li key={x.at}>{new Date(x.at * 1000).toLocaleDateString()} · {Object.entries(x.changed).map(([k, [a, b]]) => `${k} ${a} → ${b}`).join(', ')}</li>)}</ol> : null}
    </div></div></Fx>;
}
// Opens only when asked, so the heavy parts cost nothing until then.
function More({ title, tip, testid, children }) {
  const [open, setOpen] = useState(false);
  return <details className="cs-more" onToggle={e => setOpen(e.currentTarget.open)} data-testid={testid}><summary data-tip={tip}>{title}</summary>{open ? children : null}</details>;
}
export function CollectiveOwner({ call }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  useEffect(() => { let on = true; const go = () => { if (!document.hidden) call('/admin/collective').then(x => on && setD(x)).catch(e => on && setErr(e.message)); }; go(); const t = setInterval(go, 30000); return () => { on = false; clearInterval(t); }; }, [call]);
  const save = async (cfg, extra) => { setBusy(true); setErr(''); try { setD(await call('/admin/collective', { method: 'POST', body: JSON.stringify(cfg ? { cfg } : extra) })); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  return <div className="cof" data-testid="cof"><header className="cof-h"><span><small>OWNER ONLY</small><h3>The Collective</h3></span></header>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
    {!d ? <p className="fch-nil">reading the ledger…</p> : <><Flow d={d} save={save} busy={busy} part="top" /><Settings d={d} save={save} busy={busy} /><Flow d={d} save={save} busy={busy} part="rest" />
      <More title="A year, on numbers you pick" tip="The same rules, played over a year" testid="cof-more-year"><GrowthExample rules={{ ...d.cfg, plans: ['week', 'month', 'quarter'].map(n => ({ plan: n, days: d.cfg[`${n}Days`], backPct: d.cfg[`${n}Back`], weightX: d.cfg[`${n}Weight`], roomX: d.cfg[`${n}Room`] })).concat({ plan: 'vault', days: null, backPct: 0, weightX: d.cfg.vaultWeight, roomX: d.cfg.vaultRoom }) }} /></More>
      <More title="Wallet and pool" tip="The Pool wallet, and opening a pool" testid="cof-more-wallet"><ColonyPot call={call} /></More>
      <More title="Stash" tip="Every proof kept sealed, with its web of sources" testid="cof-more-stash"><StashWeb call={call} testid="cof-stash" /></More></>}</div>;
}
