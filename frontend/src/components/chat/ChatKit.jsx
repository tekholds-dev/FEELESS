import React, { useEffect, useImperativeHandle, useLayoutEffect, useRef, useState } from 'react';
import { Button, Popover, Surface, TextArea } from '@heroui/react';
import { ArrowUp, Mic, Plus, Settings2, Square, Volume2 } from 'lucide-react';
import '../../styles/chatKit.css';

// 💬 THE chat composer (owner 2026-11-05): one box, built from HeroUI, for every chat on the site. Each chat passes its own tools and settings.
export function ChatComposer({ className = '', onSubmit, above = null, field, tools = null, action, testid, autoComplete }) {
  return <form className={`ckit-composer ${className}`.trim()} onSubmit={onSubmit} data-testid={testid} autoComplete={autoComplete}>
    {above}
    <Surface variant="secondary" className="ckit-box">
      <div className="ckit-field">{field}</div>
      <div className="ckit-bar">{tools}<span className="ckit-grow" /><ChatMic />{action}</div>
    </Surface>
  </form>;
}
// 🎙 AGT-6 voice to text, in every chat (it lives in the composer): the browser's own speech recognition writes into the box as you talk;
// tap again to stop. Shown only where the browser has it. The words go through the field's normal onChange, so each chat's state stays its own.
const speechOf = () => (typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : null);
export function typeInto(field, text) {
  const set = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(field), 'value')?.set; if (set) set.call(field, text); else field.value = text;
  field.dispatchEvent(new Event('input', { bubbles: true }));
}
export function ChatMic() {
  const [on, setOn] = useState(false); const [err, setErr] = useState(''); const rec = useRef(null); const btn = useRef(null);
  useEffect(() => () => { try { rec.current?.abort(); } catch { /* already stopped */ } }, []);
  if (!speechOf()) return null;
  const flip = () => {
    if (on) { rec.current?.stop(); return; }
    const field = btn.current?.closest('form')?.querySelector('textarea, input[type="text"], input:not([type])'); if (!field) return;
    const R = speechOf(); const r = new R(); rec.current = r; r.continuous = true; r.interimResults = true; r.lang = navigator.language || 'en-US';
    const base = field.value ? `${field.value.replace(/\s+$/, '')} ` : ''; setErr('');
    r.onresult = e => { voiced = true; let said = ''; for (let i = 0; i < e.results.length; i++) said += e.results[i][0].transcript; typeInto(field, base + said); };
    r.onerror = e => setErr(e.error === 'not-allowed' ? 'Allow the microphone for this site to talk to it' : e.error === 'no-speech' ? '' : `Voice stopped: ${e.error}`);
    r.onend = () => { setOn(false); field.focus(); };
    try { r.start(); setOn(true); } catch { setOn(false); }
  };
  return <ChatTool ref={btn} className={`ckit-mic${on ? ' is-on' : ''}${err ? ' is-err' : ''}`} onPress={flip} aria-pressed={on} aria-label={on ? 'Stop listening' : 'Talk instead of typing'} data-tip={err || (on ? 'Listening. Tap to stop' : 'Talk instead of typing')} data-testid="ckit-mic"><Mic size={16} aria-hidden="true" /></ChatTool>;
}
// 🔊 AGT-6 speaking back: the browser's own voices (the most natural one it has: Siri / Google / "Natural" / "Premium"). A question asked
// by mic gets its answer read out (takeVoiced); every answer has a Listen button. Links and [source] tags are skipped when read.
let voiced = false;
export const takeVoiced = () => { const v = voiced; voiced = false; return v; };
export const canSpeak = () => typeof window !== 'undefined' && !!window.speechSynthesis && typeof window.SpeechSynthesisUtterance === 'function';
const NATURAL = /natural|neural|premium|enhanced|siri|google/i;
function bestVoice() {
  const lang = (navigator.language || 'en').slice(0, 2); const vs = window.speechSynthesis.getVoices().filter(v => (v.lang || '').startsWith(lang));
  return vs.find(v => NATURAL.test(v.name)) || vs.find(v => v.default) || vs[0] || null;
}
export const speakable = text => String(text || '').replace(/\[[^\]]*\]/g, '').replace(/https?:\/\/\S+/g, 'link').replace(/[*_`#>|]/g, '').replace(/\s+/g, ' ').trim().slice(0, 1800);
export function speak(text, onEnd) {
  if (!canSpeak()) return false; const s = window.speechSynthesis; const said = speakable(text); s.cancel(); if (!said) return false;
  const u = new window.SpeechSynthesisUtterance(said); const v = bestVoice(); if (v) { u.voice = v; u.lang = v.lang; } u.rate = 1.05;
  u.onend = u.onerror = () => onEnd?.(); s.speak(u); return true;
}
export function SpeakBtn({ text, testid, className = '' }) {
  const [on, setOn] = useState(false);
  useEffect(() => () => { if (on) window.speechSynthesis?.cancel(); }, [on]);
  if (!canSpeak()) return null;
  return <button type="button" className={`${className}${on ? ' is-on' : ''}`} aria-pressed={on} onClick={() => { if (on) { window.speechSynthesis.cancel(); setOn(false); } else setOn(speak(text, () => setOn(false))); }}
    data-tip={on ? 'Stop reading' : 'Read this answer out loud'} data-testid={testid}><Volume2 size={12} aria-hidden="true" /> {on ? 'Stop' : 'Listen'}</button>;
}
const CAN_GROW = typeof CSS !== 'undefined' && CSS.supports?.('field-sizing', 'content');
// Long text wraps and the box grows (up to its max, then it scrolls). Enter sends, Shift+Enter is a new line.
export const ChatInput = React.forwardRef(function ChatInput({ className = '', enterSends = true, onKeyDown, value, ...props }, ref) {
  const el = useRef(null);
  useImperativeHandle(ref, () => el.current);
  useLayoutEffect(() => { const t = el.current; if (!t || CAN_GROW) return; t.style.height = 'auto'; t.style.height = `${t.scrollHeight}px`; }, [value]);
  const keys = e => {
    onKeyDown?.(e);
    if (e.defaultPrevented || !enterSends || e.key !== 'Enter' || e.shiftKey || e.nativeEvent?.isComposing) return;
    e.preventDefault(); const f = e.currentTarget.form; if (!f) return;
    if (f.requestSubmit) f.requestSubmit(); else f.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  };
  return <TextArea ref={el} rows={1} variant="primary" fullWidth className={`ckit-in ${className}`.trim()} value={value} onKeyDown={keys} {...props} />;
});
export const ChatTool = React.forwardRef(function ChatTool({ className = '', children, ...props }, ref) {
  return <Button ref={ref} isIconOnly variant="ghost" size="sm" className={`ckit-tool ${className}`.trim()} {...props}>{children}</Button>;
});
export function ChatAttach({ busy = false, ...props }) {
  return <ChatTool className={busy ? 'is-busy' : ''} {...props}><Plus size={17} aria-hidden="true" /></ChatTool>;
}
export function ChatSend({ children, ...props }) {
  return <Button isIconOnly={!children} type="submit" size="sm" aria-label="Send" className={`ckit-send${children ? ' has-text' : ''}`} {...props}>{children || <ArrowUp size={17} aria-hidden="true" />}</Button>;
}
export function ChatStop(props) {
  return <Button isIconOnly size="sm" variant="secondary" aria-label="Stop" className="ckit-stop" {...props}><Square size={13} fill="currentColor" aria-hidden="true" /></Button>;
}
// ⚙ settings: HeroUI's popover, opened from the composer's own bar. The chat passes what's inside.
export function ChatSettings({ open, onOpen, tip, testid, label = 'Chat settings', panelTestid, placement = 'top start', icon = null, children }) {
  return <Popover isOpen={open} onOpenChange={onOpen}>
    <ChatTool aria-label={label} data-tip={tip} data-testid={testid} className={open ? 'is-on' : ''}>{icon || <Settings2 size={16} aria-hidden="true" />}</ChatTool>
    <Popover.Content placement={placement} offset={10} className="ckit-pop">
      <Popover.Dialog aria-label={label} className="ckit-pop-in" data-testid={panelTestid}>{children}</Popover.Dialog>
    </Popover.Content>
  </Popover>;
}
