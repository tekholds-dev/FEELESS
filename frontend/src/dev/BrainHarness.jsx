import React, { useCallback, useRef } from 'react';
import { AiChat } from '../components/command/AiChat';
import { STUDIO } from '../components/command/__fixtures__/promptStudio';
import { desk } from '../components/command/__fixtures__/modelDesk';

// 🧪 DEV ONLY (`/dev/brain`, never in a production build — index.js imports it behind NODE_ENV): the Brain on fixtures — Talk with a settings
// line that becomes 🎛 rig proposals, and Brain › Models = the LM Studio rig (OSSY MLX loaded, G4 GGUF). No backend touched.
const lms = { local: { model: 'openai/gpt-oss-20b', name: 'openai/gpt-oss-20b', fmt: 'mlx', maxCtx: 131072, sizeGb: 12.1, params: '20B', loaded: [{ id: 'openai/gpt-oss-20b', ctx: 7659, par: 2 }] },
  lan: { model: 'qwen/qwen3-4b-2507', name: 'qwen/qwen3-4b-2507', fmt: 'gguf', maxCtx: 262144, sizeGb: 2.5, params: '4B', loaded: [{ id: 'qwen/qwen3-4b-2507', ctx: 8704, par: 2, flash: 1, kv: 1, batch: 512 }] } };
const rig0 = { lan: { ctx: 0, parallel: 2, timeout: 90, perMin: 4, load: {} }, local: { ctx: 0, parallel: 1, timeout: 60, perMin: 4, load: { ctx: 16384 } }, win: { ctx: 4096, parallel: 1, timeout: 240, perMin: 2, every: 900 } };
const NAMES = { lan: 'G4', local: 'OSSY' };
export default function BrainHarness() {
  const st = useRef({ rig: JSON.parse(JSON.stringify(rig0)), chat: { temp: 0.3, len: 'normal' }, props: [], th: { chat: [{ role: 'user', text: 'yo how are the agents doing' }, { role: 'assistant', text: 'Desk is flat: 3 seats, +4.1% today [agents]. Weak link = Trigger, 2 late entries. Lever: tighten the germ gate.' }] } });
  const view = () => { const s = st.current;
    const rows = ['lan', 'local'].map(k => { const r = s.rig[k]; const lm = lms[k]; const cur = lm?.loaded?.[0] || {};
      const diff = r.load ? Object.fromEntries(Object.entries(r.load).filter(([f, v]) => cur[f] !== v).map(([f, v]) => [f, [cur[f], v]])) : undefined;
      return { key: k, name: NAMES[k], ...r, cmd: `lms load ${lm.model} --context-length ${r.load?.ctx || 8192} --parallel ${r.load?.par || 1} -y`, ...(r.load ? { lms: lm, diff } : {}) }; });
    return { rows, options: { ctx: [0, 2048, 4096, 8192, 12288, 16384, 32768], parallel: [1, 2, 3, 4], timeout: [30, 45, 60, 90, 120, 180, 240, 300], perMin: [2, 4, 6, 8, 12], every: [180, 300, 600, 900] },
      loadOptions: { ctx: [4096, 8192, 12288, 16384, 24576, 32768, 65536], par: [1, 2, 3, 4], flash: [0, 1], kv: [0, 1], batch: [256, 512, 1024, 2048] },
      live: { lan: { state: 'ONLINE', lastMs: 2100 }, local: { state: 'ONLINE', lastMs: 6400 }, win: { state: 'ONLINE', lastMs: 9000 } },
      chat: { ...s.chat, temps: [0.1, 0.3, 0.6, 0.9], lens: { short: 250, normal: 600, long: 1200 } }, reloading: [] }; };
  const props = () => ({ pending: st.current.props.filter(p => p.status === 'pending'), decided: st.current.props.filter(p => p.status !== 'pending') });
  const call = useCallback(async (u, o) => { const s = st.current; const b = o?.body ? JSON.parse(o.body) : null;
    await new Promise(r => setTimeout(r, 120));
    if (u === '/admin/ai/models') return desk({ lan: s.rig.lan.infer, local: s.rig.local.infer, win: s.rig.win.infer });   // 🧠 Model Desk on fixtures
    if (u === '/admin/ai/prompts') { if (b) s.studio = { ...(s.studio || STUDIO), models: (s.studio || STUDIO).models.map(m => (m.key !== b.key ? m : 'auto' in b ? { ...m, auto: { ...m.auto, on: b.auto } }
      : { ...m, active: b.revert ? null : { set: b.set, text: b.text || '', at: Date.now() / 1000, edited: !!b.text, since: { n: 0 } } })) };
      return s.studio || STUDIO; }   // 🎭 Prompt Studio on fixtures
    if (u === '/admin/ai/rig') { if (b?.reload) return { ...view(), reload: { ok: true, ms: 9100 } };
      if (b) Object.entries(b).forEach(([k, row]) => { if (row?.infer) { s.rig[k].infer = Object.fromEntries(Object.entries({ ...(s.rig[k].infer || {}), ...row.infer }).filter(([, v]) => v != null)); return; } if (row?.load) s.rig[k].load = { ...s.rig[k].load, ...row.load }; else Object.assign(s.rig[k], row); }); return view(); }
    if (u === '/admin/ai/chat/settings') { Object.assign(s.chat, b); return { ok: true, settings: s.chat }; }
    if (u === '/admin/ai/calls') return { inflight: [] };
    if (u === '/admin/ai/proposals/decide') { const p = s.props.find(x => x.id === b.id); p.status = b.approve ? 'approved' : 'rejected'; if (b.approve) p.applied = p.key.endsWith('.load') ? 'OSSY reloaded in 9.1s — LM Studio reports 16K context · ×1 at once' : 'live now'; return { ok: true, applied: p.applied, proposals: props() }; }
    if (u === '/admin/ai/chat' && b) { const at = Date.now();
      const items = [{ id: `p${at}1`, kind: 'rig', agent: 'desk', key: 'local.load', old: 'ctx=7659 par=2', new: 'ctx=16384 par=1', reason: `you said: "${b.text}"`, effect: 'OSSY loads with 16K context · ×1 at once (reloads OSSY)', rollback: 'set it back in Brain › Models', status: 'pending' },
        { id: `p${at}2`, kind: 'rig', agent: 'desk', key: 'chat.temp', old: 0.3, new: 0.6, reason: `you said: "${b.text}"`, effect: 'Brain chat temperature 0.6', rollback: 'set it back in Brain › Models', status: 'pending' }];
      s.props = [...items, ...s.props]; const reply = '🎛 2 model changes waiting for your ✅: OSSY loads with 16K context · ×1 at once (reloads OSSY) · Brain chat temperature 0.6. A load change reloads that model once you approve it.';
      s.th.chat = [...s.th.chat, { role: 'user', text: b.text }, { role: 'assistant', text: reply }];
      return { ok: true, mode: 'chat', reply, provider: '🎛 rig', ms: 0, threads: s.th, new: items.map(x => x.id), proposals: props(), rig: true }; }
    if (u === '/admin/ai/chat') return { threads: s.th, settings: s.chat, saved: [], proposals: props(), providers: [{ key: 'local', label: 'OSSY', state: 'ONLINE', model: 'openai/gpt-oss-20b' }, { key: 'lan', label: 'G4', state: 'ONLINE', model: 'qwen/qwen3-4b-2507' }], brain: { provider: 'OSSY', model: 'gpt-oss-20b', ms: 6400 }, learned: 14, build: { open: 2, items: [] } };
    return {}; }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  return <div style={{ minHeight: '100vh', boxSizing: 'border-box', padding: 16, background: '#050806', color: '#dfe' }}>
    <h2 className="m-label">🧪 DEV PREVIEW · the Brain + LM Studio rig</h2>
    <div style={{ maxWidth: 1180, margin: '0 auto' }}><AiChat call={call} isOwner /></div>
  </div>;
}
