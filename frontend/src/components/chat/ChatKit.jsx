import React from 'react';
import { Button, Popover, Surface, TextArea } from '@heroui/react';
import { ArrowUp, Plus, Settings2, Square } from 'lucide-react';
import '../../styles/chatKit.css';

// 💬 THE chat composer (owner 2026-11-05): one box, built from HeroUI, for every chat on the site. Each chat passes its own tools and settings.
export function ChatComposer({ className = '', onSubmit, field, tools, action }) {
  return <form className={`ckit-composer ${className}`} onSubmit={onSubmit}>
    <Surface variant="secondary" className="ckit-box">
      <div className="ckit-field">{field}</div>
      <div className="ckit-bar">{tools}<span className="ckit-grow" />{action}</div>
    </Surface>
  </form>;
}
export const ChatInput = React.forwardRef(function ChatInput({ className = '', ...props }, ref) {
  return <TextArea ref={ref} rows={1} variant="primary" fullWidth className={`ckit-in ${className}`} {...props} />;
});
export function ChatAttach({ busy = false, ...props }) {
  return <Button isIconOnly variant="ghost" size="sm" className={`ckit-tool${busy ? ' is-busy' : ''}`} {...props}><Plus size={17} aria-hidden="true" /></Button>;
}
export function ChatSend(props) {
  return <Button isIconOnly type="submit" size="sm" aria-label="Send" className="ckit-send" {...props}><ArrowUp size={17} aria-hidden="true" /></Button>;
}
export function ChatStop(props) {
  return <Button isIconOnly size="sm" variant="secondary" aria-label="Stop" className="ckit-stop" {...props}><Square size={13} fill="currentColor" aria-hidden="true" /></Button>;
}
// ⚙ settings: HeroUI's popover, opened from the composer's own bar. The chat passes what's inside.
export function ChatSettings({ open, onOpen, tip, testid, label = 'Chat settings', panelTestid, children }) {
  return <Popover isOpen={open} onOpenChange={onOpen}>
    <Button isIconOnly variant="ghost" size="sm" aria-label={label} data-tip={tip} data-testid={testid} className={`ckit-tool${open ? ' is-on' : ''}`}><Settings2 size={16} aria-hidden="true" /></Button>
    <Popover.Content placement="top start" offset={10} className="ckit-pop">
      <Popover.Dialog aria-label={label} className="ckit-pop-in" data-testid={panelTestid}>{children}</Popover.Dialog>
    </Popover.Content>
  </Popover>;
}
