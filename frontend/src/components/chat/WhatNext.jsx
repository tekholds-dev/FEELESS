import React from 'react';
// 🧭 WHAT NEXT (owner 2026-11-12: "they ask which should they do next like you do, with options or input a different one"): every chat offers the
// next step after a reply. When the reply itself lists choices (1. … / - … after its last question), those ARE the options; otherwise steps that fit
// where the work is, plus (proof chats) one tap that carries the answer into the next proof. "Something else…" goes to the box. One component, every chat.
export function nextOptions(last, { page = 0, kinds = [] } = {}) {
  const t = String(last?.text || ''); if (!t || last?.by === 'you' || last?.role === 'user') return [];
  const q = t.lastIndexOf('?'); const tail = q >= 0 ? t.slice(q + 1) : '';
  const own = tail.split('\n').map(x => x.match(/^\s*(?:\d+[.)]|[-•*])\s+(.{3,90}?)\s*$/)?.[1]).filter(Boolean).slice(0, 4);
  if (own.length >= 2) return own.map(x => ({ label: x.replace(/\*\*/g, ''), say: x.replace(/\*\*/g, '') }));
  const out = page ? [{ label: 'Make it great on a phone', say: 'Make this page work beautifully on a 360 px phone.' }, { label: 'Add a live chart of real data', say: 'Add one live chart fed by real data, with its source named.' }, { label: 'Sharper headline and copy', say: 'Tighten the headline and the copy: shorter, clearer, more confident.' }]
    : [{ label: 'Go deeper', say: 'Go deeper on that: what would make it twice as good?' }, { label: 'What could go wrong?', say: 'What could go wrong with this, and how do we guard against it?' }, { label: 'Build it', say: 'Build it.' }];
  return [...out, ...kinds.slice(0, 1).map(k => ({ label: `Carry it into a ${k[1]}`, sendTo: k[0] }))];
}
export function WhatNext({ opts, onPick, onOther, testid = 'ws-next' }) {
  if (!opts?.length) return null;
  return <div className="wn" role="group" aria-label="What next" data-testid={testid}><small className="m-label">WHAT NEXT?</small>{opts.map((o, i) => <button key={o.label} type="button" className="m-chip" style={{ '--i': i }} onClick={() => onPick(o)} data-tip={o.sendTo ? 'Carries this answer into that proof, ready for you to send' : `Sends: ${o.say}`} data-testid={`${testid}-${i}`}>{o.label}</button>)}<button type="button" className="m-chip is-other" onClick={onOther} data-tip="Type your own next step" data-testid={`${testid}-other`}>Something else…</button></div>;
}
