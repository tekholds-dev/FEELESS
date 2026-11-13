import { useEffect, useState } from 'react';
import { apiUrl } from './api';
import { parseSse } from './agentHub';

// 📡 COMP LIVE (COMP-1): ONE stream per page of COMP's real numbers (GET /admin/model-lab/live, Server-Sent Events over fetch so the HQ
// session rides in headers). A frame arrives only when a number moved; a dead socket (45 s of silence) or the server's 30-min cap reconnects
// after a short wait. No stream (signed out, a test, a buffering proxy) = the frame stays null and the pages keep their own reads.
const SESSION_KEY = 'feeless:cc-session';
const IDLE_MS = 45000; const RETRY_MS = 4000;
const session = () => { try { const s = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); return s && s.address && s.sig ? s : null; } catch (e) { return null; } };

const S = { frame: null, live: false, subs: new Set(), abort: null, users: 0, retry: null };
const emit = () => S.subs.forEach(f => f());

async function run() {
  const s = session();
  if (!s || typeof fetch !== 'function' || typeof TextDecoder === 'undefined' || S.abort) return;
  const ac = new AbortController(); S.abort = ac; let dog = null;
  try {
    const res = await fetch(apiUrl('/api/reputation/admin/model-lab/live'), { signal: ac.signal, headers: { 'x-admin-address': s.address, 'x-admin-ts': String(s.ts), 'x-admin-sig': s.sig, Accept: 'text/event-stream' } });
    if (!res.ok || !res.body || !res.body.getReader) throw new Error(`stream ${res.status}`);
    const rd = res.body.getReader(); const dec = new TextDecoder(); let buf = ''; let heard = Date.now();
    dog = setInterval(() => { if (Date.now() - heard > IDLE_MS) { try { ac.abort(); } catch (e) { /* closed */ } } }, 5000);
    for (;;) {
      const { done, value } = await rd.read(); if (done) break;
      heard = Date.now(); buf += dec.decode(value, { stream: true });
      const [evs, rest] = parseSse(buf); buf = rest;
      evs.forEach(e => { if (e.kind === 'hello') { S.live = true; emit(); } else if (e.kind === 'frame') { const { kind, seq, ...fr } = e; S.frame = fr; S.live = true; emit(); } });   // eslint-disable-line no-unused-vars
    }
  } catch (e) { /* no stream: the pages keep their own reads */ } finally { if (dog) clearInterval(dog); }
  if (S.abort === ac) S.abort = null;
  if (S.live) { S.live = false; emit(); }
  if (S.users > 0 && !ac.signal.aborted) S.retry = setTimeout(() => { S.retry = null; if (S.users > 0) run(); }, RETRY_MS);
}

/** → { frame, live }: the latest COMP live frame (null until one arrives) and whether the stream is connected. */
export function useCompLive() {
  const [, tick] = useState(0);
  useEffect(() => {
    const f = () => tick(n => n + 1); S.subs.add(f); S.users += 1; if (!S.abort && !S.retry) run();
    return () => { S.subs.delete(f); S.users -= 1; if (S.users <= 0) { S.users = 0; if (S.retry) { clearTimeout(S.retry); S.retry = null; } if (S.abort) { try { S.abort.abort(); } catch (e) { /* closed */ } S.abort = null; } } };
  }, []);
  return { frame: S.frame, live: S.live };
}
