import React, { useEffect, useRef, useState } from 'react';
import Graph from 'graphology';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import Sigma from 'sigma';

// 🫧 THE STASH'S BUBBLE MAP: sigma.js + graphology (both MIT), drawn on the GPU so it stays smooth from a dozen bubbles to many thousands. A bubble's size is what the server counted. Hover lights its links; click reads it. Wheel zooms, drag moves.
const size = n => Math.min(46, 3.5 + Math.sqrt(Math.max(0, n)) * 1.9);
export default function StashMap({ nodes, edges, onPick, testid = 'stw-sigma' }) {
  const box = useRef(null); const [fail, setFail] = useState(false); const pickRef = useRef(onPick); pickRef.current = onPick;
  const key = JSON.stringify([nodes.map(n => [n.id, n.n]), edges.length]);
  useEffect(() => {
    if (!box.current) return undefined;
    let sigma = null;
    try {
      const day = document.body.classList.contains('theme-day'); const g = new Graph(); const count = Math.max(1, nodes.length);
      nodes.forEach((n, i) => { const a = (i / count) * Math.PI * 2; const r = n.kind === 'root' ? 0 : n.kind === 'cat' ? 1 : 2; g.addNode(n.id, { fixed: n.kind === 'root', x: Math.cos(a) * r, y: Math.sin(a) * r, size: size(n.n), label: `${n.label} · ${n.n.toLocaleString()}`, color: n.color || '#7fd0ff', n: n.n, name: n.label }); });
      edges.forEach(([a, b]) => { if (g.hasNode(a.id) && g.hasNode(b.id) && !g.hasEdge(a.id, b.id)) g.addEdge(a.id, b.id, { size: 1, color: day ? '#27408f33' : '#7fa8ff40' }); });
      if (count > 1) forceAtlas2.assign(g, { iterations: count > 500 ? 80 : 220, settings: { ...forceAtlas2.inferSettings(g), scalingRatio: 30, gravity: 0.8, strongGravityMode: true, linLogMode: false, adjustSizes: count <= 500, barnesHutOptimize: count > 200 } });
      let hover = null;
      sigma = new Sigma(g, box.current, { allowInvalidContainer: true, labelColor: { color: day ? '#101a44' : '#e8efff' }, labelFont: 'Sora, sans-serif', labelSize: 12, labelWeight: '600', labelRenderedSizeThreshold: 7, defaultDrawNodeHover: (ctx, d, s) => { const label = d.label || ''; ctx.font = '600 12px Sora, sans-serif'; const w = ctx.measureText(label).width + 14; ctx.fillStyle = day ? '#ffffff' : '#0a1020'; ctx.strokeStyle = d.color; ctx.lineWidth = 1; ctx.beginPath(); ctx.roundRect(d.x + d.size + 4, d.y - 11, w, 22, 6); ctx.fill(); ctx.stroke(); ctx.fillStyle = day ? '#101a44' : '#fff'; ctx.textBaseline = 'middle'; ctx.fillText(label, d.x + d.size + 11, d.y, s.labelSize ? undefined : undefined); },
        nodeReducer: (id, a) => (hover && id !== hover && !g.areNeighbors(id, hover) ? { ...a, color: day ? '#d4dbe8' : '#22304f', label: '' } : a), edgeReducer: (id, a) => (hover && !g.hasExtremity(id, hover) ? { ...a, hidden: true } : hover ? { ...a, color: g.getNodeAttribute(hover, 'color'), size: 1.5 } : a) });
      sigma.on('enterNode', ({ node }) => { hover = node; box.current.style.cursor = 'pointer'; sigma.refresh({ skipIndexation: true }); });
      sigma.on('leaveNode', () => { hover = null; box.current.style.cursor = ''; sigma.refresh({ skipIndexation: true }); });
      sigma.on('clickNode', ({ node }) => pickRef.current?.(node));
      sigma.on('clickStage', () => pickRef.current?.(null));
    } catch { setFail(true); }
    return () => { try { sigma?.kill(); } catch { /* already gone */ } };
  }, [key]);   // eslint-disable-line react-hooks/exhaustive-deps
  return <div className="stw-sigma" ref={box} data-testid={testid} role="img" aria-label={`A bubble map of ${nodes.length} groups in the Stash`}>{fail ? <p className="stw-none">Your browser could not draw the map. The numbers below are still right.</p> : null}</div>;
}
