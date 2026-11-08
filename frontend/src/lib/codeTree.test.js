import { TextEncoder } from 'util';
import { codeTree, zipBytes } from './codeTree';

global.TextEncoder = global.TextEncoder || TextEncoder;

test('a built page splits into its pages, styles and scripts, and index.html stays the whole page', () => {
  const html = '<!doctype html><html><head><style>h1{color:red}</style><script src="https://cdn.x/k.js"></script></head><body><main data-page="home"><h1>Home</h1></main><main data-page="1" hidden><h2>The Room</h2></main><script>go()</script></body></html>';
  const f = codeTree(html); const paths = f.map(x => x.path);
  expect(paths).toEqual(['index.html', 'pages/home.html', 'pages/the-room.html', 'styles/style-1.css', 'scripts/script-1.js', 'kits.txt']);
  expect(f[0].text).toBe(html);
});

test('the tree saves as a real zip: signature, one entry per file, end record', () => {
  const b = zipBytes([{ path: 'index.html', text: '<p>hi</p>' }, { path: 'styles/a.css', text: 'p{}' }]);
  expect([...b.slice(0, 4)]).toEqual([0x50, 0x4b, 0x03, 0x04]);
  const end = b.length - 22; expect([...b.slice(end, end + 4)]).toEqual([0x50, 0x4b, 0x05, 0x06]); expect(b[end + 10]).toBe(2);
});
