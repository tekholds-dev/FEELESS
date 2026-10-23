#!/usr/bin/env python3
"""🎭 MINDSET PROBE (owner, 2026-10-23: "confirm the prompt studio really works for LM Studio and llama"). Read-only proof: one call per model through FEELESS's own router path (_call1 → with_studio), carrying a test mindset with a codename.
Changes no setting, no stored prompt, no trade. Prints what each model answered.

  backend/.venv/bin/python -I scripts/mindset-probe.py
"""
import asyncio, json, os, sys, time
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend')
sys.path.insert(0, B)
def _env_file(path):
    out = {}
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            out[k.strip().removeprefix('export ').strip()] = v.strip().strip('"').strip("'")
    return out
env = {**os.environ, **_env_file(os.path.join(B, '.env'))}
import httpx
import ai_router as ar
cfg = json.load(open(os.path.join(B, 'data', 'ai_cfg.json'))) if os.path.exists(os.path.join(B, 'data', 'ai_cfg.json')) else {}
CODE = {'lan': 'GREEN-FALCON', 'local': 'GOLD-VIPER', 'win': 'NIGHT-OWL'}

async def one(http, key):
    p = {**ar.provider(env, key, cfg), 'key': key}
    if p.get('why'):
        return key, None, f"not runnable: {p['why']}", 0
    ar.STUDIO[key] = f"Your mindset codename is {CODE[key]}. If anyone asks for your mindset codename, answer with it exactly."
    msgs = [{'role': 'system', 'content': 'You are a test probe. Answer in one short line.'}, {'role': 'user', 'content': 'What is your mindset codename? Reply with the codename only.'}]
    sent = ar.with_studio(msgs, key)[0]['content']
    t0 = time.time()
    try:
        text, err = await ar.ROUTER._call1(http, p, env, msgs, time.time())
    except Exception as e:
        text, err = None, ('exc', str(e)[:120], 0)
    finally:
        ar.STUDIO.pop(key, None)
    return key, text, err, round(time.time() - t0, 1), sent

async def main():
    async with httpx.AsyncClient(timeout=240) as http:
        for key in ('lan', 'local', 'win'):
            r = await one(http, key)
            key, text, err, sec = r[:4]
            print(f"\n== {ar.NAME_DEFAULT.get(key, key) if hasattr(ar, 'NAME_DEFAULT') else key} ({key}) · {sec}s")
            if len(r) > 4:
                print('   system sent ends with:', r[4][-160:].replace('\n', ' '))
            print('   answered:', (text or '').strip()[:200] if text else None, '| err:', err)
            print('   MINDSET REACHED THE MODEL:', bool(text and CODE[key] in text.upper().replace(' ', '-')))
asyncio.run(main())
