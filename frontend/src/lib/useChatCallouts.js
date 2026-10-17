import { useEffect, useState } from 'react';
import { callsFor } from './callout';
// the chat's /callout rows for this pool, live (one window event, no fetch)
export function useChatCallouts(pair) {
  const [rows, setRows] = useState(() => (pair ? callsFor(pair) : []));
  useEffect(() => {
    if (!pair) return undefined; setRows(callsFor(pair));
    const on = e => { if (e.detail?.pair === pair) setRows(e.detail.rows || []); };
    window.addEventListener('feeless:callouts', on); return () => window.removeEventListener('feeless:callouts', on);
  }, [pair]);
  return rows;
}
