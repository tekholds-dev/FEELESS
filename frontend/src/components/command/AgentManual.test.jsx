import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react-dom/test-utils';
import { AgentManual } from './AgentManual';

test('📖 the manual steps through a tutorial, puts a command in chat, and has no paragraphs of text', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const sent = [];
  await act(async () => { root.render(<AgentManual d={{ kernel: { v: '1', hash: 'abc', groups: [{ name: 'Budget', rows: [['Dollars a coin', 0.03]] }] } }} onCommand={c => sent.push(c)} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('am-tutorial').textContent).toContain('Open its desktop');
  for (let i = 0; i < 3; i += 1) await act(async () => { q('am-next').click(); });
  await act(async () => { q('am-try').click(); }); expect(sent).toEqual(['file a perp']);
  for (const k of ['kinds', 'pow', 'pop', 'print', 'limits', 'code', 'tutorial']) {
    await act(async () => { q(`am-tab-${k}`).click(); });
    expect(el.querySelector('p')).toBeNull();
    [...el.querySelectorAll('small')].forEach(s => expect(s.textContent.split(' ').length).toBeLessThan(26));
  }
  await act(async () => { q('am-tab-limits').click(); }); expect(q('am-limits').textContent).toContain('0.03');
  await act(async () => { root.unmount(); }); el.remove();
});
