import fix_agent as fa


def test_before_picture_shoots_the_live_page_and_says_why_on_failure(tmp_path):
    seen = []
    def shoot(url, out):
        seen.append(url); out.write_bytes(b'jpg'); return ''
    assert fa.before_picture('pick-is-not-defined', '/terminal/feecat/agents', shoot_=shoot, shots=tmp_path) == {'before': 'pick-is-not-defined-before.jpg', 'beforeWhy': ''}
    assert seen == ['http://localhost:51367/terminal/feecat/agents']
    assert fa.before_picture('x', 'https://evil.example//x', shoot_=lambda u, o: 'Timeout', shots=tmp_path) == {'before': None, 'beforeWhy': 'Timeout'}
    assert fa.page_path('https://evil.example/x') == '/' and fa.page_path('//evil') == '/'


def test_after_picture_serves_the_branch_shoots_and_always_stops_it(tmp_path):
    stopped = []
    class P:
        pid = 1
    def serve(tree, port):
        assert str(tree).endswith('fix-x') and port == fa.SHOT_PORT
        return P(), ''
    real_stop = fa.stop
    fa.stop = lambda p: stopped.append(p)
    try:
        got = fa.after_picture('case-1', '/familia', tmp_path / 'fix-x', shoot_=lambda u, o: (o.write_bytes(b'j'), '')[1] if u == 'http://127.0.0.1:51398/familia' else 'wrong url', serve=serve, busy=lambda: False, shots=tmp_path)
        assert got == {'after': 'case-1-after.jpg', 'afterWhy': ''} and len(stopped) == 1
        boom = lambda u, o: (_ for _ in ()).throw(RuntimeError('crash'))
        try:
            fa.after_picture('case-2', '/', tmp_path / 'fix-x', shoot_=boom, serve=serve, busy=lambda: False, shots=tmp_path)
        except RuntimeError:
            pass
        assert len(stopped) == 2   # a failed shot still stops the preview server
    finally:
        fa.stop = real_stop
    assert fa.after_picture('c', '/', tmp_path, busy=lambda: True)['afterWhy'].startswith('The machine was busy')
    assert fa.after_picture('c', '/', tmp_path, serve=lambda t, p: (None, 'Its preview did not start'), busy=lambda: False) == {'after': None, 'afterWhy': 'Its preview did not start'}


def test_serve_tree_uses_its_own_cache_and_port_and_gives_up(tmp_path):
    calls = {}
    class Proc:
        pid = 7
        def poll(self): return None
    def popen(cmd, cwd, env, **k):
        calls.update(cmd=cmd, cwd=cwd, env=env, k=k); return Proc()
    proc, why = fa.serve_tree(tmp_path, 51398, wait=10, popen=popen, ready=lambda u: True, nap=lambda s: None)
    assert why == '' and calls['cmd'] == ['yarn', 'start'] and calls['cwd'].endswith('frontend') and calls['env']['PORT'] == '51398'
    assert calls['env']['FEELESS_WEBPACK_CACHE'].startswith(str(tmp_path)) and calls['env']['BROWSER'] == 'none' and calls['k']['start_new_session']
    real_stop = fa.stop; fa.stop = lambda p: None
    try:
        assert fa.serve_tree(tmp_path, 51398, wait=0, popen=popen, ready=lambda u: False, nap=lambda s: None)[0] is None
    finally:
        fa.stop = real_stop
