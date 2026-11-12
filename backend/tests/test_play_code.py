"""💻 The 3D code playground: a mind's reply becomes a module, and a filed module is a locked page that loads only three.js."""
import play_studio as ps


def test_code_reply_takes_the_js_block_and_refuses_non_three():
    code, say = ps.code_reply("```js\nimport * as THREE from 'three';\nconst s = new THREE.Scene();\n```\nA quiet scene.")
    assert code.startswith("import * as THREE") and say == 'A quiet scene.'
    assert ps.code_reply('Sorry, I cannot.')[0] == '' and ps.code_reply('```js\nconsole.log(1)\n```')[0] == ''


def test_code_page_is_locked_and_loads_three_only():
    page = ps.code_page("import * as THREE from 'three'; '</script>'", 'My <b>scene</b>')
    assert 'Content-Security-Policy' in page and 'three@0.170.0' in page and '<script type="module">' in page
    assert '</script>\'' not in page and '<b>scene' not in page and 'connect-src https' not in page


def test_nova_black_cause_html_page_and_cut_reply():
    """AGT-17: NOVA opened black — the mind sent a whole ```html page, cut off by its length cap, and the old reader ran the prose as code."""
    import play_studio as ps
    raw = ("Here's a complete document.\n```html\n<!DOCTYPE html><html><head><script type=\"importmap\">{}</script></head><body>"
           "<script type=\"module\">\nimport * as THREE from 'https://unpkg.com/three@0.170.0/build/three.module.js';\n"
           "import { OrbitControls } from 'https://unpkg.com/three@0.170.0/examples/jsm/controls/OrbitControls.js';\n"
           "const r = new THREE.WebGLRenderer();\nfunction make(n) {\n  for (let i = 0; i < n; i++) {")
    code, _ = ps.code_reply(raw)
    assert code.startswith("import * as THREE from 'three';") and "'three/addons/controls/OrbitControls.js'" in code
    assert "Here's" not in code and '<html' not in code and ps.code_cut(code)
    whole, say = ps.code_reply("```html\n<html><body><script type=\"module\">\nimport * as THREE from 'three';\nnew THREE.Scene();\n</script></body></html>\n```\nA scene.")
    assert whole == "import * as THREE from 'three';\nnew THREE.Scene();" and not ps.code_cut(whole) and say == 'A scene.'
    assert ps.code_reply("Sure! I used new THREE.Mesh for it.")[0] == ''   # prose is never run as code
    assert not ps.code_cut("const s = '{ ( [';  // {\nfunction a() { return `${1}`; }")
