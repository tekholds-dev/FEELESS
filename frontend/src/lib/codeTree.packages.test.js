import { packageOf } from './codeTree';

test('a page\'s kit links read as package, version, source and kind', () => {
  expect(packageOf('https://cdn.jsdelivr.net/npm/echarts@6.0.0/dist/echarts.min.js')).toMatchObject({ name: 'echarts', version: '6.0.0', from: 'cdn.jsdelivr.net', kind: 'script' });
  expect(packageOf('https://unpkg.com/@tsparticles/engine@3.9.1/tsparticles.engine.min.js')).toMatchObject({ name: '@tsparticles/engine', version: '3.9.1' });
  expect(packageOf('https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css')).toMatchObject({ name: 'animate.css', version: '4.1.1', kind: 'style' });
  expect(packageOf('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700')).toMatchObject({ name: 'Google Fonts', version: 'Space Grotesk', kind: 'style' });
  expect(packageOf('/assets/app.js')).toMatchObject({ name: 'app.js', version: '', from: 'this page' });
});
