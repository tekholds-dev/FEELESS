import React, { useEffect, useState } from 'react';
import '../../styles/hqBridge.css';

// 🛰 THE BRIDGE (owner 2026-11-18: "a very much better view of each tab in HQ"). One screen that reads every group's vital signs from the
// admin reads HQ already has, and jumps straight to the tool. Each read is on its own: one slow or failing read never blanks the rest.
const READS = ['money-pulse', 'security', 'traffic', 'latency', 'shield', 'bugs', 'numbers', 'pulse'];

export const plain = s => String(s || '').replace(/\p{Extended_Pictographic}\uFE0F?/gu, '').trim();   // a label without its own emoji, so the chip's icon is not doubled
const n0 = v => (v == null || Number.isNaN(Number(v)) ? null : Number(v));
const usd = v => (n0(v) == null ? '—' : `$${n0(v).toLocaleString(undefined, { maximumFractionDigits: n0(v) >= 100 ? 0 : 2 })}`);
const num = v => (n0(v) == null ? '—' : n0(v).toLocaleString());
const sol = v => (n0(v) == null ? '—' : `${n0(v).toFixed(n0(v) >= 10 ? 2 : 4)} SOL`);

export function bridgeKpis(d) {
  const m = d['money-pulse'] || {}; const s = d.security || {}; const t = d.traffic || {}; const l = d.latency || {};
  const sh = d.shield || {}; const b = d.bugs || {}; const day = (t.daily || [])[(t.daily || []).length - 1] || {};
  const openBugs = d.bugs ? (b.bugs || []).filter(x => !['fixed', 'closed', 'wontfix', 'dupe'].includes(String(x.status || 'open'))).length : null;
  const slow = (l.providers || []).filter(p => p.ok === false).length; const alarms = d.latency ? (l.alarms || []).length : null;
  return [
    { k: 'fees', label: 'Fees today', value: usd(m.feesTodayUsd), sub: `7d ${usd(m.fees7dUsd)}`, tab: 'fees' },
    { k: 'sol', label: 'Admin wallet', value: sol(m.adminSol), sub: 'pays network costs', tab: 'money' },
    { k: 'visits', label: 'Visitors today', value: num(day.uniques), sub: `${num(day.views)} page views`, tab: 'traffic' },
    { k: 'sec', label: 'Security score', value: n0(s.score) == null ? '—' : `${s.score}/100`, sub: s.checks ? (k => `${num(k)} check${k === 1 ? '' : 's'} to fix`)(s.checks.filter(c => !c.ok).length) : '—', tab: 'overview', tone: n0(s.score) == null ? '' : s.score >= 85 ? 'up' : s.score >= 60 ? 'warn' : 'down' },
    { k: 'bugs', label: 'Open bugs', value: num(openBugs), sub: d.bugs ? `${num((b.bugs || []).length)} reported in all` : '—', tab: 'bugs', tone: openBugs == null ? '' : openBugs ? 'warn' : 'up' },
    { k: 'bots', label: 'Bots flagged', value: num(sh.counts?.bot), sub: `${num(sh.counts?.watch)} on watch · ${num(sh.scanned)} scanned`, tab: 'shield', tone: n0(sh.counts?.bot) ? 'warn' : '' },
    { k: 'lag', label: 'Lag alarms', value: num(alarms), sub: !l.providers ? '—' : slow ? `${slow} provider${slow > 1 ? 's' : ''} down` : 'every provider up', tab: 'latency', tone: alarms == null ? '' : alarms || slow ? 'down' : 'up' },
  ];
}

// Each group's two vital lines, read from the same data. A line with no data says so instead of a fake zero.
export function groupLines(name, d) {
  const m = d['money-pulse'] || {}; const t = d.traffic || {}; const p = d.pulse || {}; const nb = d.numbers || {}; const s = d.security || {}; const l = d.latency || {};
  const fee = p.fee || {}; const ref = (t.referrers || [])[0]; const page = (t.topPages24h || [])[0];
  const worst = [...(l.providers || [])].filter(x => n0(x.ms) != null).sort((a, b) => b.ms - a.ms)[0];
  switch (name) {
    case 'Money': return [['Fees, 7 days', usd(m.fees7dUsd)], ['Checks passing', m.checks ? `${(m.checks || []).filter(c => c.ok || c.info).length} of ${(m.checks || []).length}` : '—']];
    case 'Agents': return [["Fee's wallet", sol(fee.balanceSol)], ['Fee wins', fee.wins != null ? `${fee.wins}–${fee.losses} · ${fee.winRate}%` : '—']];
    case 'Launch': return [['Swaps, all time', num(nb.flow?.all?.swaps)], ['Traders, all time', num(nb.flow?.all?.traders)]];
    case 'Insights': return [['Busiest page, 24h', page ? `${page.page} · ${num(page.views)}` : '—'], ['Wallets active, 24h', num(p.activeWallets24h)]];
    case 'Marketing': return [['Top referrer', ref ? `${ref.host} · ${num(ref.visits)}` : '—'], ['Push subscribers', num(p.pushSubscribers)]];
    case 'Community': return [['$FEE holders', num(nb.holders?.count)], ['Chat, 24h', num(p.messages24h)]];
    case 'Rewards': return [['Custom badges', num(s.stats?.customBadges)], ['New profiles, 24h', num(p.newProfiles24h)]];
    case 'Safety': return [['Blocklisted', num(s.stats?.blocklisted)], ['Forged / replayed', s.signals ? `${num(s.signals.forgedSignatures)} / ${num(s.signals.replays)}` : '—']];
    case 'System': return [['Slowest provider', worst ? `${worst.name} · ${num(worst.ms)} ms` : '—'], ['Providers up', l.providers ? `${l.providers.filter(x => x.ok !== false).length} of ${l.providers.length}` : '—']];
    default: return [];
  }
}

function Spark({ rows }) {
  const v = (rows || []).map(r => Number(r.uniques) || 0); if (v.length < 2) return null;
  const top = Math.max(1, ...v); const pts = v.map((x, i) => `${(i / (v.length - 1)) * 100},${28 - (x / top) * 26}`).join(' ');
  return <svg className="hqb-spark" viewBox="0 0 100 30" preserveAspectRatio="none" aria-label={`Visitors, last ${v.length} days`} role="img"><polyline points={pts} /></svg>;
}

export function HqBridge({ call, groups, label, icon, onGo }) {
  const [d, setD] = useState({}); const [bad, setBad] = useState({}); const [at, setAt] = useState(0);
  useEffect(() => {
    let on = true;
    READS.forEach(r => call(`/admin/${r}`).then(x => on && setD(o => ({ ...o, [r]: x || {} }))).catch(e => on && setBad(o => ({ ...o, [r]: e.message || 'failed' }))));
    const t = setTimeout(() => on && setAt(Date.now()), 0);
    return () => { on = false; clearTimeout(t); };
  }, [call]);
  const kpis = bridgeKpis(d); const m = d['money-pulse'] || {};
  const fails = (m.checks || []).filter(c => !c.ok && !c.info); const nudges = (m.alerts || []).filter(a => a.tone !== 'ok');
  const failed = Object.keys(bad);
  return <section className="hqb" data-testid="hq-bridge">
    <div className="hqb-band" role="list" aria-label="HQ vital signs">
      {kpis.map((k, i) => <button key={k.k} type="button" role="listitem" className={`hqb-kpi${k.tone ? ` is-${k.tone}` : ''}`} style={{ '--i': i }} onClick={() => onGo(k.tab)} data-tip={`Open ${label(k.tab)}`} data-testid={`hqb-kpi-${k.k}`}>
        <small>{k.label}</small><b className="m-num">{k.value}</b><em>{k.sub}</em>{k.k === 'visits' ? <Spark rows={d.traffic?.daily} /> : null}</button>)}
    </div>
    {fails.length || nudges.length || failed.length ? <div className="hqb-attn" data-testid="hqb-attn"><b className="m-label">NEEDS YOU</b>
      <ul>{fails.map(c => <li key={c.key || c.label} className="is-bad"><i aria-hidden="true">!</i><span><b>{c.label}</b>{c.detail ? <small>{c.detail}</small> : null}</span></li>)}
        {nudges.slice(0, 4).map((a, i) => <li key={`n${i}`}><i aria-hidden="true">›</i><span>{a.text || a.label || a.title}</span></li>)}
        {failed.map(r => <li key={r} className="is-bad"><i aria-hidden="true">⚠</i><span><b>{r} did not load</b><small>{bad[r]}</small></span></li>)}</ul></div>
      : <p className="hqb-ok" data-testid="hqb-ok">✓ Nothing needs you right now{at ? '' : '…'}</p>}
    <div className="hqb-grid">
      {groups.map(([name, ids, ico, blurb], i) => <article key={name} className="hqb-g" style={{ '--i': i }} data-testid={`hqb-g-${name.toLowerCase()}`}>
        <header><span aria-hidden="true">{ico}</span><div><h4>{name}</h4><p>{blurb}</p></div></header>
        <dl>{groupLines(name, d).map(([k, v]) => <div key={k}><dt>{k}</dt><dd className="m-num">{v}</dd></div>)}</dl>
        <nav aria-label={`${name} tools`}>{ids.map(id => <button key={id} type="button" className="hqb-chip" onClick={() => onGo(id)} data-tip={`Open ${label(id)}`}><span aria-hidden="true">{icon[id] || '•'}</span>{plain(label(id))}</button>)}</nav>
      </article>)}
    </div>
  </section>;
}

// 🎛 HQ looks (owner: "more serious design options"). Ops = the glow deck it always was; Ledger = flat hairlines and mono numbers;
// Boardroom = calm and spacious. Saved per browser; a class on the shell, nothing else changes.
export const HQ_STYLES = [['ops', 'Ops', 'The live deck: glow, depth, motion'], ['ledger', 'Ledger', 'Flat hairlines, mono numbers, no glow'], ['board', 'Boardroom', 'Calm, spacious, quiet colour']];
export function readHqStyle() { try { const v = localStorage.getItem('feeless.hq.style'); return HQ_STYLES.some(s => s[0] === v) ? v : 'ops'; } catch { return 'ops'; } }
export function HqStyleSwitch({ value, onChange }) {
  return <div className="m-seg hqb-style" role="radiogroup" aria-label="HQ look" data-testid="hq-style">
    {HQ_STYLES.map(([k, l, tip]) => <button key={k} type="button" role="radio" aria-checked={value === k} className={value === k ? 'active' : ''} data-tip={tip}
      onClick={() => { try { localStorage.setItem('feeless.hq.style', k); } catch { /* private window: this visit only */ } onChange(k); }}>{l}</button>)}
  </div>;
}
