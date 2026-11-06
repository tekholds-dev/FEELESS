import React, { useImperativeHandle, useLayoutEffect, useRef } from 'react';
import { Button, Popover, Surface, TextArea } from '@heroui/react';
import { ArrowUp, Plus, Settings2, Square } from 'lucide-react';
import '../../styles/chatKit.css';

// 💬 THE chat composer (owner 2026-11-05): one box, built from HeroUI, for every chat on the site. Each chat passes its own tools and settings.
export function ChatComposer({ className = '', onSubmit, above = null, field, tools = null, action, testid, autoComplete }) {
  return <form className={`ckit-composer ${className}`.trim()} onSubmit={onSubmit} data-testid={testid} autoComplete={autoComplete}>
    {above}
    <Surface variant="secondary" className="ckit-box">
      <div className="ckit-field">{field}</div>
      <div className="ckit-bar">{tools}<span className="ckit-grow" />{action}</div>
    </Surface>
  </form>;
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
export function ChatTool({ className = '', children, ...props }) {
  return <Button isIconOnly variant="ghost" size="sm" className={`ckit-tool ${className}`.trim()} {...props}>{children}</Button>;
}
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
