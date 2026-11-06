import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Handle, Position, ReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Ic3 } from '../../lib/icon3d';
import { usd as money } from './KeepDeal';
import '../../styles/stakeFlow.css';

// 🗺 WHERE A STAKE GOES, on the same numbers as the rules. Two roads meet at the seat: the grade sets how big it is, and only a real pool profit puts money through it.
function StakeNode({ data }) {
  const v = data.vertical;
  return <div className={`skf-n is-${data.tone}`} data-tip={data.tip} data-testid={`stake-node-${data.id}`}>
    <Handle type="target" position={v ? Position.Top : Position.Left} isConnectable={false} /><Ic3 e={data.icon} size="26px" /><span><small>{data.label}</small><b className="m-num">{data.value}</b></span>
    {data.part != null ? <i aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.03, Math.min(1, data.part))})` }} /></i> : null}<Handle type="source" position={v ? Position.Bottom : Position.Right} isConnectable={false} /></div>;
}
const NODE_TYPES = { stake: StakeNode };
const WIDE = { proof: [0, 150], checks: [230, 0], boost: [460, 0], points: [690, 0], seat: [690, 125], cash: [930, 62], pools: [230, 250], profit: [460, 250], house: [690, 250], rest: [690, 375] };
const TALL = { proof: [110, 0], checks: [0, 115], pools: [220, 115], boost: [0, 230], profit: [220, 230], points: [0, 345], seat: [110, 460], house: [220, 345], rest: [220, 575], cash: [0, 575] };
const LINKS = [['proof', 'checks', 'gold'], ['checks', 'boost', 'gold'], ['boost', 'points', 'gold'], ['boost', 'seat', 'gold'], ['points', 'cash', 'gold', 'its limit'], ['proof', 'pools', 'blue'], ['pools', 'profit', 'blue'], ['profit', 'seat', 'green', 'only real profit'], ['seat', 'cash', 'green'], ['profit', 'house', 'blue'], ['profit', 'rest', 'blue']];
const NODE_W = 186; const NODE_H = 70;
const INK = { gold: '#ffc24d', blue: '#57c7ff', green: '#45e486' };
export default function StakeFlow({ usd, grade, x, points, seat, collectivePct = 20, testid = 'stake-map' }) {
  const box = useRef(null); const [size, setSize] = useState({ w: 0, h: 0 }); const vertical = size.w > 0 && size.w < 640;
  useEffect(() => { const el = box.current; if (!el || typeof ResizeObserver === 'undefined') return undefined; let raf = 0; const ro = new ResizeObserver(() => { cancelAnimationFrame(raf); raf = requestAnimationFrame(() => setSize(old => (Math.abs(old.w - el.clientWidth) < 8 && Math.abs(old.h - el.clientHeight) < 8 ? old : { w: el.clientWidth, h: el.clientHeight }))); }); ro.observe(el); return () => { cancelAnimationFrame(raf); ro.disconnect(); }; }, []);   // measured a frame later, so a resize never loops, and a small nudge never redraws the map
  // The whole map always fits: the view is worked out from its own size and the box it sits in.
  const view = useMemo(() => { const at = Object.values(vertical ? TALL : WIDE); const W = Math.max(...at.map(p => p[0])) + NODE_W; const H = Math.max(...at.map(p => p[1])) + NODE_H; const zoom = size.w ? Math.min(1.25, (size.w - 16) / W, (size.h - 16) / H) : 1; return { x: (size.w - W * zoom) / 2, y: (size.h - H * zoom) / 2, zoom }; }, [size, vertical]);
  const nodes = useMemo(() => { const at = vertical ? TALL : WIDE; return [
    ['proof', '🧾', 'PROOF + $', money(usd), 'gold', 'Every send goes with a proof, $1 or more', null],
    ['checks', '⚖', 'THE SCORE', `Score ${Math.round(grade)}`, 'gold', 'Five checks, its print, then OSSY, G4 and the owner. 300 is the top today', grade / 1000],
    ['boost', '🚀', 'ITS BOOST', `${+x.toFixed(2)}x`, 'gold', 'Score over 100. The most it can ever earn, as a multiple of what it sent', x / 10],
    ['points', '🪙', 'BOOST POINTS', points.toLocaleString(undefined, { maximumFractionDigits: 2 }), 'gold', 'The most this proof can ever earn. Each dollar paid takes one off', null],
    ['seat', '🪑', 'ITS SEAT', `${seat.toFixed(2)}%`, 'green', 'Its share of every real pool profit', Math.min(1, seat / 10)],
    ['cash', '💵', 'BOOST CASH', 'Up to the limit', 'green', 'Releases second by second. Taking it out is off for now', null],
    ['pools', '💧', 'THE POOLS', money(usd), 'blue', 'All of it stays staked in the pools the Collective opens. Pools can lose money', null],
    ['profit', '📈', 'REAL PROFIT', 'Paid on chain', 'green', 'The only thing that pays anyone. No profit, no pay', null],
    ['house', '🏛', 'THE COLLECTIVE', `${Math.round(collectivePct)}%`, 'blue', 'Its piece of each profit. Agents can never take it', collectivePct / 100],
    ['rest', '♻', 'THE REST', 'Compounds', 'blue', 'Stays working in the pools', null],
  ].map(([id, icon, label, value, tone, tip, part]) => ({ id, type: 'stake', position: { x: at[id][0], y: at[id][1] }, draggable: false, selectable: false, data: { id, icon, label, value, tone, tip, part, vertical } })); }, [vertical, usd, grade, x, points, seat, collectivePct]);
  const edges = useMemo(() => LINKS.map(([source, target, tone, label]) => ({ id: `${source}-${target}`, source, target, animated: true, label, style: { stroke: INK[tone], strokeWidth: 2 }, labelStyle: { fill: '#e8eefb', fontSize: 11, fontWeight: 600 }, labelBgStyle: { fill: '#0b111c' }, labelBgPadding: [5, 3], labelBgBorderRadius: 5 })), []);
  return <div ref={box} className={`skf${vertical ? ' is-tall' : ''}`} data-testid={testid} role="img" aria-label={`A ${money(usd)} stake at grade ${Math.round(grade)}: boost ${x.toFixed(2)}x, seat ${seat.toFixed(2)}% of every real pool profit, up to ${points.toFixed(2)} points`}>{size.w ? <ReactFlow key={`${Math.round(size.w)}x${Math.round(size.h)}`} nodes={nodes} edges={edges} nodeTypes={NODE_TYPES} defaultViewport={view} minZoom={0.15} maxZoom={1.3} nodesDraggable={false} nodesConnectable={false} elementsSelectable={false} panOnDrag={false} panOnScroll={false} zoomOnScroll={false} zoomOnPinch={false} zoomOnDoubleClick={false} preventScrolling={false} /> : null}</div>;
}
