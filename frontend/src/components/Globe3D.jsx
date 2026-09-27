import React, { useEffect, useRef, useMemo, useState } from 'react';
import Globe from 'react-globe.gl';
import * as THREE from 'three';
import { ECOSYSTEMS } from '../lib/ecosystems';
import { LAUNCHPADS } from '../lib/launchpads';
import { useGlobeBubbles } from '../lib/globeBubbles';
import { apiUrl } from '../lib/api';
import { burstObject, tickBurst, disposeBurst, coinHeat, kindFor, BURST_COLORS } from '../lib/globeBursts';

const hashNum = str => { let h = 2166136261; for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); } return (h >>> 0) / 4294967295; };
let glowTex = null;
const glowTexture = () => {
  if (glowTex) return glowTex;
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d'); const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, 'rgba(255,255,255,1)'); grad.addColorStop(0.25, 'rgba(255,255,255,.85)'); grad.addColorStop(0.55, 'rgba(255,255,255,.22)'); grad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grad; g.fillRect(0, 0, 64, 64);
  glowTex = new THREE.CanvasTexture(c);
  return glowTex;
};
// Emoji-in-a-glow texture, cached per glyph so we don't re-rasterize every frame.
const emojiTex = {};
function glyphTexture(glyph) {
  if (emojiTex[glyph]) return emojiTex[glyph];
  const c = document.createElement('canvas'); c.width = c.height = 96;
  const g = c.getContext('2d');
  g.font = '64px "Apple Color Emoji","Segoe UI Emoji",sans-serif';
  g.textAlign = 'center'; g.textBaseline = 'middle';
  g.fillText(glyph, 48, 52);
  const tex = new THREE.CanvasTexture(c);
  emojiTex[glyph] = tex;
  return tex;
}
// Activity glyph: how a coin is trading right now, not just its market color.
function activityGlyph(change24h) {
  const c = Number(change24h);
  if (!Number.isFinite(c)) return '✨';
  if (c >= 40) return '🚀';
  if (c >= 15) return '🔥';
  if (c <= -30) return '💀';
  if (c <= -12) return '🧊';
  return '✨';
}
function tokenOrb(d) {
  const group = new THREE.Group();
  const hot = Number(d.token?.change24h) >= 15;
  const cold = Number(d.token?.change24h) <= -12;
  const haloColor = hot ? '#ff8a3d' : cold ? '#5ec8ff' : d.color;
  const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture(), color: haloColor, transparent: true, opacity: hot ? 0.75 : 0.55, depthWrite: false, blending: THREE.AdditiveBlending }));
  const haloScale = d.size * (hot ? 5.4 : 4.2);
  halo.scale.set(haloScale, haloScale, 1);
  halo.userData.pulse = hot;
  const glyph = new THREE.Sprite(new THREE.SpriteMaterial({ map: glyphTexture(activityGlyph(d.token?.change24h)), transparent: true, depthWrite: false }));
  glyph.scale.set(d.size * 2.6, d.size * 2.6, 1);
  group.add(halo); group.add(glyph);
  group.userData.pulseHalo = hot ? halo : null;
  return group;
}
const fmtCap = v => (v >= 1e9 ? `$${(v / 1e9).toFixed(2)}B` : `$${(v / 1e6).toFixed(1)}M`);

// Every token with $10M+ market cap (true data from GeckoTerminal), placed around its network node.
function useBigTokens() {
  const [tokens, setTokens] = useState([]);
  useEffect(() => {
    let alive = true;
    const load = () => fetch(apiUrl('/api/reputation/globe-tokens')).then(r => (r.ok ? r.json() : null)).then(d => { if (alive && d?.tokens) setTokens(d.tokens); }).catch(() => {});
    load();
    const t = setInterval(() => { if (!document.hidden) load(); }, 60000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  return tokens;
}

// The FEELESS mark mown into the Pampas grasslands, like a crop circle: composited once into the
// earth texture (multiply = darker cut grass, soft-light = sheen), so it rotates with the planet at
// zero per-frame cost. Falls back to the plain texture if anything fails to load.
const EARTH_URL = 'https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg';
function useEngravedEarth() {
  const [url, setUrl] = useState(EARTH_URL);
  useEffect(() => {
    let alive = true;
    const load = src => new Promise((res, rej) => { const i = new Image(); i.crossOrigin = 'anonymous'; i.onload = () => res(i); i.onerror = rej; i.src = src; });
    Promise.all([load(EARTH_URL), load('/assets/feeless-logo.png')]).then(([earth, logo]) => {
      const c = document.createElement('canvas'); c.width = earth.width; c.height = earth.height;
      const g = c.getContext('2d'); g.drawImage(earth, 0, 0);
      const lat = -35.5, lng = -62.5, deg = 10;        // the Argentine Pampas — open grassland, clear of network nodes
      const px = w => (w / 360) * c.width;
      const x = ((lng + 180) / 360) * c.width, y = ((90 - lat) / 180) * c.height, size = px(deg);
      // grayscale mask of the logo -> tinted "mown grass" layers
      const m = document.createElement('canvas'); m.width = m.height = Math.round(size);
      const mg = m.getContext('2d'); mg.drawImage(logo, 0, 0, m.width, m.height);
      mg.globalCompositeOperation = 'source-in';
      g.save(); g.translate(x - size / 2, y - size / 2);
      mg.fillStyle = '#1f3d12'; mg.fillRect(0, 0, m.width, m.height);
      g.globalAlpha = 0.72; g.globalCompositeOperation = 'multiply'; g.drawImage(m, 0, 0);
      mg.fillStyle = '#b9ffcf'; mg.fillRect(0, 0, m.width, m.height);
      g.globalAlpha = 0.35; g.globalCompositeOperation = 'soft-light'; g.drawImage(m, -1, -1);
      g.restore();
      if (alive) setUrl(c.toDataURL('image/jpeg', 0.9));
    }).catch(() => {});
    return () => { alive = false; };
  }, []);
  return url;
}

const escapeHtml = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// Live global HUD readout — the same on-chain evidence surfaced everywhere else, framed as
// mission-control stats over the planet: this many coins scanned, this many snipers/funders caught.
function useGlobeStats() {
  const [stats, setStats] = useState(null);
  useEffect(() => {
    let alive = true;
    const load = () => fetch('/api/reputation/stats').then(r => (r.ok ? r.json() : null)).then(d => { if (alive && d) setStats(d); }).catch(() => {});
    load();
    const t = setInterval(() => { if (!document.hidden) load(); }, 25000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  return stats;
}

// A field of distant stars behind the planet, each drifting at its own lazy pace — the globe
// reads as floating in real space instead of sitting on a flat panel.
function useStarfield(count = 90) {
  return useMemo(() => Array.from({ length: count }, (_, i) => ({
    id: i,
    left: `${(hashNum(`sx${i}`) * 100).toFixed(2)}%`,
    top: `${(hashNum(`sy${i}`) * 100).toFixed(2)}%`,
    size: 0.6 + hashNum(`ss${i}`) * 1.8,
    delay: `${(hashNum(`sd${i}`) * 6).toFixed(2)}s`,
    duration: `${5 + hashNum(`sD${i}`) * 6}s`,
  })), [count]);
}
function bubbleElement(b) {
  const el = document.createElement('div');
  el.className = `globe-bubble globe-bubble-${b.kind}`;
  el.style.setProperty('--bubble-color', b.color);
  const text = b.text.length > 64 ? `${b.text.slice(0, 61)}…` : b.text;
  el.innerHTML = `<small>${escapeHtml(b.name)} · ${escapeHtml(b.who)}</small><span>${escapeHtml(text)}</span>`;
  return el;
}
const GLOBE_NODES = [...ECOSYSTEMS.filter(e => !e.isFeeless), ...LAUNCHPADS.map(p => ({ ...p, isLaunchpad: true }))];

// The HUD owns its own state (stats poll + live feed), so feed updates re-render only this box —
// never the WebGL globe, whose layers would otherwise be re-digested on every burst.
const GlobeHud = React.memo(function GlobeHud({ hottest, openToken, feedPush, fireRef }) {
  const stats = useGlobeStats();
  const [feed, setFeed] = useState([]);
  useEffect(() => { feedPush.current = item => setFeed(f => [item, ...f].slice(0, 3)); return () => { feedPush.current = null; }; }, [feedPush]);
  // New snipers / repeat funders caught since the last poll -> red catch burst on Solana.
  const lastStats = useRef(null);
  useEffect(() => {
    if (!stats) return;
    const was = lastStats.current; lastStats.current = stats;
    if (!was) return;
    const sol = GLOBE_NODES.find(n => n.id === 'solana');
    const caught = (stats.snipers - was.snipers) + (stats.bundlers - was.bundlers);
    const funders = (stats.flaggedFunders || 0) - (was.flaggedFunders || 0);
    if (sol && funders > 0) fireRef.current?.(sol.lat, sol.lng, 'catch', 1, `🚨 ${funders} repeat funder${funders > 1 ? 's' : ''} flagged`);
    else if (sol && caught > 0) fireRef.current?.(sol.lat, sol.lng, 'catch', 0.8, `🎯 ${caught} sniper/bundler wallet${caught > 1 ? 's' : ''} caught`);
  }, [stats, fireRef]);
  return <>
      {stats && <div className="globe-hud" data-testid="globe-hud">
        <a className="globe-hud-row" href="/terminal/reputation"><i className="flr-dot" /><span>Live on-chain evidence</span></a>
        <div className="globe-hud-stats">
          <a href="/terminal/reputation"><b>{stats.mintsScanned?.toLocaleString?.()}</b><small>scanned</small></a>
          <a href="/terminal/reputation"><b>{stats.snipers?.toLocaleString?.()}</b><small>snipers</small></a>
          <a href="/terminal/reputation"><b>{stats.flaggedFunders ?? 0}</b><small>funders</small></a>
          <a href="/terminal/reputation"><b>{stats.blocklisted?.toLocaleString?.()}</b><small>blocked</small></a>
        </div>
        {hottest && <button type="button" className="globe-hud-hot" onClick={() => openToken(hottest)}><i>🔥</i>${String(hottest.symbol).replace(/^\$/, '')} {Number(hottest.change24h) >= 0 ? '+' : ''}{Number(hottest.change24h).toFixed(1)}%</button>}
        {feed.length > 0 && <ul className="globe-feed" data-testid="globe-feed">{feed.map(f => <li key={f.id} style={{ '--c': f.color }}>{f.token ? <button type="button" onClick={() => openToken(f.token)}>{f.label}</button> : f.label}</li>)}</ul>}
      </div>}
  </>;
});

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

export default function Globe3D({ onSelect, onToken, selectedId, size = 640 }) {
  const globeRef = useRef();
  const containerRef = useRef();
  const [dims, setDims] = useState({ w: size, h: size });
  const bubbles = useGlobeBubbles(GLOBE_NODES);
  const bigTokens = useBigTokens();
  const earthUrl = useEngravedEarth();
  const stars = useStarfield(40);
  const visible = useRef(true);
  const feedPush = useRef(null);
  const fireRef = useRef(null);
  const burstObjs = useRef(new Map());
  const fire = (lat, lng, kind, power, label, color, token) => {
    const b = { id: `${Date.now()}-${Math.random()}`, lat, lng, kind, power, born: performance.now(), color: color || BURST_COLORS[kind] || '#14F195' };
    const g = globeRef.current;
    if (visible.current && !document.hidden && g?.scene && g?.getCoords && burstObjs.current.size < 18) {
      const o = burstObject(b); const c = g.getCoords(lat, lng, 0.01);
      o.position.set(c.x, c.y, c.z); o.lookAt(c.x * 2, c.y * 2, c.z * 2);
      g.scene().add(o); burstObjs.current.set(b.id, o);
    }
    if (label) feedPush.current?.({ id: b.id, kind, label, color: b.color, token });
  };
  const openToken = t => { if (!t) return; if (onToken) { onToken(t); return; } if (t.pairAddress) window.open(`/terminal/trade?chain=${encodeURIComponent(t.chain)}&pair=${encodeURIComponent(t.pairAddress)}`, '_blank', 'noopener'); };
  const hottest = useMemo(() => [...bigTokens].filter(t => Number.isFinite(Number(t.change24h)) && Math.abs(Number(t.change24h)) < 2000).sort((a, b) => Number(b.change24h) - Number(a.change24h))[0], [bigTokens]);
  // Brand-new pools can report absurd 24h moves (e.g. +8,725,052,277%); those aren't signal.
  const tokenPoints = useMemo(() => bigTokens.filter(t => Math.abs(Number(t.change24h) || 0) < 2000).map(t => {
    const home = GLOBE_NODES.find(n => !n.isLaunchpad && (n.chainId === t.chain || n.id === t.chain));
    if (!home) return null;
    const h = hashNum(`${t.chain}:${t.address}`);
    const angle = h * Math.PI * 2;
    const dist = 4 + hashNum(t.address || t.symbol) * 9;
    const change = Number(t.change24h);
    return {
      isToken: true, token: t, lat: Math.max(-80, Math.min(80, home.lat + Math.sin(angle) * dist)), lng: home.lng + Math.cos(angle) * dist,
      size: Math.min(2.6, 1.1 + Math.log10(t.marketCap / 1e7) * 0.55),
      color: Number.isFinite(change) ? (change >= 0 ? '#5ee0ff' : '#ff8fa3') : '#5ee0ff',
      name: t.symbol,
    };
  }).filter(Boolean), [bigTokens]);

  // Real activity -> bursts. Chat/signal bubbles as they land:
  useEffect(() => {
    bubbles.forEach((b, i) => setTimeout(() => fire(b.lat, b.lng, b.kind === 'chat' ? 'chat' : 'signal', b.kind === 'chat' ? 0.45 : 0.6,
      `${b.kind === 'chat' ? '💬' : '📡'} ${b.name}: ${b.text.slice(0, 38)}`, b.kind === 'chat' ? b.color : undefined), i * 450));
  }, [bubbles]); // eslint-disable-line react-hooks/exhaustive-deps

  // Price ticks between refreshes, sized by how far it moved.
  const lastPrices = useRef(new Map());
  useEffect(() => {
    const prev = lastPrices.current;
    let delay = 0;
    tokenPoints.forEach(p => {
      const px = Number(p.token.priceUsd); const key = `${p.token.chain}:${p.token.address}`;
      const was = prev.get(key); prev.set(key, px);
      if (!was || !px || was === px) return;
      const move = (px - was) / was * 100;
      const power = Math.min(1, 0.35 + Math.abs(move) * 0.25);
      setTimeout(() => fire(p.lat, p.lng, move >= 0 ? 'pump' : 'dump', power, Math.abs(move) >= 0.5 ? `${move >= 0 ? '▲' : '▼'} $${String(p.token.symbol).replace(/^\$/, '')} ${move >= 0 ? '+' : ''}${move.toFixed(2)}% on ${p.token.chain}` : null, undefined, p.token), delay);
      delay += 180;
    });
  }, [tokenPoints]); // eslint-disable-line react-hooks/exhaustive-deps

  // Heartbeat: coins erupt in proportion to their real 24h heat, so hot coins visibly boil.
  useEffect(() => {
    if (!tokenPoints.length || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return undefined;
    const weights = tokenPoints.map(p => 0.05 + coinHeat(p.token) ** 2);
    const total = weights.reduce((a, b) => a + b, 0);
    let n = 0;
    const t = setInterval(() => {
      if (document.hidden || !visible.current) return;
      let r = Math.random() * total; let i = 0;
      while (r > weights[i] && i < weights.length - 1) { r -= weights[i]; i++; }
      const p = tokenPoints[i]; const heat = coinHeat(p.token); const kind = kindFor(p.token);
      const ch = Number(p.token.change24h) || 0;
      fire(p.lat, p.lng, kind, 0.2 + heat * 0.8, (n++ % 4 === 0 && Math.abs(ch) >= 5) ? `${ch >= 25 ? '🚀' : ch >= 5 ? '🔥' : '🧊'} $${String(p.token.symbol).replace(/^\$/, '')} ${ch >= 0 ? '+' : ''}${ch.toFixed(1)}% 24h` : null, undefined, p.token);
    }, 950);
    return () => clearInterval(t);
  }, [tokenPoints]); // eslint-disable-line react-hooks/exhaustive-deps

  fireRef.current = fire;

  // One animation loop drives every live burst; finished ones are dropped + disposed.
  useEffect(() => {
    let raf;
    const loop = () => {
      if (!visible.current) { raf = requestAnimationFrame(loop); return; }
      const now = performance.now();
      const dead = [];
      burstObjs.current.forEach((obj, id) => { if (!tickBurst(obj, now)) dead.push(id); });
      if (dead.length) {
        dead.forEach(id => { const o = burstObjs.current.get(id); o?.parent?.remove(o); disposeBurst(o); burstObjs.current.delete(id); });
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, []);

  // Off-screen = paused: no bursts, no auto-rotate, no WebGL frames burned while you scroll the page.
  useEffect(() => {
    const el = containerRef.current; if (!el || typeof IntersectionObserver === 'undefined') return undefined;
    const io = new IntersectionObserver(([e]) => {
      visible.current = e.isIntersecting;
      const g = globeRef.current;
      try { if (e.isIntersecting) g?.resumeAnimation?.(); else g?.pauseAnimation?.(); } catch { /* noop */ }
    }, { threshold: 0.05 });
    io.observe(el);
    return () => io.disconnect();
  }, []);

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
        try { g.renderer().setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5)); } catch { /* noop */ }
        g.pointOfView({ altitude: 2.1 }, 0);
        if (typeof g.globeMaterial === 'function') {
          const globeMat = g.globeMaterial();
          globeMat.color = new THREE.Color('#9fb8d6');
          globeMat.emissive = new THREE.Color('#0b2a3f');
          globeMat.emissiveIntensity = 0.5;
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

  const rings = useMemo(() => [
    ...GLOBE_NODES.map(e => ({ lat: e.lat, lng: e.lng, color: e.color, maxR: 8, propagationSpeed: 2.6, repeatPeriod: 1200 })),
    ...[...tokenPoints].sort((a, b) => b.token.marketCap - a.token.marketCap).slice(0, 10)
      .map(t => ({ lat: t.lat, lng: t.lng, color: t.color, maxR: 2.6, propagationSpeed: 0.9, repeatPeriod: 2600 })),
  ], [tokenPoints]);

  const particles = useMemo(() => Array.from({ length: 16 }, (_, i) => ({
    id: i,
    left: `${(i * 37) % 100}%`,
    top: `${(i * 53) % 100}%`,
    delay: `${(i % 12) * 0.6}s`,
    duration: `${6 + (i % 5) * 1.4}s`,
    size: 1 + (i % 3),
  })), []);

  return (
    <div ref={containerRef} className="globe-canvas-wrap globe-alive" data-testid="ecosystem-globe" style={{ width: '100%', maxWidth: size, aspectRatio: '1' }}
      onMouseEnter={() => { const c = globeRef.current?.controls?.(); if (c) c.autoRotate = false; }}
      onMouseLeave={() => { const c = globeRef.current?.controls?.(); if (c && !selectedId && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) c.autoRotate = true; }}>
      <div className="globe-bloom-layer globe-bloom-outer" aria-hidden="true" />
      <div className="globe-bloom-layer globe-bloom-inner" aria-hidden="true" />
      <div className="globe-particle-field" aria-hidden="true">{particles.map(p => <span key={p.id} className="globe-particle" style={{ left: p.left, top: p.top, animationDelay: p.delay, animationDuration: p.duration, width: p.size, height: p.size }} />)}</div>
      <div className="globe-starfield" aria-hidden="true">{stars.map(s => <span key={s.id} className="globe-star" style={{ left: s.left, top: s.top, width: s.size, height: s.size, animationDelay: s.delay, animationDuration: s.duration }} />)}</div>
      <GlobeHud hottest={hottest} openToken={openToken} feedPush={feedPush} fireRef={fireRef} />
      <GlobeErrorBoundary fallback={<GlobeFallback onSelect={onSelect} selectedId={selectedId} />}>
        <Globe
          ref={globeRef}
          width={dims.w}
          height={dims.h}
          backgroundColor="rgba(0,0,0,0)"
          showAtmosphere
          atmosphereColor="#7cc8ff"
          atmosphereAltitude={0.38}
          globeImageUrl={earthUrl}
          bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
          pointsData={points}
          pointLat="lat"
          pointLng="lng"
          pointColor="color"
          pointAltitude={0.008}
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
           pointLabel={p => p.isToken
            ? `<div class="globe-point-tooltip" style="padding:7px 10px;background:#0a0f0d;border:1px solid ${p.color};border-radius:8px;color:#fff;font-family:sans-serif;font-size:12px;box-shadow:0 0 12px ${p.color}80;"><b>${escapeHtml(p.token.symbol)}</b> · ${escapeHtml(p.token.chain)}<br/>${fmtCap(p.token.marketCap)} ${p.token.mcKind === 'FDV' ? 'FDV' : 'MC'}${Number.isFinite(Number(p.token.change24h)) ? ` · ${Number(p.token.change24h) >= 0 ? '+' : ''}${Number(p.token.change24h).toFixed(1)}% 24h` : ''}</div>`
            : `<div class="globe-point-tooltip" style="padding:6px 10px;background:#0a0f0d;border:1px solid ${p.color};border-radius:8px;color:#fff;font-family:sans-serif;font-size:12px;box-shadow:0 0 12px ${p.color}80;">${p.name} · ${p.symbol}</div>`}
          onPointClick={p => { if (p.isToken) { if (p.token.pairAddress) window.open(`/terminal/trade?chain=${encodeURIComponent(p.token.chain)}&pair=${encodeURIComponent(p.token.pairAddress)}`, '_blank', 'noopener'); return; } onSelect && onSelect(p.id); }}
          onPointHover={p => document.body.style.cursor = p ? 'pointer' : 'default'}
          arcsData={arcs}
          arcColor="color"
          arcStroke={0.5}
          arcAltitude={0.22}
          arcDashLength={0.4}
          arcDashGap={2}
          arcDashAnimateTime={2600}
          ringsData={rings}
          ringColor="color"
          ringMaxRadius="maxR"
          ringPropagationSpeed="propagationSpeed"
          ringRepeatPeriod="repeatPeriod"
          objectsData={tokenPoints}
          objectLat="lat"
          objectLng="lng"
          objectAltitude={0.012}
          objectThreeObject={tokenOrb}
          objectLabel={p => `<div class="globe-point-tooltip" style="padding:7px 10px;background:#0a0f0d;border:1px solid ${p.color};border-radius:8px;color:#fff;font-family:sans-serif;font-size:12px;box-shadow:0 0 12px ${p.color}80;"><b>${escapeHtml(p.token.symbol)}</b> · ${escapeHtml(p.token.chain)}<br/>${fmtCap(p.token.marketCap)} ${p.token.mcKind === 'FDV' ? 'FDV' : 'MC'}${Number.isFinite(Number(p.token.change24h)) ? ` · ${Number(p.token.change24h) >= 0 ? '+' : ''}${Number(p.token.change24h).toFixed(1)}% 24h` : ''}</div>`}
          onObjectClick={p => { if (onToken) { onToken(p.token); return; } if (p.token.pairAddress) window.open(`/terminal/trade?chain=${encodeURIComponent(p.token.chain)}&pair=${encodeURIComponent(p.token.pairAddress)}`, '_blank', 'noopener'); }}
          onObjectHover={p => { document.body.style.cursor = p ? 'pointer' : 'default'; }}
          htmlElementsData={bubbles}
          htmlLat="lat"
          htmlLng="lng"
          htmlAltitude={0.12}
          htmlElement={bubbleElement}
        />
      </GlobeErrorBoundary>
    </div>
  );
}
