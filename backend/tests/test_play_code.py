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
