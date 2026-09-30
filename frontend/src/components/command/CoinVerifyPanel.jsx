import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { errorText } from '../../lib/api';
import { shortAddress } from '../../lib/dexscreener';
import { clearVerified } from '../../lib/verifyBatch';
import { VerifyReport } from '../VerifyReport';

// Command Center › Verify: run the checks on any coin, grant the gold check, or revoke one (revoke always wins).
export function CoinVerifyPanel({ call }) {
  const [d, setD] = useState({ manual: [], requests: [], auto: [] });
  const [mint, setMint] = useState('');
  const [run, setRun] = useState(0);
  const [note, setNote] = useState('');
  const load = useCallback(() => call('/admin/coin-verify').then(setD).catch(e => toast.error(errorText(e))), [call]);
  useEffect(() => { load(); }, [load]);
  const valid = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(mint);
  const act = async (m, action) => {
    try { await call('/admin/coin-verify', { method: 'POST', body: JSON.stringify({ mint: m, action, note }) }); clearVerified(m); toast.success({ grant: 'Gold check granted.', revoke: 'Check revoked site-wide.', clear: 'Back to automatic.' }[action]); setNote(''); setRun(x => x + 1); load(); }
    catch (e) { toast.error(errorText(e)); }
  };
  const open = m => { setMint(m); setRun(x => x + 1); };
  return <section className="cc-panel coin-verify" data-testid="coin-verify">
    <details className="tr-explain"><summary>✓ How coins earn the check</summary>
      <ul><li><b>Green ✓ (earned):</b> passes all 5 safety gates (mint + freeze revoked, creator not flagged, 24h+ trading, $25K+ liquidity) and scores {70}+ on 8 cited checks (locked LP, holder spread, insiders, dev bag, socials, real volume, two-sided flow, 72h+).</li>
        <li><b>Gold ✦ (granted):</b> official FEELESS coins, or coins you review and grant here.</li>
        <li><b>Revoke</b> removes any check site-wide instantly, even an earned one. Checks re-run every 6h, so a coin that turns bad loses it on its own.</li>
        <li>The check shows on the coin's logo everywhere: radar, chat, search, charts, profiles.</li></ul></details>
    <div className="cv-run"><input placeholder="Paste a coin mint to check" value={mint} onChange={e => setMint(e.target.value.trim())} /><button type="button" className="btn-primary" disabled={!valid} onClick={() => setRun(x => x + 1)}>Run checks</button></div>
    {valid && run > 0 && <div className="cc-block"><VerifyReport key={`${mint}-${run}`} mint={mint} fresh={run} />
      <div className="cv-actions"><input placeholder="Note (shown on revoke / grant)" maxLength={200} value={note} onChange={e => setNote(e.target.value)} />
        <button type="button" className="btn-primary" onClick={() => act(mint, 'grant')}>✦ Grant gold</button><button type="button" className="btn-outline cv-danger" onClick={() => act(mint, 'revoke')}>✕ Revoke</button><button type="button" className="btn-outline" onClick={() => act(mint, 'clear')}>Automatic</button></div></div>}
    <div className="cv-grid">
      <div className="cc-block"><h4>Review requests <em>{d.requests.length}</em></h4>{!d.requests.length ? <p className="cc-empty">No open requests.</p> : d.requests.map(r => <button type="button" key={r.mint + r.at} className="cv-row" onClick={() => open(r.mint)}><code>{shortAddress(r.mint)}</code><span>{r.note || 'No note'}</span><small>by {shortAddress(r.by)}</small></button>)}</div>
      <div className="cc-block"><h4>Granted / revoked</h4>{!d.manual.length ? <p className="cc-empty">Nothing set by hand.</p> : d.manual.map(m => <button type="button" key={m.mint} className="cv-row" onClick={() => open(m.mint)}><code>{shortAddress(m.mint)}</code><span className={m.state === 'granted' ? 'cv-gold' : 'cv-bad'}>{m.state === 'granted' ? '✦ gold' : '✕ revoked'}</span><small>{m.note}</small></button>)}</div>
      <div className="cc-block"><h4>Recently earned ✓</h4>{!d.auto.length ? <p className="cc-empty">Checks run as coins appear on screen.</p> : d.auto.map(a => <button type="button" key={a.mint} className="cv-row" onClick={() => open(a.mint)}><code>{a.symbol ? `$${a.symbol}` : shortAddress(a.mint)}</code><span className="cv-ok">✓ {a.score}/100</span></button>)}</div>
    </div>
  </section>;
}
