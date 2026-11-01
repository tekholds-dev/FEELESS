import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';

// 💬 a chat that follows its newest message (owner 2026-11-02: "new text should auto scroll to bottom, or an arrow to go to the bottom"):
// at the bottom → every new message scrolls into view; scrolled up to read → it stays put and counts what arrived, the ↓ button jumps down.
export function useStickToBottom(ref, count) {
  const atBottom = useRef(true); const last = useRef(count); const [unseen, setUnseen] = useState(0);
  useEffect(() => { const el = ref.current; if (!el) return undefined;
    const on = () => { atBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 60; if (atBottom.current) setUnseen(0); };
    el.addEventListener('scroll', on, { passive: true }); return () => el.removeEventListener('scroll', on); }, [ref]);
  useLayoutEffect(() => { const el = ref.current; const grew = count > last.current; last.current = count;
    if (!el) return;
    if (atBottom.current) el.scrollTop = el.scrollHeight;
    else if (grew) setUnseen(n => n + 1); }, [ref, count]);
  const jump = useCallback(() => { const el = ref.current; if (el) { el.scrollTop = el.scrollHeight; atBottom.current = true; } setUnseen(0); }, [ref]);
  return [unseen, jump];
}
