import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis } from 'recharts';
import { Ic3 } from '../../lib/icon3d';
import { ProofHead, ProofKit, ProofTile } from './ProofKit';
import { scoreOf } from '../../lib/proofprint';
import { EcoDesk } from './EcoDesk';
import '../../styles/ecoFolder.css';

// 📊 PoEco (owner 2026-11-05): a business's books as a proof. Python does the math; the rows stay sealed; a receipt carries totals and a hash, never a row.
const usd = v => (v == null ? '—' : `${v < 0 ? '−' : ''}$${Math.abs(v) >= 1000 ? `${(Math.abs(v) / 1000).toFixed(1)}K` : Math.abs(v).toFixed(2)}`);
const mark = g => scoreOf({ kind: 'poe', value: g === 'right' ? 1 : g === 'wrong' ? -1 : null });
function Book({ f, work, cat, onRows, onBack, onCommand }) {
  const [said, setSaid] = useState(''); const [err, setErr] = useState('');
  const act = async (body, done) => { setErr(''); try { const j = await work(cat.id, body); if (j.poeFolders) onRows(j.poeFolders); if (done) done(j); } catch (e) { setErr(e.message); } };
  const send = () => act({ op: 'eco_send', job: f.id }, j => { const url = URL.createObjectURL(new Blob([JSON.stringify(j.receipt, null, 1)], { type: 'application/json' })); const a = document.createElement('a'); a.href = url; a.download = `poeco-${f.n}-receipt.json`; a.click(); URL.revokeObjectURL(url); setSaid('Receipt saved. It has totals and a hash, no entries.'); });
  const top = Math.max(1, ...(f.cats || []).map(c => c.usd));
  return <div className="eco-book" data-testid={`eco-book-${f.id}`}><header className="eco-bh"><button type="button" className="m-btn" onClick={onBack} data-testid="eco-back">← PoEco</button><b>PoEco #{f.n} · {f.topic}</b><span className="eco-bacts"><button type="button" className={`m-btn${f.graded === 'right' ? ' is-on' : ''}`} aria-pressed={f.graded === 'right'} onClick={() => act({ op: 'eco_mark', job: f.id, text: 'right' })} data-tip="These books match your records. Your mark draws its line on the print" data-testid="eco-right">👍 Correct</button><button type="button" className={`m-btn${f.graded === 'wrong' ? ' is-on' : ''}`} aria-pressed={f.graded === 'wrong'} onClick={() => act({ op: 'eco_mark', job: f.id, text: 'wrong' })} data-tip="Something does not match your records" data-testid="eco-wrong">👎 Off</button><button type="button" className="m-btn m-go" onClick={send} data-tip="Saves a receipt to send: totals and a hash, never an entry" data-testid="eco-send">Send proof</button></span></header>
    <div className="eco-kpis">{[['INCOME', usd(f.income), ''], ['COSTS', usd(f.costs), ''], ['NET', usd(f.net), f.net >= 0 ? 'is-up' : 'is-dn'], ['MARGIN', f.margin == null ? '—' : `${f.margin}%`, ''], [`SET ASIDE ${f.taxPct}%`, usd(f.taxSetAside), ''], ['COSTS A MONTH', usd(f.burnPerMonth), '']].map(([k, v, c]) => <span key={k}><small>{k}</small><b className={`m-num ${c}`}>{v}</b></span>)}</div>
    <div className="eco-two"><section className="eco-chart" aria-label="Income and costs by month"><h4>BY MONTH</h4><ResponsiveContainer width="100%" height={190}><BarChart data={f.months || []} barGap={2}><XAxis dataKey="month" tick={{ fill: '#9fb2c8', fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip cursor={{ fill: '#ffffff0a' }} contentStyle={{ background: '#0b1410', border: '1px solid #ffffff24', borderRadius: 8, fontSize: 12 }} formatter={v => usd(v)} /><Bar dataKey="income" name="Income" fill="#3ee58a" radius={[4, 4, 0, 0]} /><Bar dataKey="costs" name="Costs" fill="#ff8fa3" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></section>
      <section className="eco-cats" aria-label="Where the money goes"><h4>WHERE IT GOES</h4><ul>{(f.cats || []).map(c => <li key={c.cat}><span>{c.cat}</span><i aria-hidden="true"><u style={{ transform: `scaleX(${c.usd / top})` }} /></i><b className="m-num">{usd(c.usd)}</b></li>)}</ul></section></div>
    <p className="eco-hash" data-tip="The same entries always give this hash"><small>PROOF</small><code data-testid="eco-hash">{f.hash}</code></p>
    {onCommand ? <button type="button" className="m-btn" onClick={() => onCommand(`Read these books and tell me the one thing to change: income ${usd(f.income)}, costs ${usd(f.costs)}, net ${usd(f.net)}, biggest costs ${(f.cats || []).slice(0, 3).map(c => `${c.cat} ${usd(c.usd)}`).join(', ')}.`)} data-tip="Puts the totals in its chat box. You press send" data-testid="eco-ask">Ask its minds</button> : null}
    {said ? <small className="git-said" role="status">{said}</small> : null}{err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}</div>;
}
// The folder opens on the desk. Its filed proofs and their print sit under Proofs: a proof is made from the books, so there is one set of entries, never two.
function Proofs({ rows, cat, d, pool, work, onBrowse, onRows, onCommand, tool }) {
  const [open, setOpen] = useState(null); const [name, setName] = useState(''); const [said, setSaid] = useState('');
  useEffect(() => { if (open) setOpen(o => rows.find(f => f.id === o.id) || o); }, [rows]);   // eslint-disable-line react-hooks/exhaustive-deps
  const prove = async e => { e.preventDefault(); const j = await tool.prove(name.trim() || 'All books'); if (j) { setName(''); setSaid('Filed. It holds totals and a hash, never an entry.'); } };
  return <div className="prf" data-testid="dsk-poe"><ProofHead kind="poe" folders={rows} d={d} cat={cat} pool={pool} work={work} onBrowse={onBrowse} /><div className="prf-main">
    {open ? <Book f={open} work={work} cat={cat} onRows={onRows} onBack={() => setOpen(null)} onCommand={onCommand} /> : <>
      {rows.length ? <div className="dsk-xgrid" data-testid="eco-tiles">{rows.map((f, i) => <ProofTile key={f.id} i={i} ic="📊" tone={f.graded === 'right' ? 'good' : f.graded === 'wrong' ? 'bad' : 'none'} print={[f.id, mark(f.graded)]} label={`PoEco #${f.n}`} sub={usd(f.net)} tip={f.topic} onOpen={() => setOpen(f)} testid={`eco-${f.id}`} />)}</div> : null}
      <form className="eco-new m-card" onSubmit={prove}><h4><Ic3 e="📊" /> PROVE MY BOOKS</h4><div className="eco-row"><input className="m-input" maxLength={60} value={name} onChange={e => setName(e.target.value)} placeholder="Name, like Q3 books" aria-label="Name of this proof" data-testid="eco-name" /><button type="submit" className="m-btn m-go" disabled={tool.busy || !tool.count} data-tip={tool.count ? 'Files your real entries as a proof you can send' : 'Add real entries first. Made-up examples never count'} data-testid="eco-file">File {tool.count} entries</button><small>Python does the sums and the entries stay sealed. A proof holds totals and a hash you can send.</small></div>
        {said ? <small className="git-said" role="status" data-testid="eco-proved">{said}</small> : null}</form></>}
  </div><aside className="prf-rail"><ProofKit kind="poe" folders={rows} onCommand={onCommand} /></aside></div>;
}
export function EcoFolder({ cat, d, setD, work, pool, onCommand, onBrowse }) {
  const rows = useMemo(() => d?.poeFolders || [], [d?.poeFolders]);
  const onRows = useCallback(poeFolders => setD?.(x => ({ ...x, poeFolders })), [setD]);
  return <EcoDesk cat={cat} work={work} onCommand={onCommand} onRows={onRows} proofs={tool => <Proofs rows={rows} cat={cat} d={d} pool={pool} work={work} onBrowse={onBrowse} onRows={onRows} onCommand={onCommand} tool={tool} />} />;
}
