"""📌 THE "FEELESS LIVE" PRESET IN LM STUDIO (owner, 2026-10-23, LM Studio screenshot: "I don't see where the new Prompt Studio updates are — or is it
only for the site and this stays as the root brain prompt?").

LM Studio's own System Prompt box (the "FEELESS FEE Master" preset) feeds ONLY LM Studio's chat window. Every FEELESS call sends its own system
message (the seat prompt + the applied 🎭 mindset) and its own sampling — so that box never shows what OSSY really trades on. This module writes
what FEELESS really sends into a SEPARATE preset LM Studio lists as "FEELESS LIVE · OSSY" (the owner's own preset is never touched): pick it in
LM Studio and its box shows the live brain, rewritten every time a mindset is applied, reverted or auto-tuned.

Only this Mac's LM Studio (OSSY) can be written — G4's LM Studio lives on the desktop (Brain › Prompts copies its prompt for pasting there).
Tests never write the real home folder (`home` must be passed while pytest runs)."""
import json
import os
from pathlib import Path

NAME = {'local': 'FEELESS LIVE · OSSY'}
_SAMPLING = {'topP': 'llm.prediction.topPSampling', 'topK': 'llm.prediction.topKSampling', 'minP': 'llm.prediction.minPSampling',
             'repeatPenalty': 'llm.prediction.repeatPenalty'}
_last = {}   # key → the body last written (only rewrite on a change)


def preset_dir(home=None):
    return Path(home or os.path.expanduser('~')) / '.lmstudio' / 'config-presets'


def build(key, system, infer=None):
    """The preset body LM Studio reads ({identifier, name, operation.fields}) — the system prompt FEELESS sends + its sampling overrides."""
    inf = infer or {}
    fields = [{'key': 'llm.prediction.systemPrompt', 'value': str(system or '')}]
    if inf.get('temp') is not None:
        fields.append({'key': 'llm.prediction.temperature', 'value': float(inf['temp'])})
    if inf.get('maxTok') is not None:
        fields.append({'key': 'llm.prediction.maxPredictedTokens', 'value': {'checked': True, 'value': int(inf['maxTok'])}})
    for k, lk in _SAMPLING.items():
        if inf.get(k) is not None:
            fields.append({'key': lk, 'value': {'checked': True, 'value': inf[k]}})
    if inf.get('stop'):
        fields.append({'key': 'llm.prediction.stopStrings', 'value': list(inf['stop'])})
    return {'identifier': f'@local:feeless-live-{key}', 'name': NAME.get(key, f'FEELESS LIVE · {key}'), 'changed': True,
            'operation': {'fields': fields}, 'load': {'fields': []}}


def write(key, system, infer=None, home=None):
    """Write / refresh the live preset for a model on THIS Mac → its path, or None (not this Mac's model, no LM Studio folder, unchanged, or a
    test without an explicit home)."""
    if key not in NAME or not system:
        return None
    if home is None and os.environ.get('PYTEST_CURRENT_TEST'):
        return None   # 🧪 never the owner's real LM Studio folder from a test
    d = preset_dir(home)
    if not d.is_dir():
        return None
    body = build(key, system, infer)
    p = d / f'{NAME[key]}.preset.json'
    if _last.get((str(d), key)) == body and p.exists():
        return None
    tmp = p.with_name(p.name + '.tmp')
    tmp.write_text(json.dumps(body, indent=2, ensure_ascii=False))
    os.replace(tmp, p)
    _last[(str(d), key)] = body
    return str(p)
