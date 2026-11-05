import React, { useEffect, useRef, useState } from 'react';
import Graph from 'graphology';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import Sigma from 'sigma';

// 🌌 THE STASH AS SPACE (owner 2026-11-05: black, fine lines and dots): sigma.js + graphology (both MIT), drawn on the GPU so it stays smooth from a dozen bubbles to many thousands. A bubble's size is what the server counted. Hover lights its links; click reads it. Wheel zooms, drag moves.
const size = (n, kind) => (kind === 'dot' ? 1.5 : kind === 'root' ? 8 : kind === 'cat' ? 5.5 : Math.min(5, 1.8 + Math.sqrt(Math.max(0, n)) * 0.42));
export default function StashMap({ nodes, edges, onPick, testid = 'stw-sigma' }) {
  const box = useRef(null); const [fail, setFail] = useState(false); const pickRef = useRef(onPick); pickRef.current = onPick;
  const key = JSON.stringify([nodes.map(n => [n.id, n.n]), edges.length]);
  useEffect(() => {
    if (!box.current) return undefined;
    let sigma = null; let stopTurn = null;
    try {
      const day = document.body.classList.contains('theme-day'); const g = new Graph(); const count = Math.max(1, nodes.length);
      nodes.forEach((n, i) => { const a = (i / count) * Math.PI * 2; const r = n.kind === 'root' ? 0 : n.kind === 'cat' ? 1 : 2; g.addNode(n.id, { fixed: n.kind === 'root', x: Math.cos(a * 37) * (r + (i % 7) / 3), y: Math.sin(a * 37) * (r + (i % 7) / 3), size: size(n.n, n.kind), label: n.kind === 'dot' ? '' : `${n.label} · ${n.n.toLocaleString()}`, color: n.kind === 'dot' ? n.color : n.kind === 'root' ? '#ffffff' : n.kind === 'cat' ? (n.color || '#7fd0ff') : '#cfe0ff', n: n.n, name: n.label, kind: n.kind }); });
      edges.forEach(([a, b]) => { if (g.hasNode(a.id) && g.hasNode(b.id) && !g.hasEdge(a.id, b.id)) g.addEdge(a.id, b.id, { size: 0.3, color: day ? '#27408f22' : (b.kind === 'dot' ? '#ffffff30' : '#8fb7ff66') }); });
      if (count > 1) forceAtlas2.assign(g, { iterations: count > 1500 ? 28 : 55, settings: { ...forceAtlas2.inferSettings(g), scalingRatio: 14, gravity: 0.35, strongGravityMode: false, linLogMode: true, adjustSizes: false, barnesHutOptimize: count > 200 } });
      let hover = null;
      sigma = new Sigma(g, box.current, { allowInvalidContainer: true, minEdgeThickness: 0.45, labelColor: { color: day ? '#101a44' : '#aeb9d4' }, labelFont: 'JetBrains Mono, monospace', labelSize: 10, labelWeight: '500', labelDensity: 0.6, labelGridCellSize: 110, labelRenderedSizeThreshold: 3, defaultDrawNodeHover: (ctx, d, s) => { const label = d.label || ''; ctx.font = '600 12px Sora, sans-serif'; const w = ctx.measureText(label).width + 14; ctx.fillStyle = day ? '#ffffff' : '#0a1020'; ctx.strokeStyle = d.color; ctx.lineWidth = 1; ctx.beginPath(); ctx.roundRect(d.x + d.size + 4, d.y - 11, w, 22, 6); ctx.fill(); ctx.stroke(); ctx.fillStyle = day ? '#101a44' : '#fff'; ctx.textBaseline = 'middle'; ctx.fillText(label, d.x + d.size + 11, d.y, s.labelSize ? undefined : undefined); },
        nodeReducer: (id, a) => (hover && id !== hover && !g.areNeighbors(id, hover) ? { ...a, color: day ? '#d4dbe8' : '#22304f', label: '' } : a), edgeReducer: (id, a) => (hover && !g.hasExtremity(id, hover) ? { ...a, hidden: true } : hover ? { ...a, color: g.getNodeAttribute(hover, 'color'), size: 1.5 } : a) });
      sigma.on('enterNode', ({ node }) => { hover = node; box.current.style.cursor = 'pointer'; sigma.refresh({ skipIndexation: true }); });
      sigma.on('leaveNode', () => { hover = null; box.current.style.cursor = ''; sigma.refresh({ skipIndexation: true }); });
      sigma.on('clickNode', ({ node }) => pickRef.current?.(node));
      sigma.on('clickStage', () => pickRef.current?.(null));
      // 🌌 It turns very slowly. Stops when hidden, off-screen, in fx-lite or with reduced motion.
      const still = document.body.classList.contains('fx-lite') || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches; let seen = true; const io = typeof IntersectionObserver !== 'undefined' ? new IntersectionObserver(([e]) => { seen = e.isIntersecting; }) : null; io?.observe(box.current); const cam = sigma.getCamera(); const turn = !still ? setInterval(() => { if (seen && !document.hidden && !hover) cam.setState({ angle: cam.angle + 0.0012 }); }, 80) : null; stopTurn = () => { if (turn) clearInterval(turn); io?.disconnect(); };
    } catch { setFail(true); }
    return () => { stopTurn?.(); try { sigma?.kill(); } catch { /* already gone */ } };
  }, [key]);   // eslint-disable-line react-hooks/exhaustive-deps
  return <div className="stw-sigma" ref={box} data-testid={testid} role="img" aria-label={`A map of everything in the Stash, ${nodes.length} points`}>{fail ? <p className="stw-none">Your browser could not draw the map. The numbers below are still right.</p> : null}</div>;
}
