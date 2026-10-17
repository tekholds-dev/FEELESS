import React from 'react';
import { RULES } from '../../lib/ruleLegend';
import '../../styles/ruleLegend.css';

// 📖 one fold: every rule code, plain words, HARD / SOFT, and a tap that jumps to the control that tweaks it (🎛 Limits)
export function RuleLegend({ onTweak }) {
  return <details className="rlg" data-testid="rule-legend"><summary>📖 What R1 · R5 · R7 … mean (tap one to tweak it)</summary>
    <ul>{RULES.map(([k, w, kind, ctl]) => <li key={k} className={`is-${kind}`}><b>{k}</b><span>{w}</span><em>{kind === 'hard' ? 'ALWAYS SELLS' : kind === 'soft' ? 'CAN BE OVERRULED' : 'INFO'}</em>
      {ctl && onTweak ? <button type="button" className="m-btn" onClick={() => onTweak(ctl)} data-testid={`rlg-${k}`}>tweak</button> : <i>{ctl ? `🎛 Limits` : 'fixed'}</i>}</li>)}</ul></details>;
}
