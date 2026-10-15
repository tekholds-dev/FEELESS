import { deckMeters } from './AgentCockpit';

test('deck tab meters come from the payload: trades won share, agents active share, feed freshness; missing = no meter', () => {
  const o = { tradeTape: { rows: [{ result: 4 }, { result: -2 }, { result: 1 }, {}] }, generations: [{ status: 'ACTIVE' }, { status: 'ACTIVE' }, { status: 'PROBATION' }, { status: 'ACTIVE' }],
    tape: [{ at: 1000 }] };
  const out = deckMeters(o, [['live', '⚡ Feed', 1, null], ['tape', '🎬 Trades', 4, null], ['agents', '🧩 Desk', 4, null], ['brain', '🧠 Brain', null, null]], 1030);
  const by = Object.fromEntries(out.map(t => [t[0], t]));
  expect(by.tape[4]).toBeCloseTo(2 / 3); expect(by.tape[5]).toBe('2 of 3 closed real trades won');
  expect(by.agents[4]).toBe(0.75); expect(by.live[4]).toBe(1); expect(by.brain[4]).toBeNull(); expect(by.brain[5]).toBeNull();
  expect(deckMeters({ tape: [{ at: 1 }] }, [['live', '⚡ Feed', 1, null]], 1 + 600)[0][4]).toBe(0);   // ten quiet minutes = an empty meter
});
