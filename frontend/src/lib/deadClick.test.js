import { blockerAt, installDeadClick, describe as desc } from './deadClick';

const ptr = (type, el, x = 5, y = 5) => { const e = new MouseEvent(type, { bubbles: true, cancelable: true, clientX: x, clientY: y, button: 0 }); el.dispatchEvent(e); };

afterEach(() => { document.body.innerHTML = ''; delete document.elementsFromPoint; delete document.elementFromPoint; });

test('a non-control layer over a real button is the blocker; a modal shade or a pointer-cursor div is not', () => {
  document.body.innerHTML = '<div id="wrap"><button data-testid="go">Go</button></div><div class="glow-layer" id="layer"></div><div class="m-shade" id="shade"></div><div id="tap" style="cursor:pointer"></div>';
  const btn = document.querySelector('button');
  document.elementsFromPoint = () => [document.getElementById('layer'), btn, document.getElementById('wrap'), document.body];
  const b = blockerAt(1, 1);
  expect(desc(b.layer)).toBe('div.glow-layer'); expect(desc(b.control)).toBe('button[go]');
  document.elementsFromPoint = () => [document.getElementById('shade'), btn, document.body];
  expect(blockerAt(1, 1)).toBeNull();
  document.elementsFromPoint = () => [document.getElementById('tap'), btn, document.body];
  expect(blockerAt(1, 1)).toBeNull();
  document.elementsFromPoint = () => [btn, document.body];
  expect(blockerAt(1, 1)).toBeNull();   // the press reached the control
});

test('a press on a covered control is filed once; a control remounted under the press still gets its click', async () => {
  const filed = [];
  document.body.innerHTML = '<div id="layer"></div><div id="row"><button data-testid="ack-iv-5m">5m</button></div>';
  installDeadClick({ report: t => filed.push(t) });
  const layer = document.getElementById('layer'); const old = document.querySelector('button');
  document.elementsFromPoint = () => [layer, old, document.body];
  ptr('pointerdown', layer); ptr('pointerdown', layer);
  expect(filed).toEqual(['[dead click] div sits over button[ack-iv-5m] — the press never reached it']);
  // remount: pointerdown on the old button, a live tick swaps it for a new one, pointerup over the new one
  document.elementsFromPoint = () => [old, document.body];
  ptr('pointerdown', old);
  const fresh = document.createElement('button'); fresh.dataset.testid = 'ack-iv-5m'; const onClick = jest.fn(); fresh.addEventListener('click', onClick);
  old.replaceWith(fresh); document.elementFromPoint = () => fresh;
  ptr('pointerup', fresh); ptr('click', document.getElementById('row'));   // the browser sends the click to the common parent
  await new Promise(r => setTimeout(r, 5));
  expect(onClick).toHaveBeenCalledTimes(1);
  expect(filed[1]).toContain('re-rendered under the press');
});
