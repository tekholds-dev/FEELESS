import React, { useEffect, useRef, useMemo, useState } from 'react';
import Globe from 'react-globe.gl';
import * as THREE from 'three';
import { ECOSYSTEMS } from '../lib/ecosystems';
import { LAUNCHPADS } from '../lib/launchpads';
const GLOBE_NODES = [...ECOSYSTEMS.filter(e => !e.isFeeless), ...LAUNCHPADS.map(p => ({ ...p, isLaunchpad: true }))];

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
        g.controls().autoRotateSpeed = 0.6;
        g.controls().enableZoom = false;
        g.pointOfView({ altitude: 2.2 }, 0);
        if (typeof g.globeMaterial === 'function') {
          const globeMat = g.globeMaterial();
          globeMat.color = new THREE.Color('#02110A');
          globeMat.emissive = new THREE.Color('#0A3D2A');
          globeMat.emissiveIntensity = 0.15;
          globeMat.shininess = 0.6;
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
    lat: e.lat, lng: e.lng, color: e.color, maxR: 6, propagationSpeed: 2, repeatPeriod: 1800
  })), []);

  return (
    <div ref={containerRef} className="globe-canvas-wrap" data-testid="ecosystem-globe" style={{ width: '100%', maxWidth: size, aspectRatio: '1' }}>
      <div className="absolute inset-0 rounded-full pointer-events-none"
        style={{ background: 'radial-gradient(circle at 50% 50%, rgba(20,241,149,0.18) 0%, rgba(20,241,149,0.06) 30%, transparent 60%)', filter: 'blur(20px)' }}
      />
      <Globe
        ref={globeRef}
        width={dims.w}
        height={dims.h}
        backgroundColor="rgba(0,0,0,0)"
        showAtmosphere
        atmosphereColor="#14F195"
        atmosphereAltitude={0.22}
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
        pointLabel={p => `<div style="padding:6px 10px;background:#0a0f0d;border:1px solid ${p.color};border-radius:8px;color:#fff;font-family:sans-serif;font-size:12px;box-shadow:0 0 12px ${p.color}80;">${p.name} · ${p.symbol}</div>`}
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
    </div>
  );
}
