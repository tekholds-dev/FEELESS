"""🪦 The owner's own 3D models for a build (owner 2026-11-17: "choose a model … have them tweak it … add to the trench build filing so they
use the new 3D tombstone throughout the site"). A real model picked and set in the 3D studio is kept on one PoStatic folder; that folder's
builds then carry that exact model: placed on the set by code in a 3D build, mounted live by code in every marked spot of a page build.
Pure: no network, no store."""
import html as _html
import json
import math
import re

import asset_packs as _assets
import play_studio as _play

MAX = 6        # models one build carries
MOUNTS = 8     # live models one page draws at once (a browser allows ~16 WebGL contexts)


def _id(v):
    return re.sub(r'[^\w-]', '', str(v or ''))[:60]


def take(obj, now, where=''):
    """A model on the studio's stage → the row a build keeps: the real file plus the owner's tweaks (size, turn, spin), never its place."""
    rows = _play.clean_scene({'objects': [obj]})['objects'] if isinstance(obj, dict) else []
    o = rows[0] if rows else None
    if not o or not o.get('asset'):
        raise ValueError('Pick a real model on the stage first.')
    return {'id': _id(o['asset'].get('id')) or _id(o['id']), 'name': o['name'], 'obj': {**o, 'pos': [0, 0, 0]}, 'from': ' '.join(str(where or '').split())[:40], 'at': round(now)}


def clean(rows):
    """Only rows whose model is still a real, allowed file (each read is checked again: the folder is data)."""
    out = []
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict) or not isinstance(r.get('obj'), dict):
            continue
        got = _play.clean_scene({'objects': [r['obj']]})['objects']
        if got and got[0].get('asset') and _id(r.get('id')):
            out.append({'id': _id(r['id']), 'name': got[0]['name'], 'obj': {**got[0], 'pos': [0, 0, 0]}, 'from': str(r.get('from') or '')[:40], 'at': int(r.get('at') or 0)})
    return out[-MAX:]


def add(rows, row):
    """The same model again replaces its old tweaks."""
    return clean([*[r for r in clean(rows) if r['id'] != row['id']], row])


def drop(rows, rid):
    return [r for r in clean(rows) if r['id'] != _id(rid)]


def view(rows):
    return [{'id': r['id'], 'name': r['name'], 'height': r['obj'].get('height') or 0, 'turn': round(r['obj']['rot'][1] * 180 / math.pi), 'spin': r['obj'].get('spin') or 0, 'from': r['from'], 'at': r['at']} for r in clean(rows)]


def on_set(scene, rows):
    """A 3D build: each of the owner's models stands on the set (in front, side by side) unless the scene already has that exact file."""
    rows = clean(rows)
    if not rows:
        return scene
    have = {(o.get('asset') or {}).get('url') for o in scene.get('objects') or []}
    new = [r for r in rows if r['obj']['asset']['url'] not in have]
    put = [{**r['obj'], 'id': f'own{i}', 'pos': [round((i - (len(new) - 1) / 2) * 1.6, 2), 0, 1.4]} for i, r in enumerate(new)]
    return {**scene, 'objects': (_play.clean_scene({'objects': put})['objects'] + list(scene.get('objects') or []))[:_play.MAX_OBJECTS]}


def scene_line(rows):
    rows = clean(rows)
    return ('\nTHE OWNER\'S OWN MODELS ARE ALREADY ON THE SET (exact files, placed by code): ' + ', '.join(r['name'] for r in rows)
            + '. They are the theme of this build: shape the mood, props and words around them, and never ask for another of them as hero or prop.') if rows else ''


def page_line(rows):
    rows = clean(rows)
    if not rows:
        return ''
    ids = '; '.join(f'"{r["id"]}" = {r["name"]}' for r in rows)
    return ('\nTHE OWNER\'S OWN 3D MODELS (picked and set in the 3D studio): use each one, this exact model, throughout the site: in the hero and in at '
            'least two more places where it fits the design (section breaks, cards, the footer). Mark each place with an empty element sized by your CSS, '
            f'and code puts the live model in it: <div data-feeless-model="ID"></div>. IDs: {ids}. Never draw, photograph or emoji a stand-in for it, and '
            'never write your own loader for it.')


_RUN = """import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
const M = __MODELS__, first = Object.keys(M)[0], still = matchMedia('(prefers-reduced-motion: reduce)').matches;
[...document.querySelectorAll('[data-feeless-model]')].slice(0, __MOUNTS__).forEach(el => {
  const m = M[el.dataset.feelessModel] || M[first]; if (!m) return;
  if (getComputedStyle(el).position === 'static') el.style.position = 'relative';
  if (el.clientHeight < 40) el.style.minHeight = '240px';
  let r; try { r = new THREE.WebGLRenderer({ antialias: true, alpha: true }); } catch (e) { el.dataset.feelessModelOff = 'no-webgl'; el.title = m.name; return; }   // a browser with no 3D keeps the page working and the rest of its spots
  r.setPixelRatio(Math.min(devicePixelRatio, 2));
  Object.assign(r.domElement.style, { position: 'absolute', inset: '0', width: '100%', height: '100%' }); el.appendChild(r.domElement);
  const s = new THREE.Scene(); s.add(new THREE.HemisphereLight(0xffffff, 0x223344, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 2.2); sun.position.set(3, 5, 4); s.add(sun);
  const cam = new THREE.PerspectiveCamera(35, 1, 0.01, 200), turn = new THREE.Group(); s.add(turn);
  const fit = () => { const w = el.clientWidth || 1, h = el.clientHeight || 1; r.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix(); };
  const lm = new THREE.LoadingManager(); lm.setURLModifier(u => (m.files || {})[decodeURI(u.split('/').pop().split('?')[0])] || u);
  new GLTFLoader(lm).load(m.url, g => { const o = g.scene; o.scale.set(m.shape[0], m.shape[1], m.shape[2]);   // its proportions as set in the studio (a squash or stretch stays)
    const box = new THREE.Box3().setFromObject(o), size = box.getSize(new THREE.Vector3()), big = Math.max(size.x, size.y, size.z) || 1;
    o.position.sub(box.getCenter(new THREE.Vector3())); turn.add(o); turn.rotation.set(m.rot[0], m.rot[1], m.rot[2]); cam.position.set(0, big * 0.15, big * 2.2); cam.lookAt(0, 0, 0); fit(); el.dataset.feelessModelOn = m.name; });
  new ResizeObserver(fit).observe(el); fit();
  let seen = false; new IntersectionObserver(e => { seen = e[0].isIntersecting; }).observe(el);
  const clock = new THREE.Clock();
  r.setAnimationLoop(() => { const dt = clock.getDelta(); if (!seen || document.hidden) return; if (!still && m.spin) turn.rotation.y += dt * m.spin * Math.PI / 30; r.render(s, cam); });
});"""
_OLD = re.compile(r'<script type="module" id="feeless-models">.*?</script>', re.S)


def _shape(scale):
    """The studio's scale as proportions only (largest side = 1): a page frames the model to its spot, so a uniform size never shrinks it to a dot."""
    v = [abs(float(x or 0)) or 1.0 for x in (list(scale or [])[:3] + [1, 1, 1])[:3]]; big = max(v)
    return [round(x / big, 4) for x in v]


_SPOT = re.compile(r'<div data-feeless-model="[^"]*" data-feeless-spot="code"[^>]*></div>')


def mount(html, rows):
    """A page build: the live model goes into every spot the page marked (data-feeless-model). A page that marked none gets one under its header,
    so the model is never missing. Run again on each version: the old copy of this code is replaced, never doubled. Taken out of the build, its
    code, credit line and the spot code put in leave the page too. → html"""
    h = re.sub(r'<p id="feeless-models-by"[^>]*>.*?</p>', '', _OLD.sub('', str(html or '')), flags=re.S); rows = clean(rows)
    if not rows:
        return _SPOT.sub('', h)
    if 'data-feeless-model' not in h:
        spot = f'<div data-feeless-model="{rows[0]["id"]}" data-feeless-spot="code" role="img" aria-label="{_html.escape(rows[0]["name"])}" style="height:min(56vh,480px)"></div>'
        at = h.find('</header>')
        if at >= 0:
            h = h[:at + 9] + spot + h[at + 9:]
        else:
            h = re.sub(r'(<body[^>]*>)', lambda m: m.group(1) + spot, h, count=1)
    data = {r['id']: {'name': r['name'], 'url': r['obj']['asset']['url'], 'files': r['obj']['asset'].get('files') or {}, 'rot': r['obj']['rot'], 'spin': r['obj'].get('spin') or 0,
                      'shape': _shape(r['obj'].get('scale')), 'height': r['obj'].get('height') or 0} for r in rows}
    code = _RUN.replace('__MODELS__', json.dumps(data).replace('<', '\\u003c')).replace('__MOUNTS__', str(MOUNTS))
    by = _assets.credits([{'objects': [r['obj'] for r in rows]}])   # a CC-BY model's creator is named, as its licence asks (CC0 needs none)
    tag = (f'<p id="feeless-models-by" style="font:12px system-ui;opacity:.6;text-align:center;margin:12px">3D: {_html.escape(by)}</p>' if by else '') + f'<script type="module" id="feeless-models">\n{code}\n</script>'
    return h.replace('</body>', tag + '</body>', 1) if '</body>' in h else h + tag


def mounted(html):
    """The models a page really carries, read back from its own code (never from the folder's wish list). → {id: {url, rot, spin, shape, height}}"""
    m = re.search(r'<script type="module" id="feeless-models">\s*import[^\n]*\n[^\n]*\nconst M = (\{.*?\}), first =', str(html or ''), re.S)
    try:
        got = json.loads(m.group(1)) if m else {}
    except ValueError:
        return {}
    return got if isinstance(got, dict) else {}


def record(rows, html):
    """🧾 The studio pieces a filed PoStatic was given, each with the exact tweaks it carries and whether its page really mounts THAT piece
    (same file, same turn and spin). → [{id, name, url, height, turn, spin, used}]"""
    on = mounted(html); out = []
    for r in clean(rows):
        o = r['obj']; got = on.get(r['id']) or {}
        out.append({'id': r['id'], 'name': r['name'], 'url': o['asset']['url'], 'height': o.get('height') or 0, 'turn': o['rot'], 'spin': o.get('spin') or 0,
                    'used': got.get('url') == o['asset']['url'] and got.get('rot') == o['rot'] and (got.get('spin') or 0) == (o.get('spin') or 0)})
    return out


def place(html, rows):
    """🪦 The page the folder has NOW, with the owner's models put in (or taken out) by code: no mind, no cost. Its lock lets three.js and the
    model's one host through, and every kit the page already carried keeps loading. → html (unchanged when there is nothing to change)"""
    import collective_kits as _kits
    h = mount(html, rows)
    if h == str(html or ''):
        return h
    return _kits.open_for_kits(_kits.with_kit_tags(h, ['three']) if clean(rows) else h)
