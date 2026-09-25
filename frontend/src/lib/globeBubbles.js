import { useEffect, useState } from 'react';
import { apiUrl } from './api';

const ROTATE_MS = 15000;
const MAX_BUBBLES = 5;

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
  const tape = await getJson(`/api/intelligence/tape?chain=${encodeURIComponent(node.chainId)}`);
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
      for (let i = 0; i < nodes.length && batch.length < MAX_BUBBLES; i++) {
        const node = nodes[(offset + i) % nodes.length];
        const item = await latestFor(node);
        if (item) batch.push({ ...item, id: `${node.id}-${Date.now()}`, lat: node.lat, lng: node.lng, color: node.color, name: node.name });
      }
      offset = (offset + MAX_BUBBLES) % Math.max(1, nodes.length);
      if (alive) setBubbles(batch);
    };
    tick();
    const timer = setInterval(tick, ROTATE_MS);
    return () => { alive = false; clearInterval(timer); };
  }, [nodes]);
  return bubbles;
}
