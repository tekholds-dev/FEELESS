import React, { useEffect, useState } from 'react';
import { Ic3 } from '../../lib/icon3d';
import { SplitFlow, money } from './SplitFlow';
import { GrowthExample, NOT_PONZI } from './GrowthExample';
import { ColonyPot } from './HiveBoard';
import { StashWeb } from './StashWeb';
import '../../styles/boosts.css';

// 👑 THE OWNER'S COLLECTIVE FOLDER (owner 2026-11-04: "all the configs and hover to explain, cause the math kills me"): where the money stands, and every setting, each with its effect drawn live beside it. Server-gated to the owner.
const PLAN_ROWS = (n, l) => [[`${n}Days`, `${l}: days`, 'd', 1, 'locked', 'How long this plan takes to come back.'], [`${n}Back`, `${l}: comes back`, '%', 1, 'back', 'Of what locks, what comes back to the agent. The rest stays with the Collective.'], [`${n}Weight`, `${l}: fee pot weight`, 'x', 0.5, 'pot', 'How big a part of the fee pot this plan earns while its money works.'], [`${n}Room`, `${l}: earn limit`, 'x', 0.5, 'pot', 'It can earn from the pot up to this many times what it sent, fading by half every 30 days. It stops a late big send draining the pot.']];
const GROUPS = [
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
  const S = [['keep', 'Keeps', '#4fb8ff'], ['pot', 'Fee pot', '#ff8bd8'], ['locked', 'Locked', '#a06bff'], ['owed', 'Agents earned', '#3ee58a']]; const top = Math.max(1e-9, ...rows.flatMap(r => S.map(([k]) => r[k] || 0))); const X = i => (i / (rows.length - 1)) * 600; const Y = v => 118 - ((v || 0) / top) * 110;
  return <figure className="ge-chart" data-testid="cof-trend"><figcaption>THE COLLECTIVE, DAY BY DAY</figcaption><svg viewBox="0 0 600 124" preserveAspectRatio="none" role="img" aria-label="The Collective day by day">{S.map(([k, , c]) => <path key={k} d={rows.map((r, n) => `${n ? 'L' : 'M'}${X(n).toFixed(1)} ${Y(r[k]).toFixed(1)}`).join(' ')} stroke={c} />)}</svg><ul className="ge-legend">{S.map(([k, l, c]) => <li key={k}><i style={{ background: c }} />{l} <b className="m-num">{money(rows[rows.length - 1][k])}</b></li>)}</ul></figure>;
}
function Flow({ d }) {
  const t = d.totals || {}; const u = t.usd || {}; const rows = Object.entries(t.in || {}).sort((a, b) => b[1] - a[1]); const most = Math.max(1e-9, ...rows.map(r => r[1])); const tanks = [['keep', 'THE COLLECTIVE KEEPS', u.keep, 'Yours: everything not promised to anyone.'], ['pot', 'FEE POT', u.pot, 'Paying out to agents with money locked, a part at a time.'], ['locked', 'COMING BACK', u.locked, 'Sent by agents, on its way back on its date.'], ['owed', 'AGENTS EARNED', u.owed, 'Released to agents. This must always be in the wallet.']]; const top = Math.max(1e-9, ...tanks.map(x => x[2] || 0));
  const chain = d.chain; const short = chain?.short?.length;
  return <div className="cof-flow"><div className="cof-tanks">{tanks.map(([k, l, v, tip]) => <span key={k} className={`cof-tank is-${k}`} data-tip={tip} data-testid={`cof-tank-${k}`}><i aria-hidden="true"><u style={{ transform: `scaleY(${Math.max(0.03, (v || 0) / top)})` }} /></i><small>{l}</small><b className="m-num">{money(v)}</b></span>)}</div>
    <div className={`cof-cover${short ? ' is-short' : chain ? ' is-ok' : ''}`} data-testid="cof-cover" data-tip="Every 5 minutes the real wallet is read and compared with what it must hold: fee pot + locked + earned."><b>{!chain ? 'NOT READ YET' : short ? `SHORT IN ${chain.short.join(' + ')}` : 'FULLY COVERED'}</b><small>{chain ? Object.entries(chain.tokens).map(([k, v]) => `${k}: holds ${(v.chain / (k === 'SOL' ? 1e9 : 1e6)).toFixed(k === 'SOL' ? 4 : 2)}, must hold ${(v.need / (k === 'SOL' ? 1e9 : 1e6)).toFixed(k === 'SOL' ? 4 : 2)}`).join(' · ') : 'The first read comes within 5 minutes.'}</small></div>
    <div className={`cof-cover${d.audit?.ok ? ' is-ok' : d.audit ? ' is-short' : ''}`} data-testid="cof-audit" data-tip="Every 5 minutes the whole chain is walked from the first dollar. It must equal what the ledger holds to the unit. An edited ledger refuses to load."><b>{!d.audit ? 'CHAIN NOT WALKED YET' : d.audit.ok ? `CHAIN UNBROKEN · ${d.links} LINKS` : 'CHAIN BROKEN'}</b><small>{d.audit && !d.audit.ok ? d.audit.why : `Head ${String(d.head || '').slice(0, 20)}…`}</small></div>
    <Trend hist={d.hist} />
    <section className="cof-in"><h4><Ic3 e="💸" /> MONEY IN<small>{t.agents || 0} agents have sent proofs · paying {money((t.ratePerSecUsd || 0) * 86400)} a day back</small></h4>
      {rows.length ? <ul>{rows.map(([k, v], i) => <li key={k} style={{ '--i': i }}><small>{IN[k] || k}</small><i aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, v / most)})` }} /></i><b className="m-num">{money(v)}</b></li>)}</ul> : <p className="fch-nil">No money counted yet. The ledger starts with the next deposit, fee or proof sent.</p>}</section>
    <section className="cof-why"><h4><Ic3 e="🛡" /> WHY IT IS NOT A PONZI</h4><ul>{NOT_PONZI.map(([h, t]) => <li key={h} data-tip={t}><b>✓</b> {h}</li>)}</ul></section>
    {d.agents?.length ? <section className="cof-top"><h4><Ic3 e="🤖" /> AGENTS</h4><ol>{d.agents.map(a => <li key={a.id}><b>{a.name || a.id}</b><small data-tip="Sent · locked · earned">{money(a.sentUsd)} · {money(a.lockedUsd)} · {money(a.owedUsd)}</small><em className="m-num" data-tip="Its fee pot boost right now">{a.levers?.weightX}x</em></li>)}</ol></section> : null}</div>;
}
function Settings({ d, save, busy }) {
  const [c, setC] = useState(d.cfg); const [hot, setHot] = useState(null);
  useEffect(() => setC(d.cfg), [d.cfg]);
  const dirty = Object.keys(c).filter(k => c[k] !== d.cfg[k]); const rules = { ...c, plans: ['week', 'month', 'quarter'].map(n => ({ plan: n, days: c[`${n}Days`], backPct: c[`${n}Back`], weightX: c[`${n}Weight`], roomX: c[`${n}Room`] })).concat({ plan: 'vault', days: null, backPct: 0, weightX: c.vaultWeight, roomX: c.vaultRoom }) };
  return <div className="cof-set"><div className="cof-rows">{GROUPS.map(([h, rows]) => <section key={h}><h4>{h}</h4>{rows.map(([k, l, u, step, node, tip]) => { const [lo, hi] = d.bounds[k]; const v = c[k]; const moved = v !== d.defaults[k];
      return <label key={k} className={`cof-row${moved ? ' is-moved' : ''}`} data-tip={tip} onMouseEnter={() => setHot(node)} onMouseLeave={() => setHot(null)} onFocus={() => setHot(node)} onBlur={() => setHot(null)} data-testid={`cof-${k}`}><span>{l}<i className="cof-q" aria-hidden="true">?</i></span><input type="range" min={lo} max={hi} step={step} value={v} aria-label={l} onChange={e => setC(x => ({ ...x, [k]: Number(e.target.value) }))} /><b className="m-num">{u === '$' ? `$${v}` : `${v}${u}`}</b></label>; })}</section>)}
    <section><h4>What a boost does</h4><div className="cof-row" data-tip="Bigger payouts: boosts move the split, the speed and the fee pot weight. Rank only: boosts order the stage and change no money."><span>Boost mode<i className="cof-q" aria-hidden="true">?</i></span><span className="m-seg" role="group" aria-label="What a boost does">{[['payout', 'Bigger payouts'], ['rank', 'Rank only']].map(([k, l]) => <button key={k} type="button" className={c.boostMode === k ? 'active' : ''} aria-pressed={c.boostMode === k} onClick={() => setC(x => ({ ...x, boostMode: k }))} data-testid={`cof-mode-${k}`}>{l}</button>)}</span></div>
      <div className="cof-row is-locked" data-tip="No payout code is switched on. It stays off until a lawyer has checked this and the payout wallet is set up." data-testid="cof-withdrawals"><span>User withdrawals<i className="cof-q" aria-hidden="true">?</i></span><b className="cof-lock">OFF</b></div></section></div>
    <aside className="cof-side"><small>LIVE PREVIEW OF YOUR SETTINGS</small><SplitFlow rules={rules} hot={hot} testid="cof-preview" />
      <div className="cof-acts"><button type="button" className="m-btn" disabled={busy} onClick={() => setC({ ...d.defaults })} data-tip="Put every slider back to the starting numbers. Nothing changes until you save." data-testid="cof-defaults">Starting numbers</button><button type="button" className="m-btn m-go" disabled={busy || !dirty.length} onClick={() => save(c)} data-tip="New money and the next minute use these. Nothing already earned shrinks." data-testid="cof-save">{busy ? 'Saving…' : dirty.length ? `Save ${dirty.length} change${dirty.length > 1 ? 's' : ''}` : 'Saved'}</button></div>
      {d.log?.length ? <ol className="cof-log">{d.log.slice(0, 5).map(x => <li key={x.at}>{new Date(x.at * 1000).toLocaleDateString()} · {Object.entries(x.changed).map(([k, [a, b]]) => `${k} ${a} → ${b}`).join(', ')}</li>)}</ol> : null}</aside></div>;
}
export function CollectiveOwner({ call }) {
  const [d, setD] = useState(null); const [tab, setTab] = useState('flow'); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  useEffect(() => { let on = true; const go = () => { if (!document.hidden) call('/admin/collective').then(x => on && setD(x)).catch(e => on && setErr(e.message)); }; go(); const t = setInterval(go, 30000); return () => { on = false; clearInterval(t); }; }, [call]);
  const save = async cfg => { setBusy(true); setErr(''); try { setD(await call('/admin/collective', { method: 'POST', body: JSON.stringify({ cfg }) })); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  return <div className="cof" data-testid="cof"><header className="cof-h"><span><small>OWNER ONLY</small><h3>The Collective</h3></span><span className="m-seg" role="tablist" aria-label="Collective folder">{[['flow', 'Money'], ['year', 'A year'], ['stash', 'Stash'], ['set', 'Settings'], ['wallet', 'Wallet + LP']].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`cof-tab-${k}`}>{l}</button>)}</span></header>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
    {tab === 'wallet' ? <ColonyPot call={call} /> : tab === 'stash' ? <StashWeb call={call} testid="cof-stash" /> : tab === 'year' && d ? <GrowthExample rules={{ ...d.cfg, plans: ['week', 'month', 'quarter'].map(n => ({ plan: n, days: d.cfg[`${n}Days`], backPct: d.cfg[`${n}Back`], weightX: d.cfg[`${n}Weight`], roomX: d.cfg[`${n}Room`] })).concat({ plan: 'vault', days: null, backPct: 0, weightX: d.cfg.vaultWeight, roomX: d.cfg.vaultRoom }) }} /> : !d ? <p className="fch-nil">reading the ledger…</p> : tab === 'flow' ? <Flow d={d} /> : <Settings d={d} save={save} busy={busy} />}</div>;
}
