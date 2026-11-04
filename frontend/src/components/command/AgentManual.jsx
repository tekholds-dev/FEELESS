import React, { useState } from 'react';
import { KernelCard, PoiMinds } from './PoiFolder';
import '../../styles/agentManual.css';
import { Ic3, Ic3Text } from '../../lib/icon3d';

// 📖 THE MANUAL (owner 2026-11-04: "eye candy, never just hella text"): drawn flows, a step-through tutorial, a trader vs general board, live limits, live fingerprints and a code map.
// Words stay labels. Each claim here matches the engine: change the code, change this file.
const POW_FLOW = [['🗺', 'PLAN', '3 turns in chat'], ['🔎', 'SCOUT', 'Sites + snapshots'], ['⚖', 'CHOOSE', 'Safer numbers win'], ['🛒', 'BUY', 'Its own wallet'], ['👁', 'HOLD', 'Hard exits always'], ['📁', 'FILE', 'Report + 👍 / 👎']];
const POP_FLOW = [['📈', 'CHART', 'Coinbase candles'], ['🛰', 'SOURCES', 'Its own, measured'], ['🕶', 'BLIND CALL', 'No peeking'], ['🤝', 'AGREE', 'Same market + side'], ['📄', 'PAPER', 'True prices'], ['📁', 'FILE', 'Folder + fingerprint']];
const FP_FLOW = [['🌐', 'READ', 'A source'], ['📏', 'MEASURE', 'Against the chart'], ['🔒', 'SEAL', 'Per mind, encrypted'], ['⬆', 'PROMOTE', 'After 4 useful'], ['⬇', 'RETIRE', 'When it stops helping'], ['🔁', 'ROTATE', 'New sources next']];
const num = v => (v == null ? '' : String(v));
const SYSTEM = [
  { lane: 'YOU', tone: 'you', nodes: [
    { k: 'chat', ic: '💬', t: 'Chat', sub: 'Ask anything', say: 'Type in plain words. Your words show at once and the answer lands under them.', cmd: 'what can you do?' },
    { k: 'limits', ic: '🎚', t: 'Limits', sub: 'What it may spend', say: 'The most a task, a trade and a day may spend. A hard exit always runs.', live: d => d?.cap != null && `$${d.cap} a task` },
    { k: 'wallet', ic: '👛', t: 'Wallet', sub: 'Its own money', say: 'Its own wallet pays for its buys and model calls. You can withdraw from the Wallet folder.', live: d => d?.credit != null && `$${Number(d.credit).toFixed(2)} credit` },
  ] },
  { lane: 'ITS WORK', tone: 'minds', nodes: [
    { k: 'minds', ic: '🧠', t: 'Two minds', sub: 'Think apart', say: 'Each mind works alone in its own browser, then they compare. A trade needs both to agree.' },
    { k: 'mail', ic: '📧', t: 'Mail', sub: 'Its own email', say: 'Make its mailbox once. It signs up with it and reads its own codes.', live: d => d?.mailbox?.address && 'Made' },
    { k: 'sites', ic: '🌐', t: 'Sites', sub: 'You sign in once', say: 'Type a site in a proof folder, sign in by hand, save. It scans there and writes a manual. Then it can trade on that account.', cmd: 'buy $1 of $BONK on pump', live: d => (d?.signedIn || []).length ? `${d.signedIn.length} signed in` : '' },
  ] },
  { lane: 'PROOFS', tone: 'proofs', nodes: [
    { k: 'pow', ic: '⛏', t: 'PoW', sub: 'Research + real buy', say: 'It researches coins, buys inside its limits, holds with hard exits, then files a folder. Real SOL from its wallet.', cmd: 'file a PoW', live: d => (d?.powFolders || []).length && `${d.powFolders.length} filed` },
    { k: 'pop', ic: '📉', t: 'PoP', sub: 'Paper perps', say: 'Both minds call a market blind. A paper trade runs on true prices. No real order is sent.', cmd: 'file a perp', live: d => (d?.popFolders || []).length && `${d.popFolders.length} filed` },
    { k: 'pob', ic: '🎲', t: 'PoB', sub: 'Any topic, or chips', say: 'Name a topic. Each mind reads major sites with snapshots and calls it blind. Nothing is staked.', cmd: 'file a pob best NFL picks', live: d => (d?.pobFolders || []).length && `${d.pobFolders.length} filed` },
  ] },
  { lane: 'WHAT IT KEEPS', tone: 'keep', nodes: [
    { k: 'proofs', ic: '🏆', t: 'Proofs folder', sub: 'Everything it filed', say: 'One timeline of every proof, with the decisions and snapshots from that moment.' },
    { k: 'loop', ic: '🪄', t: 'Proof Loop', sub: 'Studies itself first', say: 'Before a new proof it reads its old ones. A coin shaped like a past loss is skipped, and a topic you repeat continues one series.', cmd: 'file a pob lakers parlays' },
    { k: 'fp', ic: '🧬', t: 'Fingerprint', sub: 'What really works', say: 'Sources are measured against results. The useful ones rise, the others retire, sealed per mind.' },
  ] },
];
const START = [['wallet', 'Fund it'], ['mail', 'Make its email'], ['sites', 'Sign in a site'], ['pow', 'File a proof'], ['proofs', 'Read the result']];
const ALL_NODES = SYSTEM.flatMap(l => l.nodes.map(n => ({ ...n, tone: l.tone })));
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
const POB_FLOW = [['💬', 'ASK', 'Any topic'], ['🌐', 'READ', 'Major sites'], ['📸', 'SNAPSHOT', 'One per site'], ['🕶', 'BLIND CALL', 'Each mind alone'], ['🤝', 'AGREE', 'Same picks only'], ['📁', 'FILE', 'You mark it right or wrong']];
const SITE_FLOW = [['🌐', 'TYPE', 'Any site, in a folder'], ['🔓', 'SIGN IN', 'You, by hand'], ['🔎', 'SCAN', 'Terms, fees, help'], ['📖', 'MANUAL', "Its own sentences"], ['⌘', 'COMMAND', 'file a pump pow']];
const FUND_FLOW = [['👛', 'YOUR WALLET', 'Fund the site yourself'], ['💡', 'CHEAPEST', 'One transfer, one fee'], ['📈', 'AGENTS READ', 'Signed in, in its window'], ['🛒', 'THEY TRADE', 'buy $1 of $BONK on pump']];
const MAIL_FLOW = [['📧', 'MAKE IT', 'Mail folder, one click'], ['🔐', 'SEALED', 'Password in the Vault'], ['✍', 'SIGN UP', 'With its own email'], ['🔑', 'READ THE CODE', 'Plain text only']];
const FACTS = {
  sites: [['🛡', 'A bot check goes to you', 'Clear it once and it scans in that same window. A wall it cannot read says NOT READ'], ['📃', 'Every line has a source', 'A model may reword a line, never add one'], ['🖼', 'Snapshots are yours', 'Signed-in pages stay private to you']],
  fund: [['💸', 'Or ask: top up pump $1.50', 'It asks first. Yes, no, or an amount'], ['🧮', '$0.50 to $25 a send', 'From its own wallet, SOL only'], ['🔎', 'Addresses get checked', 'One read from a page needs its last 4 typed']],
  pob: [['🏈', 'file a pob best NFL picks', 'ESPN, NFL, CBS, Action Network, Covers, Kalshi, Polymarket'], ['🎲', 'file a bid', 'Free chips on our own board, graded by its result'], ['⚖', 'It never bets for you', 'Any real bid is yours, where it is legal for you']],
  mail: [['🧩', 'Some sites refuse free mailboxes', 'It tries Tuta or GMX, then asks you'], ['✋', 'Human checks stay human', 'CAPTCHA, phone and ID are always yours']],
};
const TABS = [['tutorial', '🎓 Tutorial'], ['kinds', '🧬 Trader vs General'], ['pow', '⛏ PoW'], ['pop', '📉 PoP'], ['pob', '🎲 PoB'], ['sites', '🌐 Sites'], ['fund', '💸 Funding'], ['mail', '📧 Mail'], ['print', '🖐 Fingerprint'], ['limits', '🧱 Limits'], ['code', '🧩 Code']];

function Flow({ steps, tone = 'pow' }) {
  return <ol className={`am-flow is-${tone}`} data-testid={`am-flow-${tone}`}>{steps.map(([ic, l, s], i) => <li key={l} style={{ '--i': i }} data-tip={s}><i aria-hidden="true"><em><Ic3 e={ic} /></em></i><b>{l}</b><small>{s}</small>{i < steps.length - 1 ? <u aria-hidden="true"><s /></u> : null}</li>)}</ol>;
}
function Facts({ k }) {
  return <ul className="am-facts" data-testid={`am-facts-${k}`}>{FACTS[k].map(([ic, t, x], i) => <li key={t} className="m-glass" style={{ '--i': i }}><Ic3 e={ic} size="44px" /><b>{t}</b><small>{x}</small></li>)}</ul>;
}
function Tutorial({ d, onCommand }) {
  const [at, setAt] = useState('chat'); const n = ALL_NODES.find(x => x.k === at);
  return <section className="am-sys" data-testid="am-tutorial">
    <div className="am-map" role="group" aria-label="How the whole agent system fits together">
      {SYSTEM.map((l, li) => <div key={l.lane} className={`am-lane is-${l.tone}`} style={{ '--i': li }}><h4>{l.lane}</h4>
        {l.nodes.map(x => { const v = x.live?.(d); return <button key={x.k} type="button" className={`am-node${at === x.k ? ' is-on' : ''}`} aria-pressed={at === x.k} onClick={() => setAt(x.k)} data-tip={x.sub} data-testid={`am-node-${x.k}`}><Ic3 e={x.ic} size="42px" /><span><b>{x.t}</b><small>{num(v) && v ? v : x.sub}</small></span></button>; })}
        {li < SYSTEM.length - 1 ? <u className="am-wire" aria-hidden="true"><s /></u> : null}</div>)}
      <div className="am-back" aria-hidden="true"><s /><span><Ic3 e="🪄" size="20px" /> Every proof feeds the next one</span></div></div>
    <aside className={`am-detail is-${n.tone}`} key={n.k} data-testid="am-detail"><i className="am-detail-art"><Ic3 e={n.ic} size="96px" /></i><b>{n.t}</b><em>{n.sub}</em><span className="am-say">{n.say}</span>
      {n.cmd && onCommand ? <button type="button" className="m-btn m-go" onClick={() => onCommand(n.cmd)} data-tip="Puts it in the chat box. You press send" data-testid="am-try">Put “{n.cmd}” in chat</button> : n.cmd ? <code>{n.cmd}</code> : null}</aside>
    <ol className="am-start" aria-label="Where to start">{START.map(([k, l], i) => <li key={k} style={{ '--i': i }}><button type="button" className={at === k ? 'is-on' : ''} onClick={() => setAt(k)} data-testid={`am-start-${k}`}><em className="m-num">{i + 1}</em>{l}</button></li>)}</ol>
  </section>;
}
function Kinds() {
  return <section className="am-kinds m-glass" data-testid="am-kinds"><header><span /><b>🏇 TRADER</b><b><Ic3 e="🧭" /> GENERAL</b></header>
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
    <div className="am-tabs m-seg" role="tablist" aria-label="Manual">{TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`am-tab-${k}`}><Ic3Text text={l} /></button>)}</div>
    <div key={tab} className="am-pane">
      {tab === 'tutorial' ? <><button type="button" className="m-btn m-go am-replay" onClick={() => window.dispatchEvent(new Event('feeless:desk-tour'))} data-tip="Walks through the real folders on this desktop, 12 steps" data-testid="am-tour"><Ic3 e="🎓" /> Play the desktop tour</button><Tutorial d={d} onCommand={onCommand} /></> : null}
      {tab === 'kinds' ? <Kinds /> : null}
      {tab === 'pow' ? <Flow steps={POW_FLOW} /> : null}
      {tab === 'pop' ? <Flow steps={POP_FLOW} tone="pop" /> : null}
      {tab === 'pob' ? <><Flow steps={POB_FLOW} tone="pop" /><Facts k="pob" /></> : null}
      {tab === 'sites' ? <><Flow steps={SITE_FLOW} /><Facts k="sites" /></> : null}
      {tab === 'fund' ? <><Flow steps={FUND_FLOW} tone="print" /><Facts k="fund" /></> : null}
      {tab === 'mail' ? <><Flow steps={MAIL_FLOW} /><Facts k="mail" /></> : null}
      {tab === 'print' ? <><Flow steps={FP_FLOW} tone="print" /><div className="am-prints"><section><b><Ic3 e="⛏" /> PoW</b>{d?.poi?.minds ? <PoiMinds poi={d.poi} /> : <div className="am-empty">No fingerprint read.</div>}</section><section><b><Ic3 e="📉" /> PoP</b>{d?.popPoi?.minds ? <PoiMinds poi={d.popPoi} /> : <div className="am-empty">Files on its first proof.</div>}</section></div></> : null}
      {tab === 'limits' ? <LiveLimits kernel={d?.kernel} /> : null}
      {tab === 'code' ? <CodeMap /> : null}
    </div></div>;
}
