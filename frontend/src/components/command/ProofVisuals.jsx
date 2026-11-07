import React from 'react';
import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, Tooltip } from 'recharts';
import '../../styles/proofVisuals.css';

// 🧬 A proof's score as a radar (Recharts): each thing it was scored on is a spoke, and what is not known stays at zero.
const TONE = { good: '#15d16a', bad: '#ff8fa3', open: '#e7c36a' };
export function ProofSeal({ parts, rank, tone, size = 190 }) {
  const rows = (parts || []).slice(0, 8).map(p => ({ part: p.label, value: p.value == null ? 0 : Math.round(Number(p.value) * 100), known: p.value != null })); const c = TONE[tone] || TONE.open;
  return <span className="pvz-seal" data-testid="pvz-seal" role="img" aria-label={`Rank ${rank}. ${rows.map(r => `${r.part} ${r.known ? r.value : 'not known'}`).join(', ')}`}><RadarChart width={size} height={size} data={rows} outerRadius="66%"><PolarGrid stroke="#ffffff22" /><PolarAngleAxis dataKey="part" tick={{ fill: '#a9bdb2', fontSize: 8 }} /><PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} /><Tooltip contentStyle={{ background: '#07110c', border: `1px solid ${c}`, borderRadius: 8, fontSize: 11 }} /><Radar dataKey="value" stroke={c} fill={c} fillOpacity={0.32} isAnimationActive={!document.body.classList.contains('fx-lite')} animationDuration={500} /></RadarChart><b>{rank}</b></span>;
}
