import React, { useMemo, useState } from 'react';
import { CHECKED, LENSES, PAY_OPTIONS, TYPES, fit } from '../../lib/payOptions';
import '../../styles/payGrid.css';

// 💳 HQ › Money › Cards & pay: every card, card API and on-ramp worth testing, side by side, ranked for what you pick (testing, small customers,
// wide scale). Links only: FEELESS signs up for nothing and sends nothing to any of them. Pick up to 3 to compare cell by cell.
const US = { yes: ['US', 'is-ok'], partly: ['Partly', 'is-mid'], check: ['Check', 'is-ask'], no: ['Not US', 'is-no'] };
const KYC = { none: ['No ID', 'is-ok'], light: ['Light ID', 'is-ok'], id: ['ID', 'is-mid'], kyb: ['KYB', 'is-mid'] };
const TEST = { sandbox: ['Sandbox', 'is-ok'], check: ['Check', 'is-ask'], none: ['None', 'is-no'] };
const TYPE_WORD = { person: 'CARD', issuing: 'API', ramp: 'RAMP' };
const FILTERS = [['us', 'Works in the US', r => r.us === 'yes' || r.us === 'partly'], ['sol', 'Solana USDC', r => /solana/i.test(r.funding) && /usdc/i.test(r.funding)], ['sandbox', 'Has a sandbox', r => r.test === 'sandbox'], ['noid', 'No ID to start', r => r.kyc === 'none' || r.kyc === 'light'], ['api', 'Has an API', r => r.api]];
const Cell = ({ k, v, tone, tip }) => <span className={`pg-cell ${tone || ''}`} data-tip={tip}><small>{k}</small><b>{v}</b></span>;
function Ring({ v }) { const r = 15; const c = 2 * Math.PI * r; return <svg className="pg-ring" viewBox="0 0 40 40" aria-label={`fit ${v} of 10`}><circle cx="20" cy="20" r={r} /><circle cx="20" cy="20" r={r} className="is-on" style={{ strokeDasharray: c, strokeDashoffset: c * (1 - v / 10) }} /><text x="20" y="24">{v}</text></svg>; }
export function PayGrid() {
  const [type, setType] = useState('all'); const [lens, setLens] = useState('test'); const [on, setOn] = useState([]); const [q, setQ] = useState(''); const [cmp, setCmp] = useState([]);
  const rows = useMemo(() => PAY_OPTIONS.filter(r => (type === 'all' || r.type === type) && on.every(f => FILTERS.find(x => x[0] === f)[2](r)) && (!q.trim() || `${r.name} ${r.funding} ${r.note}`.toLowerCase().includes(q.trim().toLowerCase())))
    .map(r => ({ ...r, score: fit(r, lens) })).sort((a, b) => b.score - a.score), [type, lens, on, q]);
  const pick = k => setCmp(c => (c.includes(k) ? c.filter(x => x !== k) : [...c, k].slice(-3)));
  const picked = cmp.map(k => PAY_OPTIONS.find(r => r.k === k)).filter(Boolean);
  return <section className="pg" data-testid="pay-grid">
    <header className="pg-h m-live"><span><em>CARDS · CARD APIS · RAMPS</em><b>Pick the best ways to pay, for testing and for customers</b><small>{PAY_OPTIONS.length} options read {CHECKED} from vendor pages and reviews, never full terms. "Check" means sources disagreed. Links only: nothing signs up and no money moves from here.</small></span>
      <span className="pg-count"><b className="m-num">{rows.length}</b><small>shown</small></span></header>
    <div className="pg-bar">
      <span className="m-seg" role="tablist" aria-label="Kind">{TYPES.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={type === k} className={type === k ? 'active' : ''} onClick={() => setType(k)} data-testid={`pg-type-${k}`}>{l}</button>)}</span>
      <span className="m-seg" role="radiogroup" aria-label="Rank for">{LENSES.map(([k, l, tip]) => <button key={k} type="button" role="radio" aria-checked={lens === k} className={lens === k ? 'active' : ''} onClick={() => setLens(k)} data-tip={`Ranks by: ${tip}`} data-testid={`pg-lens-${k}`}>{l}</button>)}</span>
      <input className="m-input pg-q" value={q} onChange={e => setQ(e.target.value)} placeholder="Search: USDC, sandbox, Visa…" aria-label="Search options" data-testid="pg-q" />
    </div>
    <div className="pg-filters">{FILTERS.map(([k, l]) => <button key={k} type="button" className={`m-chip${on.includes(k) ? ' is-on' : ''}`} aria-pressed={on.includes(k)} onClick={() => setOn(o => (o.includes(k) ? o.filter(x => x !== k) : [...o, k]))} data-testid={`pg-f-${k}`}>{on.includes(k) ? '✓ ' : ''}{l}</button>)}</div>
    {picked.length ? <div className="pg-cmp" data-testid="pg-compare"><table><thead><tr><th>Compare</th>{picked.map(r => <th key={r.k}>{r.name}<button type="button" onClick={() => pick(r.k)} aria-label={`Take ${r.name} out`}>✕</button></th>)}</tr></thead>
      <tbody>{[['Fit', r => fit(r, lens)], ['Funding', r => r.funding], ['US', r => r.usWord], ['ID', r => KYC[r.kyc][0]], ['Fees', r => r.fee], ['Test', r => r.testWord || TEST[r.test][0]], ['API', r => (r.api ? 'Yes' : 'No')]].map(([l, f]) => <tr key={l}><th>{l}</th>{picked.map(r => <td key={r.k}>{f(r)}</td>)}</tr>)}</tbody></table></div> : null}
    {rows.length ? <ul className="pg-grid">{rows.map((r, i) => <li key={r.k} className={`pg-card is-${r.type}${cmp.includes(r.k) ? ' is-picked' : ''}`} style={{ '--i': Math.min(i, 12) }} data-testid={`pg-card-${r.k}`}>
      <header><span><em>{TYPE_WORD[r.type]}</em><b>{r.name}</b><small>{r.funding}</small></span><Ring v={r.score} /></header>
      <div className="pg-cells"><Cell k="US" v={US[r.us][0]} tone={US[r.us][1]} tip={r.usWord} /><Cell k="ID" v={KYC[r.kyc][0]} tone={KYC[r.kyc][1]} /><Cell k="TEST" v={TEST[r.test][0]} tone={TEST[r.test][1]} tip={r.testWord} /><Cell k="API" v={r.api ? 'Yes' : 'No'} tone={r.api ? 'is-ok' : 'is-no'} /></div>
      <p className="pg-fee"><small>FEES</small>{r.fee}</p><p className="pg-note">{r.note}</p>
      <footer>{r.wired ? <span className="pg-tag is-in" data-tip="Already listed for agents under Bids › Get a digital card">In FEELESS</span> : null}{r.keys ? <span className="pg-tag" data-tip={`Waiting on your account: ${r.keys} on the keys list`}>Keys list · {r.keys}</span> : null}
        <span className="pg-src">{r.src.map((u, j) => <a key={u} href={u} target="_blank" rel="noopener noreferrer" data-tip={`Where this row came from: ${u.split('/')[2]}`}>{j + 1}</a>)}</span>
        <button type="button" className={`m-btn${cmp.includes(r.k) ? ' is-on' : ''}`} aria-pressed={cmp.includes(r.k)} onClick={() => pick(r.k)} data-tip="Compare up to 3 side by side" data-testid={`pg-cmp-${r.k}`}>{cmp.includes(r.k) ? '✓ Comparing' : 'Compare'}</button>
        <a className="m-btn m-go" href={r.url} target="_blank" rel="noopener noreferrer" data-tip={`Opens ${r.name} in a new tab. You sign up there yourself`}>Open ↗</a></footer></li>)}</ul>
      : <p className="pg-none">Nothing matches all of those. Take a filter off.</p>}
  </section>;
}
