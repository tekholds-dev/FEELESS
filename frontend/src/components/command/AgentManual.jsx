import React, { useState } from 'react';
import { KernelCard, PoiMinds } from './PoiFolder';
import '../../styles/agentManual.css';

// 📖 THE MANUAL (owner 2026-11-04: "eye candy, never just hella text"): drawn flows, a step-through tutorial, a trader vs general board, live limits, live fingerprints and a code map.
// Words stay labels. Each claim here matches the engine: change the code, change this file.
const POW_FLOW = [['🗺', 'PLAN', '3 turns in chat'], ['🔎', 'SCOUT', 'Sites + snapshots'], ['⚖', 'CHOOSE', 'Safer numbers win'], ['🛒', 'BUY', 'Its own wallet'], ['👁', 'HOLD', 'Hard exits always'], ['📁', 'FILE', 'Report + 👍 / 👎']];
const POP_FLOW = [['📈', 'CHART', 'Coinbase candles'], ['🛰', 'SOURCES', 'Its own, measured'], ['🕶', 'BLIND CALL', 'No peeking'], ['🤝', 'AGREE', 'Same market + side'], ['📄', 'PAPER', 'True prices'], ['📁', 'FILE', 'Folder + fingerprint']];
const FP_FLOW = [['🌐', 'READ', 'A source'], ['📏', 'MEASURE', 'Against the chart'], ['🔒', 'SEAL', 'Per mind, encrypted'], ['⬆', 'PROMOTE', 'After 4 useful'], ['⬇', 'RETIRE', 'When it stops helping'], ['🔁', 'ROTATE', 'New sources next']];
const STEPS = [
  { t: 'Open its desktop', sub: 'Every tool is a folder', hot: 'vault', tip: 'Press Private desktop on its desk' },
  { t: 'Fund its wallet', sub: 'It trades from its own', hot: 'wallet', tip: 'Add SOL on its desk. Open Wallet to see it' },
  { t: 'File a PoW', sub: 'Research → buy → hold → file', hot: 'pow', cmd: 'file a PoW', tip: 'Spends real SOL from its wallet, inside its limits' },
  { t: 'File a perp', sub: 'A paper trade on true prices', hot: 'pop', cmd: 'file a perp', tip: 'Two small paid model calls. No real order is sent' },
  { t: 'Propose a perp', sub: 'A card: you Run or Pass', hot: 'pop', cmd: 'propose a perp', tip: 'Nothing opens until you press Run. To trade for real, place it yourself on Crypto.com' },
  { t: 'Read the folder', sub: 'Report · sources · fingerprint', hot: 'pop', tip: 'Every proof files a dated folder you can keep or delete' },
];
const MINI = [['vault', 'Vault'], ['pow', 'PoW'], ['pop', 'PoP'], ['wallet', 'Wallet']];
const KINDS = [ // [what, trader, general] : 2 = on its own, 1 = when you ask, 0 = no
  ['Private desktop + folders', 2, 2], ['Vault + signed-in sites', 2, 2], ['Own wallet', 2, 2], ['Two minds + commands', 2, 2],
  ['PoW research + buy', 2, 1], ['PoP paper perps', 1, 1], ['Buys inside its limits', 2, 1], ['Hard exits on its trades', 2, 2],
  ['Browse any site', 0, 2], ['Coin + narrative research', 2, 2], ['Colony + honey', 2, 0], ['Job cards + hourly brief', 0, 2],
];
const LEVEL = [['none', 'No'], ['ask', 'When you ask'], ['auto', 'On its own']];
const CODE = [
  ['Rules the models can’t change', [['pow_kernel.py', 'Every hard limit, hash pinned'], ['pow.py', 'PoW phases and budgets'], ['pop.py', 'Agreement, exits, reports']]],
  ['What they read', [['pop_sources.py', 'Perps sources, measured'], ['cat_agent.py', 'Browser windows'], ['candles_service.py', 'True candles + fills']]],
  ['What they remember', [['poi.py', 'Sealed fingerprints'], ['colony.py', 'Colony + honey'], ['hive.py', 'Graded calls']]],
  ['What moves money', [['agent_trade.py', 'Guards, one in flight'], ['cat_real.py', 'Proposals'], ['agent_wallet.py', 'Its own wallet']]],
];
const TABS = [['tutorial', '🎓 Tutorial'], ['kinds', '🧬 Trader vs General'], ['pow', '⛏ PoW'], ['pop', '📉 PoP'], ['print', '🖐 Fingerprint'], ['limits', '🧱 Limits'], ['code', '🧩 Code']];

function Flow({ steps, tone = 'pow' }) {
  return <ol className={`am-flow is-${tone}`} data-testid={`am-flow-${tone}`}>{steps.map(([ic, l, s], i) => <li key={l} style={{ '--i': i }} data-tip={s}><i aria-hidden="true"><em>{ic}</em></i><b>{l}</b><small>{s}</small>{i < steps.length - 1 ? <u aria-hidden="true"><s /></u> : null}</li>)}</ol>;
}
function Tutorial({ onCommand }) {
  const [at, setAt] = useState(0); const s = STEPS[at];
  return <section className="am-tut" data-testid="am-tutorial">
    <div className="am-mini m-glass" aria-hidden="true"><span className="am-mini-wall">FEELESS</span>{MINI.map(([k, l]) => <span key={k} className={`am-mini-f is-${k}${s.hot === k ? ' is-hot' : ''}`}><i /><small>{l}</small></span>)}<span className="am-mini-bar"><i />{s.cmd ? <code key={s.cmd}>{s.cmd}<u /></code> : null}</span></div>
    <div className="am-step" key={at}><em className="m-num">{at + 1}/{STEPS.length}</em><b>{s.t}</b><small>{s.sub}</small>
      {s.cmd && onCommand ? <button type="button" className="m-btn m-go" onClick={() => onCommand(s.cmd)} data-tip={`${s.tip}. Puts it in the chat box; you press send`} data-testid="am-try">Put “{s.cmd}” in chat</button> : <small className="am-hint">{s.tip}</small>}</div>
    <div className="am-dots" role="group" aria-label="Tutorial step">{STEPS.map((x, i) => <button key={x.t} type="button" className={i === at ? 'is-on' : i < at ? 'is-done' : ''} aria-label={`Step ${i + 1}: ${x.t}`} aria-current={i === at} onClick={() => setAt(i)} data-tip={x.t} />)}</div>
    <div className="am-nav"><button type="button" className="m-btn" disabled={!at} onClick={() => setAt(at - 1)} data-tip="Previous step">← Back</button><button type="button" className="m-btn" disabled={at === STEPS.length - 1} onClick={() => setAt(at + 1)} data-tip="Next step" data-testid="am-next">Next →</button></div>
  </section>;
}
function Kinds() {
  return <section className="am-kinds m-glass" data-testid="am-kinds"><header><span /><b>🏇 TRADER</b><b>🧭 GENERAL</b></header>
    {KINDS.map(([w, t, g], i) => <div key={w} style={{ '--i': i }}><span>{w}</span>{[t, g].map((v, k) => <i key={k} className={`am-lv is-${LEVEL[v][0]}`} data-tip={LEVEL[v][1]} aria-label={LEVEL[v][1]} />)}</div>)}
    <footer>{LEVEL.slice().reverse().map(([k, l]) => <span key={k}><i className={`am-lv is-${k}`} aria-hidden="true" />{l}</span>)}</footer></section>;
}
function LiveLimits({ kernel }) {
  if (!kernel) return <div className="am-empty">Limits load with its state.</div>;
  return <div className="am-limits" data-testid="am-limits"><KernelCard kernel={kernel} />
    <div className="am-tiles">{kernel.groups.flatMap(g => g.rows.slice(0, 4).map(([k, v]) => <span key={`${g.name}${k}`} className="m-glass"><small>{k}</small><b className="m-num">{Array.isArray(v) ? v.join(' – ') : String(v)}</b><em>{g.name}</em></span>))}</div></div>;
}
function CodeMap() {
  return <div className="am-code" data-testid="am-code">{CODE.map(([layer, files], n) => <section key={layer} className={`m-glass is-l${n}`} style={{ '--i': n }}><b>{layer}</b>{files.map(([f, w]) => <span key={f} data-tip={w}><code>{f}</code><small>{w}</small></span>)}</section>)}</div>;
}

export function AgentManual({ d, onCommand }) {
  const [tab, setTab] = useState('tutorial');
  return <div className="am" data-testid="dsk-manual">
    <div className="am-tabs m-seg" role="tablist" aria-label="Manual">{TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`am-tab-${k}`}>{l}</button>)}</div>
    <div key={tab} className="am-pane">
      {tab === 'tutorial' ? <Tutorial onCommand={onCommand} /> : null}
      {tab === 'kinds' ? <Kinds /> : null}
      {tab === 'pow' ? <Flow steps={POW_FLOW} /> : null}
      {tab === 'pop' ? <Flow steps={POP_FLOW} tone="pop" /> : null}
      {tab === 'print' ? <><Flow steps={FP_FLOW} tone="print" /><div className="am-prints"><section><b>⛏ PoW</b>{d?.poi?.minds ? <PoiMinds poi={d.poi} /> : <div className="am-empty">No fingerprint read.</div>}</section><section><b>📉 PoP</b>{d?.popPoi?.minds ? <PoiMinds poi={d.popPoi} /> : <div className="am-empty">Files on its first proof.</div>}</section></div></> : null}
      {tab === 'limits' ? <LiveLimits kernel={d?.kernel} /> : null}
      {tab === 'code' ? <CodeMap /> : null}
    </div></div>;
}
