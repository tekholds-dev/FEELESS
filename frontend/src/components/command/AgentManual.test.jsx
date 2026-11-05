import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { AgentManual } from './AgentManual';

test('📖 the manual maps the whole system, puts a command in chat, and has no paragraphs of text', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const sent = [];
  await act(async () => { root.render(<AgentManual d={{ kernel: { v: '1', hash: 'abc', groups: [{ name: 'Budget', rows: [['Dollars a coin', 0.03]] }] } }} onCommand={c => sent.push(c)} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  for (const part of ['Chat', 'Two minds', 'PoW', 'PoP', 'PoB', 'Proofs folder', 'Proof Loop', 'Fingerprint']) expect(q('am-tutorial').textContent).toContain(part);
  await act(async () => { q('am-node-pop').click(); });
  expect(q('am-detail').textContent).toContain('No real order is sent');
  await act(async () => { q('am-try').click(); }); expect(sent).toEqual(['file a perp']);
  await act(async () => { q('am-start-mail').click(); }); expect(q('am-detail').textContent).toContain('Make its mailbox');
  for (const k of ['kinds', 'pow', 'pop', 'print', 'limits', 'code', 'tutorial']) {
    if (!q(`am-tab-${k}`)) await act(async () => { q('am-more').click(); });
    await act(async () => { q(`am-tab-${k}`).click(); });
    expect(el.querySelector('p')).toBeNull();
    [...el.querySelectorAll('small')].forEach(s => expect(s.textContent.split(' ').length).toBeLessThan(26));
  }
  await act(async () => { q('am-tab-limits').click(); }); expect(q('am-limits').textContent).toContain('0.03');
  await act(async () => { root.unmount(); }); el.remove();
});
