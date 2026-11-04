import React, { useState } from 'react';
import { FeeBackFlow } from './FeeBack';
import { Tokenomics } from './FeeCommand';
import '../../styles/whitepaper.css';

// 📄 The web edition reads like a product's docs (owner Q03: no text walls): shelves, then one line per chapter, opening to its points. Every word stays here and in the PDF.
const SHELVES = [
  ['start', 'Start', ['Executive Summary', 'The Problem With On-Chain Fees', 'What FEELESS Is', 'What FEELESS Is NOT', 'Conclusion']],
  ['money', '$FEE + Fee-Back', ['The $FEE Ecosystem Asset', '$FEE Tokenomics', 'Fee-Back Architecture', 'How Eligible Fees Are Tracked', 'How FeeCat Makes the Fee-Back Experience Work', 'FeeCat', 'Revenue Model']],
  ['product', 'Product', ['The FEELESS Terminal', 'The Global Ecosystem Globe', 'Trading & Routing Architecture', 'FUSE Cards', 'Runners, Arena and Prime Cards', 'Top-Tier Cards and the Vault', 'Automation and the FUSE Card Contract', 'Community / Trenches']],
  ['data', 'Data + trust', ['Reputation, Bot Shield and Rewards Integrity', 'Market Data Architecture', 'Supported Ecosystems', 'Security Principles', 'Wallet & Transaction Principles', 'Transparency Principles']],
  ['next', 'Roadmap', ['Roadmap', 'Future Development']],
  ['risk', 'Risks', ['Risk Factors', 'Disclosures']],
];
const VISUAL = { '$FEE Tokenomics': () => <Tokenomics compact />, 'Fee-Back Architecture': () => <FeeBackFlow /> };
const ALWAYS_OPEN = new Set(['Risk Factors', 'Disclosures']);

/** A chapter's text → its first sentence and its other sentences, every word kept. */
export function splitChapter(text) {
  const parts = String(text || '').split(/(?<=[.!?])\s+(?=[A-Z$0-9])/);
  return { lead: parts[0] || '', points: parts.slice(1) };
}

/** Which shelf holds a chapter. A new chapter nobody placed still shows, on the first shelf. */
export function shelfOf(title) {
  return (SHELVES.find(s => s[2].includes(title)) || SHELVES[0])[0];
}

function Chapter({ c, i }) {
  const { lead, points } = splitChapter(c.text); const Visual = VISUAL[c.title];
  const body = <><ul className="wpc-points">{points.map(p => <li key={p}>{p}</li>)}</ul>{Visual ? <Visual /> : null}</>;
  const head = <><span className="wpc-n m-num">{String(c.number).padStart(2, '0')}</span><span className="wpc-title"><h2>{c.title}</h2><p>{lead}</p></span></>;
  if (ALWAYS_OPEN.has(c.title)) return <section id={c.id} className="wpc-ch m-glass is-open" style={{ '--i': i }} data-testid={`whitepaper-chapter-${c.number}`}><div className="wpc-head">{head}</div>{body}</section>;
  return <details id={c.id} className="wpc-ch m-glass" style={{ '--i': i }} data-testid={`whitepaper-chapter-${c.number}`}><summary className="wpc-head">{head}<i className="wpc-chev" aria-hidden="true" /></summary>{body}</details>;
}

export function WhitepaperChapters({ chapters = [] }) {
  const [shelf, setShelf] = useState('start');
  const rows = chapters.filter(c => shelfOf(c.title) === shelf);
  return <div className="wpc" data-testid="whitepaper-chapters">
    <div className="m-seg wpc-seg" role="radiogroup" aria-label="Whitepaper sections">{SHELVES.map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={shelf === k} onClick={() => setShelf(k)} data-testid={`wpc-shelf-${k}`}>{l}</button>)}</div>
    {shelf === 'risk' ? null : <p className="wpc-risk m-glass" data-testid="wpc-risk-line"><b>Crypto can lose all its value. This is not financial advice.</b><button type="button" className="m-btn" onClick={() => setShelf('risk')} data-tip="Risk factors and disclosures">Read the risks</button></p>}
    <div key={shelf} className="wpc-list">{rows.map((c, i) => <Chapter key={c.id} c={c} i={i} />)}</div>
  </div>;
}
