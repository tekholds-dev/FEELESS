import React, { useState } from 'react';
import { toast } from 'sonner';
import { Bug } from 'lucide-react';
import { apiUrl } from '../lib/api';

// Public "Report a bug" box (every profile). Lives outside HQ so the HQ code never ships to traders.
export function ReportBug({ address }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const [kind, setKind] = useState('bug');
  const send = async () => {
    const res = await fetch(apiUrl('/api/reputation/bugs'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, kind, page: window.location.pathname, address }) });
    const b = await res.json().catch(() => ({}));
    if (!res.ok) { toast.error(b.detail || 'Could not send.'); return; }
    toast.success('Sent to FEELESS HQ — thank you!'); setText(''); setOpen(false);
  };
  if (!open) return <button type="button" className="btn-outline wp-report" onClick={() => setOpen(true)}><Bug size={13} />Report a bug</button>;
  return <div className="wp-report-box"><select value={kind} onChange={e => setKind(e.target.value)}><option value="bug">🐞 Bug</option><option value="security">🔐 Security issue</option><option value="idea">💡 Idea</option></select>
    <textarea rows={3} maxLength={2000} placeholder="What happened? What did you expect?" value={text} onChange={e => setText(e.target.value)} />
    <div><button type="button" className="btn-primary" disabled={text.trim().length < 5} onClick={send}>Send</button><button type="button" className="btn-outline" onClick={() => setOpen(false)}>Cancel</button></div></div>;
}

