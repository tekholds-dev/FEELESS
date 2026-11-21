import React, { useEffect, useMemo, useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { AnimatePresence, motion } from 'motion/react';
import '../../styles/proofWorkspace.css';   // the --pws-* type lights
import '../../styles/startWizard.css';

// 🧭 THE START WIZARD (Slice 33, owner 2026-11-20 night: "before a PoC, PoEco or PoStatic job starts, instead of the drop of long text, it can
// pop out a 3-step window"). 1 · Direction: the brief, the goal and the minds' pitch; he approves it or writes his own. 2 · Kits and what to
// start from. 3 · Research: COMP, OSSY or G4 search the web first, or the minds search as they work, with the minds and the cost shown before
// Go. Every choice goes to the server with the start (`tools.wizard`), is checked there (start_wizard.clean), reaches the engine and is kept
// on the filed proof's record (STARTED WITH in its true record). Nothing here decides anything on its own.

const STEPS = [['direction', 'Direction'], ['kits', 'Kits'], ['research', 'Research']];
const usd = v => (v == null ? '—' : Number(v) < 0.01 ? `$${Number(v).toFixed(4)}` : `$${Number(v).toFixed(2)}`);
const SLIDE = { enter: d => ({ x: d * 28, opacity: 0 }), at: { x: 0, opacity: 1 }, exit: d => ({ x: d * -28, opacity: 0 }) };

/** <StartWizard open cat work kind job typed onGo onClose goLabel/>: onGo(wizard) starts the job and may throw (its message shows here). */
export function StartWizard({ open, cat, work, kind, job = '', typed = '', onGo, onClose, goLabel = 'Go' }) {
  const [o, setO] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  const [step, setStep] = useState(0); const [dir, setDir] = useState(1);
  const [text, setText] = useState(''); const [kits, setKits] = useState([]); const [start, setStart] = useState('fresh'); const [by, setBy] = useState('minds');
  useEffect(() => {
    if (!open) return undefined;
    let on = true; setO(null); setErr(''); setStep(0); setText(''); setStart('fresh'); setBy('minds');
    work(cat.id, { op: 'wizard_opts', text: kind, job, cap: typed || '' }).then(j => { if (!on) return; setO(j.wizard); setKits(j.wizard?.mode === 'mine' ? j.wizard.picks || [] : []); })
      .catch(e => on && setErr(e.message));
    return () => { on = false; };
  }, [open, cat?.id, kind, job, typed]);   // eslint-disable-line react-hooks/exhaustive-deps -- `work` is a new function each render
  const pitch = useMemo(() => (o?.pitch || []).join(' · '), [o]);
  const go = n => { setDir(n > step ? 1 : -1); setStep(n); };
  const kitName = id => o?.kits?.find(k => k.id === id)?.name || id;
  const flip = id => setKits(ks => (ks.includes(id) ? ks.filter(k => k !== id) : ks.length >= (o?.max || 3) ? ks : [...ks, id]));
  const fire = async () => {
    setBusy(true); setErr('');
    try { await onGo({ direction: { text: text.trim(), pitch, approved: true }, kits, start, research: { by } }); onClose(); }
    catch (e) { setErr(e.message); } finally { setBusy(false); }
  };
  const res = o?.research?.find(r => r.by === by);
  const minds = [...(o?.minds || []), ...(res?.mind ? [res.mind] : [])];
  const startRow = o?.starts?.find(s => s.id === start);
  const body = !o ? <p className="swz-wait" data-testid="swz-wait">{err ? `⚠ ${err}` : 'Reading the brief, the kits and its record…'}</p>
    : step === 0 ? <div className="swz-pane" data-testid="swz-step-direction">
      <dl className="swz-brief"><div><dt>BRIEF</dt><dd data-testid="swz-brief">{o.brief || '—'}</dd></div>{o.goal ? <div><dt>GOAL</dt><dd>{o.goal}</dd></div> : null}</dl>
      {o.pitch?.length ? <section className="swz-pitch" aria-label="The minds' pitch"><h4>THE PITCH</h4><ol>{o.pitch.map((p, i) => <li key={p} style={{ '--i': i }}>{p}</li>)}</ol></section> : null}
      <label className="swz-edit"><span>YOUR DIRECTION <small>optional: leave it empty to approve the pitch as it is</small></span>
        <textarea className="m-input" rows={3} maxLength={600} value={text} onChange={e => setText(e.target.value)} placeholder="Change anything: the angle, the audience, the price, what must be in it…" data-testid="swz-direction" /></label>
    </div>
    : step === 1 ? <div className="swz-pane" data-testid="swz-step-kits">
      <section className="swz-sec"><h4>KITS <small>{kits.length ? `${kits.length} of ${o.max}` : 'its own pick'}</small></h4>
        <div className="swz-chips" role="group" aria-label="Kits for this job">
          <button type="button" className={`swz-chip${!kits.length ? ' is-on' : ''}`} aria-pressed={!kits.length} onClick={() => setKits([])} data-tip="The agent picks the kits for this ask, as it always does" data-testid="swz-kit-auto">Let it pick</button>
          {o.kits.map(k => <button key={k.id} type="button" className={`swz-chip${kits.includes(k.id) ? ' is-on' : ''}`} aria-pressed={kits.includes(k.id)} disabled={!kits.includes(k.id) && kits.length >= o.max} onClick={() => flip(k.id)}
            data-tip={`${k.what || k.name}${k.cat ? ` · ${k.cat}` : ''}`} data-testid={`swz-kit-${k.id}`}>{k.name}</button>)}</div></section>
      <section className="swz-sec"><h4>START FROM</h4><div className="swz-starts" role="radiogroup" aria-label="What it starts from">
        {[{ id: 'fresh', label: 'Fresh', sub: 'A new footprint, nothing carried' }, ...(o.starts || [])].map(s => <button key={s.id} type="button" role="radio" aria-checked={start === s.id} className={`swz-start${start === s.id ? ' is-on' : ''}`} onClick={() => setStart(s.id)} data-testid={`swz-start-${s.id}`}>
          <b>{s.label}{s.good ? <em data-tip="This one worked">✓</em> : null}</b><small>{s.sub || '—'}</small></button>)}</div></section>
    </div>
    : <div className="swz-pane" data-testid="swz-step-research">
      <div className="swz-res" role="radiogroup" aria-label="Who researches first">{o.research.map(r => <button key={r.by} type="button" role="radio" aria-checked={by === r.by} className={`swz-ropt${by === r.by ? ' is-on' : ''}`} onClick={() => setBy(r.by)} data-testid={`swz-research-${r.by}`}>
        <b>{r.label}</b><small>{r.tip}</small><em>{Number(r.usd) > 0 ? usd(r.usd) : 'free'}</em></button>)}</div>
      <section className="swz-sum" aria-label="Before Go" data-testid="swz-summary">
        <span><small>MINDS</small><b data-testid="swz-minds">{minds.join(' + ') || 'none set'}</b></span>
        <span data-tip={o.cost?.n ? `The median of its last ${o.cost.n} filed of this kind, plus the research pass` : 'Nothing filed yet to measure from'}><small>COST</small><b className="swz-hot" data-testid="swz-cost">{o.cost?.usd != null ? `≈ ${usd(o.cost.usd + (res?.usd || 0))}` : 'first one'}</b></span>
        <span><small>KITS</small><b>{kits.length ? kits.map(kitName).join(', ') : 'its own pick'}</b></span>
        <span><small>START</small><b>{startRow ? startRow.label : 'Fresh'}</b></span>
        <span className="swz-sum-dir"><small>DIRECTION</small><b>{text.trim() || 'As pitched'}</b></span>
      </section>
    </div>;
  return <Dialog.Root open={open} onOpenChange={v => { if (!v && !busy) onClose(); }}>
    <Dialog.Portal><Dialog.Overlay className="swz-back" />
      <Dialog.Content className={`swz is-${kind}`} data-testid="swz" aria-describedby={undefined} onOpenAutoFocus={e => e.preventDefault()}>
        <header className="swz-h"><Dialog.Title className="swz-t"><i aria-hidden="true" />Start a {o?.label || 'job'}</Dialog.Title>
          <ol className="swz-steps">{STEPS.map(([k, l], i) => <li key={k} className={`${i < step ? 'is-done' : ''}${i === step ? ' is-now' : ''}`}><button type="button" disabled={!o || i > step} onClick={() => go(i)} data-testid={`swz-to-${k}`}><i>{i < step ? '✓' : i + 1}</i>{l}</button></li>)}</ol>
          <Dialog.Close className="swz-x" aria-label="Close the start wizard" data-tip="Close. Nothing starts" data-testid="swz-close">✕</Dialog.Close></header>
        <div className="swz-body"><AnimatePresence mode="wait" initial={false} custom={dir}><motion.div key={o ? step : 'wait'} custom={dir} variants={SLIDE} initial="enter" animate="at" exit="exit" transition={{ duration: 0.16 }}>{body}</motion.div></AnimatePresence></div>
        {err && o ? <p className="swz-err" role="alert" data-testid="swz-err">⚠ {err}</p> : null}
        <footer className="swz-f">{step > 0 ? <button type="button" className="m-btn" onClick={() => go(step - 1)} data-testid="swz-backstep">Back</button> : <span />}
          {step === 0 ? <button type="button" className="m-btn m-go" disabled={!o} onClick={() => go(1)} data-tip={text.trim() ? 'Your direction goes to the minds word for word' : 'Approve the pitch as it is'} data-testid="swz-approve">{text.trim() ? 'Approve my direction' : 'Approve the pitch'} →</button>
            : step === 1 ? <button type="button" className="m-btn m-go" onClick={() => go(2)} data-testid="swz-next">Next →</button>
              : <button type="button" className="m-btn m-go" disabled={busy} onClick={fire} data-tip="Starts the job with every choice above, kept on its record" data-testid="swz-go">{busy ? 'Starting…' : goLabel}</button>}</footer>
      </Dialog.Content></Dialog.Portal>
  </Dialog.Root>;
}
