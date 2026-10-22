"""🪟 NEXA runtime control: the Windows controller's validation / command / auth / apply, and the backend's desired-vs-actual view."""
import asyncio
import pytest
import ai_rig
import nexa_controller as nc

CONF = {'token': 'T' * 30, 'exe': r'C:\nexa\llamafile.exe', 'model': r'C:\nexa\Qwen2.5-1.5B-Instruct-Q4_K_M.gguf', 'host': '0.0.0.0', 'port': 8080}


def test_controller_only_takes_allowlisted_numbers():
    assert nc.validate({'ctx': 2048, 'parallel': 1}) == (2048, 1)
    assert nc.validate({'ctx': '4096', 'parallel': '2', 'exe': 'evil.exe', 'cmd': 'del *'}) == (4096, 2)   # extra keys are never read
    for bad in ({'ctx': 0, 'parallel': 1}, {'ctx': 2047, 'parallel': 1}, {'ctx': 2048, 'parallel': 5}, {'ctx': 32768, 'parallel': 2},
                {'ctx': 'x', 'parallel': 1}, [], None):
        with pytest.raises(ValueError):
            nc.validate(bad)


def test_command_is_an_argument_list_from_the_local_config_only():
    cmd = nc.command(CONF, 2048, 1)
    assert cmd[0] == CONF['exe'] and cmd[cmd.index('-m') + 1] == CONF['model']
    assert cmd[cmd.index('-c') + 1] == '2048' and cmd[cmd.index('-np') + 1] == '1'
    assert nc.command(CONF, 4096, 2)[nc.command(CONF, 4096, 2).index('-c') + 1] == '8192'     # per-slot ctx × slots
    assert all(isinstance(a, str) for a in cmd)


def test_auth_needs_the_exact_bearer_token():
    assert nc.authed('Bearer ' + 'T' * 30, 'T' * 30)
    assert not nc.authed('Bearer nope', 'T' * 30) and not nc.authed('', 'T' * 30) and not nc.authed('Bearer ', '')


def test_parse_actual_reads_per_slot_context_and_slot_count():
    props = {'default_generation_settings': {'n_ctx': 2048}, 'total_slots': 4, 'model_path': r'C:\nexa\Qwen2.5-1.5B-Instruct-Q4_K_M.gguf'}
    a = nc.parse_actual(props, [{'n_ctx': 2048}] * 4)
    assert a == {'ctx': 2048, 'slots': 4, 'model': 'Qwen2.5-1.5B-Instruct-Q4_K_M.gguf'} or a['model'].endswith('.gguf')
    assert nc.matches(a, 2048, 4) and not nc.matches(a, 2048, 1)


class FakeRt(nc.Runtime):
    def __init__(self, after):
        super().__init__(CONF); self.after = after; self.killed = 0; self.spawned = []; self.up = False
    def kill(self):
        self.killed += 1; self.up = False
    def spawn(self, ctx, par):
        self.spawned.append((ctx, par)); self.up = True
    def actual(self):
        return self.after if self.up else None


def test_apply_restarts_and_verifies(tmp_path, monkeypatch):
    monkeypatch.setattr(nc, 'STATE', tmp_path / 's.json')
    rt = FakeRt({'ctx': 2048, 'slots': 1, 'model': 'q.gguf'})
    r = nc.apply(rt, 2048, 1, sleep=lambda s: None)
    assert r['ok'] and r['verified'] and rt.killed == 1 and rt.spawned == [(2048, 1)]
    assert nc.load_state()['parallel'] == 1


def test_apply_refuses_when_the_old_llamafile_will_not_stop(tmp_path, monkeypatch):
    monkeypatch.setattr(nc, 'STATE', tmp_path / 's.json')
    rt = FakeRt({'ctx': 2048, 'slots': 4})
    rt.kill = lambda: None; rt.up = True              # the old one keeps answering
    t = [0.0]
    def clock():
        t[0] += 5; return t[0]
    r = nc.apply(rt, 2048, 1, sleep=lambda s: None, clock=clock)
    assert not r['ok'] and 'could not stop' in r['msg'] and rt.spawned == []


def test_apply_reports_a_mismatch_and_a_dead_start(tmp_path, monkeypatch):
    monkeypatch.setattr(nc, 'STATE', tmp_path / 's.json')
    t0 = [0.0]
    def clock0():
        t0[0] += 3; return t0[0]
    r = nc.apply(FakeRt({'ctx': 2048, 'slots': 4}), 2048, 1, sleep=lambda s: None, clock=clock0)
    assert not r['ok'] and 'differ' in r['msg']
    t = [0.0]
    def clock():
        t[0] += 50; return t[0]
    r2 = nc.apply(FakeRt(None), 2048, 1, sleep=lambda s: None, clock=clock)
    assert not r2['ok'] and 'did not come up' in r2['msg']


def test_runtime_view_never_calls_a_setting_active_until_the_runtime_reports_it():
    row = {'ctx': 2048, 'parallel': 1}
    assert ai_rig.runtime_view(row, {'ctx': 2048, 'slots': 1})['state'] == 'active'
    v = ai_rig.runtime_view(row, {'ctx': 2048, 'slots': 4})
    assert v['state'] == 'differs' and not v['active'] and v['desired'] == {'ctx': 2048, 'slots': 1}
    assert ai_rig.runtime_view(row, None)['state'] == 'unreachable'
    assert ai_rig.runtime_view(row, {'ctx': 2048, 'slots': 1}, {'state': 'applying'})['state'] == 'applying'
    assert ai_rig.runtime_view({'ctx': 0, 'parallel': 1}, None)['auto'] is True and ai_rig.win_target({'ctx': 0}) is None


def _svc(monkeypatch, tmp_path):
    import reputation_service as rs
    monkeypatch.setattr(rs, 'NEXA_CTL_PATH', tmp_path / 'nexa_ctl.json')
    monkeypatch.setenv('WIN_LLM_BASE_URL', 'http://10.0.0.116:8080')
    rs._nexa_job.clear(); rs._nexa_act.update(at=0, v=None)
    return rs


def test_unreachable_controller_saves_but_reports_not_changed(monkeypatch, tmp_path):
    rs = _svc(monkeypatch, tmp_path)
    async def dead(*a, **k):
        return None, {'error': 'ConnectError'}
    monkeypatch.setattr(rs, '_nexa_ctl', dead)
    j = asyncio.run(rs._nexa_apply_job(2048, 1))
    assert j['state'] == 'not-applied' and 'NOT changed' in j['msg'] and not j['verified']
    c = rs._nexa_ctl_conf()
    assert c['url'] == 'http://10.0.0.116:8081' and len(c['token']) > 20


def test_successful_apply_is_verified_on_the_runtime_itself(monkeypatch, tmp_path):
    rs = _svc(monkeypatch, tmp_path)
    async def ok(*a, **k):
        return 200, {'ok': True}
    async def runtime(fresh=False):
        return {'ctx': 2048, 'slots': 1, 'model': 'q.gguf'}
    monkeypatch.setattr(rs, '_nexa_ctl', ok); monkeypatch.setattr(rs, '_nexa_actual', runtime)
    j = asyncio.run(rs._nexa_apply_job(2048, 1))
    assert j['state'] == 'verified' and j['verified'] is True


def test_controller_says_ok_but_the_runtime_differs(monkeypatch, tmp_path):
    rs = _svc(monkeypatch, tmp_path)
    async def ok(*a, **k):
        return 200, {'ok': True}
    async def runtime(fresh=False):
        return {'ctx': 2048, 'slots': 4}
    monkeypatch.setattr(rs, '_nexa_ctl', ok); monkeypatch.setattr(rs, '_nexa_actual', runtime)
    j = asyncio.run(rs._nexa_apply_job(2048, 1))
    assert j['state'] == 'mismatch' and not j['verified'] and '4 slots' in j['msg']


def test_mcp_serves_a_setup_that_carries_no_shell_input_from_http():
    import feeless_mcp as fm
    ps = fm.nexa_install_ps1('http://10.0.0.5:8765', 'MCPTOK', 'CTLTOK')
    assert "nexa_controller.py" in ps and "CTLTOK" in ps and "LocalSubnet" in ps and 'FEELESS-NEXA' in ps
