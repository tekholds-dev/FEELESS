import React, { useEffect, useRef, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { Ic3 } from '../../lib/icon3d';
import { load2d, peopleFile, thumbOf } from '../../lib/wireface';
import '../../styles/chatStyles.css';

// 💬 HOW ITS CHAT LOOKS (owner 2026-11-05): the patterns people already know, plus just the agent, sitting there blinking, answering in bubbles. A look only: saved in this browser.
export const CHAT_STYLES = [['classic', 'Classic', 'Avatars and names, the way it started'], ['clean', 'Clean', 'Plain answers down the middle, like an AI chat'], ['bubbles', 'Bubbles', 'Colored bubbles, like a messenger'], ['feed', 'Feed', 'One post after another, like a timeline'], ['agent', 'Just the agent', 'Its character and thought bubbles, nothing else']];
const DEFAULTS = { style: 'classic', theme: 'auto', motion: true };
const key = id => `feeless.chatStyle.${id}`;
export function useChatStyle(id) {
  const [p, setP] = useState(() => { try { return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(key(id)) || '{}') }; } catch { return DEFAULTS; } });
  const set = patch => setP(x => { const n = { ...x, ...patch }; try { localStorage.setItem(key(id), JSON.stringify(n)); } catch { /* it still works for this visit */ } return n; });
  return [p, set];
}
export const chatClass = p => `chs-${p.style} chs-t-${p.theme}${p.motion ? '' : ' chs-still'}`;
export function ChatStylePicker({ value, set }) {
  return <section className="chs-pick" data-testid="chat-style"><em>CHAT LOOK</em><div className="chs-opts" role="radiogroup" aria-label="Chat look">{CHAT_STYLES.map(([k, l, t]) => <button key={k} type="button" role="radio" aria-checked={value.style === k} className={value.style === k ? 'is-on' : ''} onClick={() => set({ style: k })} data-tip={t} data-testid={`chs-${k}`}><i className={`chs-mini is-${k}`} aria-hidden="true"><u /><u /><u /></i><span>{l}</span></button>)}</div>
    <div className="chs-row"><span className="m-seg" role="group" aria-label="Chat theme">{[['auto', 'Match site'], ['day', 'Day'], ['night', 'Night']].map(([k, l]) => <button key={k} type="button" className={value.theme === k ? 'active' : ''} aria-pressed={value.theme === k} onClick={() => set({ theme: k })} data-testid={`chs-theme-${k}`}>{l}</button>)}</span><label className="chs-check" data-tip="New messages slide in"><input type="checkbox" checked={!!value.motion} onChange={e => set({ motion: e.target.checked })} data-testid="chs-motion" /> Animations</label></div></section>;
}
// Its real character, idling and blinking. No character picked, or no WebGL: its still picture, or its mind.
function Character({ cat }) {
  const stage = useRef(null); const [live, setLive] = useState(false); const id = cat?.face?.id;
  useEffect(() => { if (!id) return undefined; let dead = false; let face; (async () => { try { const sdk = await load2d(); if (dead || !stage.current) return; face = sdk.createFace2d(stage.current); if (id === 'custom') { const r = await fetch(apiUrl(`/api/cats/${cat.id}/face/character`)); await face.useCharacter(await sdk.loadCharacter(await r.arrayBuffer())); } else if (peopleFile(id)) await face.useCharacter(await sdk.loadCharacter(peopleFile(id))); else await face.useCharacter(id); if (!dead) { face.view.start(); setLive(true); } } catch { if (!dead) setLive(false); } })(); return () => { dead = true; try { face?.view?.stop(); } catch { /* it had stopped */ } }; }, [id, cat?.id]);
  return <div className="chs-char" data-testid="chs-character"><div ref={stage} className={`chs-face${live ? ' is-live' : ''}`} />{!live ? (id ? <img src={id === 'custom' ? apiUrl(thumbOf(id, cat.id)) : thumbOf(id)} alt={`${cat?.name || 'Agent'}'s character`} /> : <span className="chs-orb"><Ic3 e="🧠" size="64px" /></span>) : null}<i className="chs-floor" aria-hidden="true" /></div>;
}
export function AgentStage({ cat, msgs, working, onChip }) {
  const rows = (msgs || []).slice(-3); const last = rows[rows.length - 1];
  return <div className="chs-stage" data-testid="chs-stage"><div className="chs-thoughts" aria-live="polite">{rows.map((m, i) => <p key={`${m.at || i}${String(m.text).slice(0, 12)}`} className={`chs-th ${m.by === 'you' ? 'is-you' : 'is-it'}${i === rows.length - 1 ? ' is-now' : ''}`} style={{ '--i': rows.length - 1 - i }}>{String(m.text).slice(0, 420)}</p>)}{working ? <p className="chs-th is-it is-now is-think" data-testid="chs-think"><i /><i /><i /></p> : null}{!rows.length && !working ? <p className="chs-th is-it is-now">Ask me anything.</p> : null}</div>
    {last?.ask?.chips?.length && onChip ? <span className="cwb-chips">{last.ask.chips.map(c => <button key={c} type="button" className="m-chip" onClick={() => onChip(c)}>{c}</button>)}</span> : null}<Character cat={cat} /></div>;
}
