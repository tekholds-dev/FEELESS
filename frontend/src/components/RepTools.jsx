import React, { useState } from 'react';
import { apiUrl } from '../lib/api';
import { investigate, caseCard } from './CaseFile';
import { VerifyReport } from './VerifyReport';
import { WatchButton } from './WatchButton';
import { ShareGifButton } from './ShareGif';
import '../styles/repPage.css';

// Reputation engine tools: the same cited evidence the whole site uses, pointed wherever you want.
const OK = a => /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(a || '');
const TOOLS = [['case', '🔎 Case file'], ['coin', '✓ Check a coin'], ['compare', '⚖ Compare wallets'], ['watch', '👁 Watch a wallet']];

export function RepTools() {
  const [tool, setTool] = useState('case');
  const [a, setA] = useState(''); const [b, setB] = useState('');
  const [run, setRun] = useState(0);
  const [cmp, setCmp] = useState(null);
  const compare = async () => {
    setCmp('loading');
    const get = x => fetch(apiUrl(`/api/reputation/case/${x}`)).then(r => (r.ok ? r.json() : null)).catch(() => null);
    const [ca, cb] = await Promise.all([get(a), get(b)]); setCmp([ca, cb]);
  };
  const Side = ({ c, addr }) => !c ? <div className="rt-side"><p className="cc-empty">No case for {addr.slice(0, 4)}…</p></div> : <div className={`rt-side lv-${c.level}`}>
    <small>{c.kind === 'coin' ? 'COIN' : 'WALLET'} · {addr.slice(0, 4)}…{addr.slice(-4)}</small><b>{c.score ?? 0}<em>/100</em></b><span>{c.label}</span>
    <ul>{(c.evidence || []).filter(e => e.weight > 0).slice(0, 3).map((e, i) => <li key={i}>{e.claim}<i>{e.source}</i></li>)}{!(c.evidence || []).some(e => e.weight > 0) && <li>No red flags on record.</li>}</ul>
    <div className="rt-row"><button type="button" className="btn-outline" onClick={() => investigate(addr)}>Full case</button><ShareGifButton label="🎞 GIF" card={caseCard(c)} /></div></div>;
  return <section className="rep-tools rep-v2-tools m-live" data-testid="rep-tools"><i className="rt-radar" aria-hidden="true" />
    <div className="rt-head"><div><small>REPUTATION ENGINE · TOOLS</small><h3>Check anyone before you touch them.</h3><p>Every score is cited evidence: launch forensics, the funding graph, the blocklist and trade history.</p></div>
      <div className="bdg-seg">{TOOLS.map(([k, l]) => <button key={k} type="button" className={tool === k ? 'active' : ''} onClick={() => { setTool(k); setRun(0); setCmp(null); }}>{l}</button>)}</div></div>
    <div className="rt-body">
      {tool === 'compare' ? <><div className="rt-row"><input placeholder="Wallet A" value={a} onChange={e => setA(e.target.value.trim())} /><input placeholder="Wallet B" value={b} onChange={e => setB(e.target.value.trim())} /><button type="button" className="btn-primary" disabled={!OK(a) || !OK(b)} onClick={compare}>Compare</button></div>
        {cmp === 'loading' ? <p className="cc-empty">Pulling both case files…</p> : cmp && <div className="rt-cmp"><Side c={cmp[0]} addr={a} /><Side c={cmp[1]} addr={b} /></div>}</>
        : <div className="rt-row"><input placeholder={tool === 'coin' ? 'Coin mint address' : 'Wallet or coin address'} value={a} onChange={e => setA(e.target.value.trim())} />
          {tool === 'case' && <button type="button" className="btn-primary" disabled={!OK(a)} onClick={() => investigate(a)}>Open case file</button>}
          {tool === 'coin' && <button type="button" className="btn-primary" disabled={!OK(a)} onClick={() => setRun(x => x + 1)}>Run checks</button>}
          {tool === 'watch' && OK(a) && <WatchButton target={a} />}</div>}
      {tool === 'coin' && OK(a) && run > 0 && <VerifyReport key={`${a}-${run}`} mint={a} />}
      {tool === 'watch' && <small className="cc-empty">You get an alert on its next buy or sell; dumps by suspect wallets are called out. Buys open a pre-quoted Quick trade.</small>}
    </div>
  </section>;
}
