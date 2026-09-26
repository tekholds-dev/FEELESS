import { useEffect, useState } from 'react';
import { apiUrl } from './api';

const ROTATE_MS = 15000;
const MAX_BUBBLES = 5;
const MAX_LOOKUPS = 6;
const tapeCache = new Map();

async function getJson(path) {
  try {
    const res = await fetch(apiUrl(path));
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

// One bubble per node, from real data only: the room's latest chat message if anyone
// has posted, otherwise the latest observed market signal on that chain.
async function latestFor(node) {
  const room = `${node.id}-general`;
  const chat = await getJson(`/api/chat/${encodeURIComponent(room)}`);
  const msg = chat?.messages?.[chat.messages.length - 1];
  if (msg?.text) return { kind: 'chat', who: msg.profile?.hidden ? 'anon' : msg.username, text: msg.text };
  if (!node.chainId) return null;
  const cached = tapeCache.get(node.chainId);
  const tape = cached && Date.now() - cached.at < 30000 ? cached.data : await getJson(`/api/intelligence/tape?chain=${encodeURIComponent(node.chainId)}`);
  if (!cached || Date.now() - cached.at >= 30000) tapeCache.set(node.chainId, { at: Date.now(), data: tape });
  const ev = tape?.events?.find(e => !e.chain || e.chain === node.chainId);
  if (ev?.title) return { kind: 'signal', who: ev.kind?.toLowerCase().replace(/_/g, ' ') || 'signal', text: ev.title };
  return null;
}

export function useGlobeBubbles(nodes) {
  const [bubbles, setBubbles] = useState([]);
  useEffect(() => {
    let alive = true;
    let offset = 0;
    const tick = async () => {
      const batch = [];
      for (let i = 0; i < Math.min(nodes.length, MAX_LOOKUPS) && batch.length < MAX_BUBBLES; i++) {
        const node = nodes[(offset + i) % nodes.length];
        const item = await latestFor(node);
        if (item) batch.push({ ...item, id: `${node.id}-${Date.now()}`, lat: node.lat, lng: node.lng, color: node.color, name: node.name });
      }
      offset = (offset + MAX_LOOKUPS) % Math.max(1, nodes.length);
      if (alive) setBubbles(batch);
    };
    tick();
    const timer = setInterval(() => { if (!document.hidden) tick(); }, ROTATE_MS);
    return () => { alive = false; clearInterval(timer); };
  }, [nodes]);
  return bubbles;
}
