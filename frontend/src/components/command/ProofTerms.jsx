import React, { useState } from 'react';
import { Ic3 } from '../../lib/icon3d';
import { OTHER_TERMS, PROOF_IS, TERMS } from '../../lib/proofTerms';
import '../../styles/boosts.css';

// 📖 One explainer for every proof word: the same cards in the Manual and on top of the Proofs folder.
export function ProofTerms({ compact = false }) {
  const [more, setMore] = useState(!compact);
  return <section className={`trm${compact ? ' is-compact' : ''}`} data-testid="proof-terms"><p className="trm-is"><b>What is a proof?</b> {PROOF_IS}</p>
    <div className="trm-cards">{TERMS.map((t, i) => <article key={t.k} style={{ '--i': i }} className={`trm-card is-${t.k}`} data-tip={`Try it: ${t.ex}`} data-testid={`term-${t.k}`}><header><Ic3 e={t.ic} size="26px" /><span><b>{t.code}</b><small>{t.name}</small></span></header><strong>{t.what}</strong><p>{t.says}</p><em>{t.real}</em></article>)}</div>
    {compact ? <button type="button" className="m-btn trm-more" aria-expanded={more} onClick={() => setMore(x => !x)} data-testid="terms-more">{more ? 'Fewer words' : 'More words explained'}</button> : null}
    {more ? <dl className="trm-words">{OTHER_TERMS.map(t => <div key={t.term}><dt><Ic3 e={t.ic} size="16px" /> {t.term}</dt><dd>{t.says}</dd></div>)}</dl> : null}</section>;
}
