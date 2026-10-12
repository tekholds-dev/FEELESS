"""⚙ The trench kernel — ONE MintState per mint, ONE candidate lifecycle, ONE ten-agent brain, four hunter lanes, measured latency.
   state.py   MintState + candidate states + the deduping, event-emitting store
   brain.py   the ten pure agent opinions + the reducer + the lanes (philosophy: trench_crew.py)
   kernel.py  events → only the affected mints re-judged → decisions; `KERNEL` is the process's one instance
   lifecycle.py  ONE generation record for all ten roles (four desks + office desks)
The legacy desk (agents.py: Tally's tape, Sherlock's drivers, Trigger's chart read, Devil's objections) feeds rows in; the kernel decides."""
