import React, { useEffect, useRef, useMemo, useState } from 'react';
import Globe from 'react-globe.gl';
import * as THREE from 'three';
import { ECOSYSTEMS } from '../lib/ecosystems';
import { LAUNCHPADS } from '../lib/launchpads';
const GLOBE_NODES = [...ECOSYSTEMS.filter(e => !e.isFeeless), ...LAUNCHPADS.map(p => ({ ...p, isLaunchpad: true }))];

class GlobeErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

function GlobeFallback({ onSelect, selectedId }) {
  return (
    <div
      className="globe-webgl-fallback"
      role="img"
      aria-label="FEELESS ecosystem network"
      style={{
        width: '100%',
        height: '100%',
        minHeight: 320,
        borderRadius: '50%',
        display: 'grid',
        placeItems: 'center',
        position: 'relative',
        overflow: 'hidden',
        background: 'radial-gradient(circle at 42% 38%, rgba(31, 107, 73, .9), rgba(3, 24, 15, .96) 52%, #020604 74%)',
        boxShadow: '0 0 80px rgba(20, 241, 149, .22), inset -36px -24px 70px rgba(0, 0, 0, .8)',
      }}
    >
      <div className="globe-fallback-orbit globe-fallback-orbit-primary" style={{ position: 'absolute', inset: '12%', border: '1px solid rgba(20, 241, 149, .25)', borderRadius: '50%', transform: 'rotate(-18deg)' }} />
      <div className="globe-fallback-orbit globe-fallback-orbit-secondary" style={{ position: 'absolute', inset: '22%', border: '1px dashed rgba(216, 246, 229, .18)', borderRadius: '50%', transform: 'rotate(28deg)' }} />
      <span className="globe-fallback-status" style={{ color: '#14f195', fontFamily: 'monospace', fontSize: 11, letterSpacing: '.18em' }}>WEBGL UNAVAILABLE</span>
      {GLOBE_NODES.map((node, index) => {
        const angle = (index / GLOBE_NODES.length) * Math.PI * 2 - Math.PI / 2;
        const radius = 39;
        const left = 50 + Math.cos(angle) * radius;
        const top = 50 + Math.sin(angle) * radius;
        return (
          <button
            key={node.id}
            type="button"
            onClick={() => onSelect?.(node.id)}
            aria-label={`Open ${node.name}`}
            className="globe-fallback-node"
            style={{
              position: 'absolute',
              left: `${left}%`,
              top: `${top}%`,
              transform: 'translate(-50%, -50%)',
              border: `1px solid ${node.color}`,
              borderRadius: 999,
              padding: '6px 9px',
              background: selectedId === node.id ? `${node.color}33` : 'rgba(2, 12, 8, .88)',
              color: '#eafff3',
              boxShadow: selectedId === node.id ? `0 0 18px ${node.color}88` : 'none',
              cursor: 'pointer',
              fontSize: 10,
              whiteSpace: 'nowrap',
            }}
          >
            {node.symbol || node.name?.slice(0, 1)} {node.name}
          </button>
        );
      })}
    </div>
  );
}

export default function Globe3D({ onSelect, selectedId, size = 640 }) {
  const globeRef = useRef();
  const containerRef = useRef();
  const [dims, setDims] = useState({ w: size, h: size });

  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => {
      const width = Math.max(1, Math.min(size, entry.contentRect.width));
      setDims({ w: width, h: width });
    });
    if (containerRef.current) observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [size]);

  useEffect(() => {
    let timer;
    let stopped = false;
    const setup = () => {
      if (stopped) return;
      const g = globeRef.current;
      if (!g || typeof g.controls !== 'function') { timer = setTimeout(setup, 80); return; }
      try {
        g.controls().autoRotate = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        g.controls().autoRotateSpeed = 0.85;
        g.controls().enableZoom = false;
        g.pointOfView({ altitude: 2.1 }, 0);
        if (typeof g.globeMaterial === 'function') {
          const globeMat = g.globeMaterial();
          globeMat.color = new THREE.Color('#02110A');
          globeMat.emissive = new THREE.Color('#0FDB8F');
          globeMat.emissiveIntensity = 0.22;
          globeMat.shininess = 4;
        }
      } catch (e) { /* noop */ }
    };
    setup();
    return () => { stopped = true; clearTimeout(timer); document.body.style.cursor = 'default'; };
  }, []);

  useEffect(() => {
    const node = GLOBE_NODES.find(n => n.id === selectedId);
    const globe = globeRef.current;
    if (globe?.controls) {
      globe.controls().autoRotate = !node && !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (node) globe.pointOfView({ lat: node.lat, lng: node.lng, altitude: 2.2 }, 900);
    }
  }, [selectedId]);

  const points = useMemo(() => GLOBE_NODES.map(e => ({
    ...e,
    size: e.id === selectedId ? 1.7 : e.isLaunchpad ? 1.25 : 0.85,
  })), [selectedId]);

  const arcs = useMemo(() => {
    const arr = [];
    const eco = GLOBE_NODES;
    for (let i = 0; i < eco.length; i++) {
      const a = eco[i];
      const b = eco[(i + 1) % eco.length];
      arr.push({
        startLat: a.lat, startLng: a.lng,
        endLat: b.lat, endLng: b.lng,
        color: [a.color, b.color]
      });
    }
    // hub arcs from Solana to each
    const hub = eco[0];
    for (const e of eco.slice(1)) {
      arr.push({
        startLat: hub.lat, startLng: hub.lng,
        endLat: e.lat, endLng: e.lng,
        color: ['#14F195', e.color]
      });
    }
    return arr;
  }, []);

  const rings = useMemo(() => GLOBE_NODES.map(e => ({
    lat: e.lat, lng: e.lng, color: e.color, maxR: 8, propagationSpeed: 2.6, repeatPeriod: 1200
  })), []);

  const particles = useMemo(() => Array.from({ length: 36 }, (_, i) => ({
    id: i,
    left: `${(i * 37) % 100}%`,
    top: `${(i * 53) % 100}%`,
    delay: `${(i % 12) * 0.6}s`,
    duration: `${6 + (i % 5) * 1.4}s`,
    size: 1 + (i % 3),
  })), []);

  return (
    <div ref={containerRef} className="globe-canvas-wrap globe-alive" data-testid="ecosystem-globe" style={{ width: '100%', maxWidth: size, aspectRatio: '1' }}>
      <div className="globe-bloom-layer globe-bloom-outer" aria-hidden="true" />
      <div className="globe-bloom-layer globe-bloom-inner" aria-hidden="true" />
      <div className="globe-particle-field" aria-hidden="true">{particles.map(p => <span key={p.id} className="globe-particle" style={{ left: p.left, top: p.top, animationDelay: p.delay, animationDuration: p.duration, width: p.size, height: p.size }} />)}</div>
      <GlobeErrorBoundary fallback={<GlobeFallback onSelect={onSelect} selectedId={selectedId} />}>
        <Globe
          ref={globeRef}
          width={dims.w}
          height={dims.h}
          backgroundColor="rgba(0,0,0,0)"
          showAtmosphere
          atmosphereColor="#14F195"
          atmosphereAltitude={0.32}
          globeImageUrl="//unpkg.com/three-globe/example/img/earth-dark.jpg"
          bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
          pointsData={points}
          pointLat="lat"
          pointLng="lng"
          pointColor="color"
          pointAltitude={0.02}
          pointRadius="size"
          pointResolution={24}
          labelsData={GLOBE_NODES.filter(n => n.isLaunchpad || n.id === 'solana')}
          labelLat="lat"
          labelLng="lng"
          labelText="name"
          labelColor={() => '#d8f6e5'}
          labelSize={1.15}
          labelDotRadius={0}
          labelAltitude={0.07}
          labelResolution={2}
          onLabelClick={p => onSelect?.(p.id)}
           pointLabel={p => `<div class="globe-point-tooltip" style="padding:6px 10px;background:#0a0f0d;border:1px solid ${p.color};border-radius:8px;color:#fff;font-family:sans-serif;font-size:12px;box-shadow:0 0 12px ${p.color}80;">${p.name} · ${p.symbol}</div>`}
          onPointClick={p => onSelect && onSelect(p.id)}
          onPointHover={p => document.body.style.cursor = p ? 'pointer' : 'default'}
          arcsData={arcs}
          arcColor="color"
          arcStroke={0.35}
          arcAltitude={0.22}
          arcDashLength={0.4}
          arcDashGap={2}
          arcDashAnimateTime={4000}
          ringsData={rings}
          ringColor="color"
          ringMaxRadius="maxR"
          ringPropagationSpeed="propagationSpeed"
          ringRepeatPeriod="repeatPeriod"
        />
      </GlobeErrorBoundary>
    </div>
  );
}
