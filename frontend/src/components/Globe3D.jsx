import React, { useEffect, useRef, useMemo, useState } from 'react';
import Globe from 'react-globe.gl';
import * as THREE from 'three';
import { ECOSYSTEMS } from '../lib/ecosystems';

export default function Globe3D({ onSelect, selectedId, size = 640 }) {
  const globeRef = useRef();
  const [dims, setDims] = useState({ w: size, h: size });

  useEffect(() => {
    const setup = () => {
      const g = globeRef.current;
      if (!g || typeof g.controls !== 'function') { setTimeout(setup, 80); return; }
      try {
        g.controls().autoRotate = true;
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
  }, []);

  const points = useMemo(() => ECOSYSTEMS.filter(e => !e.isFeeless).map(e => ({
    ...e,
    size: e.id === selectedId ? 1.6 : 1.0,
  })), [selectedId]);

  const arcs = useMemo(() => {
    const arr = [];
    const eco = ECOSYSTEMS.filter(e => !e.isFeeless);
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

  const rings = useMemo(() => ECOSYSTEMS.filter(e => !e.isFeeless).map(e => ({
    lat: e.lat, lng: e.lng, color: e.color, maxR: 6, propagationSpeed: 2, repeatPeriod: 1800
  })), []);

  return (
    <div className="relative" style={{ width: dims.w, height: dims.h }}>
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
