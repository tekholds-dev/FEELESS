import React, { useEffect } from 'react';
import { ProofWorkspace, MindsThread } from '../components/command/ProofWorkspace';
import { TaskCard, TaskChatProvider, TaskStrip, useTaskChats } from '../components/desk/TaskChat';
import FIX from './taskChatFixture.json';   // 🧵 Slice 35: Happy's REAL TEST task chat (tccacb76dbd4, split off PoW #17 $AI, gpt-6.1-terra, $0.0126) + that folder's minds' lines
import '../styles/agentDemo.css';
import '../styles/catWorkbench.css';
import '../styles/deskLook.css';

// 🧪 DEV ONLY (`/dev/taskchat`, never in a production build): a task chat on Happy's real data, inside the real PoW filing workspace.
// ?live = the same real task replayed at step 2 of 3 (doing spinner, the newest thought open) · ?day = day theme · ?w=700 = that wide.
// Every op is answered from the fixture: nothing reaches the server.
const Q = window.location.search; const LIVE = /[?&]live/.test(Q); const W = Number((Q.match(/[?&]w=(\d+)/) || [])[1]) || 0;
const T = LIVE ? FIX.live : FIX.done;
const card = ({ checklist, thoughts, logs, msgs, brief, model, cap, created, started, ended, ...c }) => c;
const call = async b => {
  if (b.op === 'task_list') return { tasks: [card(T)], parallel: 1 };
  if (b.op === 'task_get') return { task: T };
  throw new Error('Harness only: nothing is sent from this page.');
};
function OpenIt() { const ctx = useTaskChats(); useEffect(() => { ctx.open(T.id); }, []); return null; }   // eslint-disable-line react-hooks/exhaustive-deps

export default function TaskChatHarness() {
  useEffect(() => { document.body.classList.toggle('theme-day', /[?&]day/.test(Q)); }, []);
  const f = FIX.folder;
  return <TaskChatProvider call={call}><OpenIt />
    <div style={{ padding: 16, maxWidth: W || undefined, minHeight: '100vh', background: 'var(--m-bg)', color: 'var(--m-text)', display: 'grid', gap: 12, alignContent: 'start' }}>
      <ProofWorkspace id="dev-task-pow" kind="pow" name={`PoW #${f.n} · $${f.sym}`} status="filed" taskRef={f.id} chat={<MindsThread rows={(f.talk || []).slice(-6).map(t => ({ by: t.by, text: t.text }))} />} chatLabel="Discussion">
        <div style={{ padding: 12, display: 'grid', gap: 8 }}><b>{FIX.agent} · the chat it came from</b>
          {FIX.chat.map((m, i) => <div key={i} className="dkl-msg"><small>{m.by === 'you' ? 'You' : FIX.agent}</small><p style={{ whiteSpace: 'pre-line', margin: '2px 0' }}>{m.text}</p>{m.task ? <TaskCard c={card(T)} /> : null}</div>)}
          <TaskStrip scope="desk" hideEmpty /></div>
      </ProofWorkspace>
    </div>
  </TaskChatProvider>;
}
