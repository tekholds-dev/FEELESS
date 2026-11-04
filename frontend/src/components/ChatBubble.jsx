import React from 'react';
import '../styles/chatBubble.css';

// 💬 One message shell for every chat (Trench, Street, Messenger): your own lines sit on the right as `is-mine`, long text wraps. Each chat keeps its own palette and contents.
export function ChatBubble({ as: Tag = 'div', mine = false, className = '', children, ...rest }) {
  return <Tag className={`cb ${mine ? 'is-mine' : ''} ${className}`.trim()} {...rest}>{children}</Tag>;
}
