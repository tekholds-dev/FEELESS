import React, { useState } from 'react';

// A small "?" that explains a number in plain words — hover, focus or tap.
export function Explain({ children, label = 'What is this?' }) {
  const [open, setOpen] = useState(false);
  return <span className="explain" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
    <button type="button" aria-label={label} aria-expanded={open} onClick={e => { e.preventDefault(); e.stopPropagation(); setOpen(o => !o); }} onBlur={() => setOpen(false)}>?</button>
    {open && <span role="tooltip" className="explain-tip">{children}</span>}
  </span>;
}
