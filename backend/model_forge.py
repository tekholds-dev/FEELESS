"""🏗 MODEL FORGE (owner 2026-11-12: "create my full own model and my own guardrails … a model build playground that truly works and shows
specs … I click and it builds"). A real GPT-style transformer, written from scratch in numpy, trained on THIS Mac from the owner's own proofs.

  tokenizer (char, or byte-level BPE via `tokenizers`) → token + position embeddings → N × [LayerNorm → causal multi-head attention →
  LayerNorm → MLP (4×, GELU)] with residuals → LayerNorm → head tied to the token embedding. Hand-written backprop (checked against finite
  differences in tests), AdamW, warmup + cosine learning rate, gradient clipping. Guardrails wrap every answer (refused topics, blocked words,
  the wallet / key / email / phone scrubber, a length cap, a required footer) and say which rule fired.
It is small on purpose (≤ LIMITS): it learns the voice and structure of the owner's proofs, not world knowledge — the specs say so plainly.
Run a build as its own process: `python model_forge.py train <job_dir>` (the route starts it niced, so the site never lags)."""
import json
import math
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

LIMITS = {'d': (16, 384), 'layers': (1, 8), 'heads': (1, 8), 'ctx': (16, 256), 'steps': (20, 5000), 'batch': (4, 64), 'vocab': (64, 4096),
          'params': 6_000_000}
PRESETS = {
    'nano': {'name': 'Nano', 'tok': 'char', 'd': 64, 'layers': 2, 'heads': 4, 'ctx': 64, 'steps': 300, 'batch': 16, 'lr': 3e-3, 'vocab': 256},
    'mini': {'name': 'Mini', 'tok': 'char', 'd': 128, 'layers': 4, 'heads': 4, 'ctx': 128, 'steps': 800, 'batch': 16, 'lr': 1e-3, 'vocab': 256},
    'small': {'name': 'Small', 'tok': 'bpe', 'd': 192, 'layers': 6, 'heads': 6, 'ctx': 128, 'steps': 2000, 'batch': 16, 'lr': 6e-4, 'vocab': 1024},
}
FLOPS_PER_SEC = 12e9      # numpy on an M3 for a ~100K model (measured 2026-11-12: Nano 12, Mini 36 GFLOP/s effective — bigger matmuls run faster)
EPS = 1e-5
RAILS_DEFAULT = {'refuse': ['seed phrase', 'private key', 'guaranteed profit'], 'block': [], 'scrub': True, 'max_chars': 600,
                 'footer': 'Not financial advice.'}


# ─── the blueprint ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def clean_cfg(c):
    """Any blueprint the page sends → one inside LIMITS (heads always divide the width)."""
    c = {**PRESETS['nano'], **(c or {})}
    out = {'tok': 'bpe' if c.get('tok') == 'bpe' else 'char', 'name': str(c.get('name') or 'My model')[:40]}
    for k in ('d', 'layers', 'heads', 'ctx', 'steps', 'batch', 'vocab'):
        lo, hi = LIMITS[k]
        try:
            out[k] = int(min(hi, max(lo, int(c.get(k)))))
        except (TypeError, ValueError):
            out[k] = PRESETS['nano'][k]
    while out['d'] % out['heads']:
        out['heads'] -= 1
    out['lr'] = float(min(1e-2, max(1e-5, float(c.get('lr') or 1e-3))))
    return out


def n_params(c, vocab):
    d, L, T = c['d'], c['layers'], c['ctx']
    block = 2 * d + (3 * d * d + 3 * d) + (d * d + d) + 2 * d + (4 * d * d + 4 * d) + (4 * d * d + d)
    return {'embed': vocab * d, 'position': T * d, 'blocks': L * block, 'per_block': block, 'final_norm': 2 * d,
            'total': vocab * d + T * d + L * block + 2 * d}


def spec(c, vocab, corpus_tokens):
    """Everything the page shows before a build: parameters per part, memory, compute per token, data per parameter, an honest verdict."""
    c = clean_cfg(c); p = n_params(c, vocab); N = p['total']; B, T, d, L = c['batch'], c['ctx'], c['d'], c['layers']
    flops_tok = 6 * N + 12 * L * T * d                        # forward + backward per training token (the attention term included)
    act_mb = B * T * L * (34 * d + 5 * c['heads'] * T) * 4 / 1e6
    seen = c['steps'] * B * T
    return {'cfg': c, 'vocab': vocab, 'params': p, 'paramsTotal': N, 'tooBig': N > LIMITS['params'],
            'weightsMb': round(N * 4 / 1e6, 2), 'trainMb': round(N * 16 / 1e6 + act_mb, 1),
            'flopsPerToken': flops_tok, 'tokensSeen': seen, 'corpusTokens': corpus_tokens,
            'epochs': round(seen / max(1, corpus_tokens), 1), 'tokensPerParam': round(corpus_tokens / max(1, N), 3),
            'estSec': round(seen * flops_tok / min(40e9, FLOPS_PER_SEC * math.sqrt(max(1.0, N / 1e5))), 1), 'headDim': d // c['heads'],
            'verdict': ('Too big for this Mac: lower the width or layers.' if N > LIMITS['params'] else
                        'Your data is small next to this model: it will learn your proofs\' voice and repeat them — more proofs make it smarter.'
                        if corpus_tokens < 2 * N else 'Data and size are balanced: it can generalise past what it read.')}


# ─── tokenizers ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class CharTok:
    kind = 'char'

    def __init__(self, chars):
        self.chars = list(chars); self.ix = {ch: i for i, ch in enumerate(self.chars)}

    @classmethod
    def train(cls, text, _vocab=None):
        return cls(['\x00'] + sorted(set(text) - {'\x00'}))

    @property
    def size(self):
        return len(self.chars)

    def encode(self, s):
        return [self.ix.get(ch, 0) for ch in s]

    def decode(self, ids):
        return ''.join(self.chars[i] for i in ids if 0 < i < len(self.chars))

    def dump(self):
        return {'kind': 'char', 'chars': self.chars}


class BpeTok:
    kind = 'bpe'

    def __init__(self, tk):
        self.tk = tk

    @classmethod
    def train(cls, text, vocab=512):
        from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers
        tk = Tokenizer(models.BPE()); tk.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False); tk.decoder = decoders.ByteLevel()
        tk.train_from_iterator([text], trainers.BpeTrainer(vocab_size=int(vocab), initial_alphabet=pre_tokenizers.ByteLevel.alphabet(), show_progress=False))
        return cls(tk)

    @property
    def size(self):
        return self.tk.get_vocab_size()

    def encode(self, s):
        return self.tk.encode(s).ids

    def decode(self, ids):
        return self.tk.decode(list(ids))

    def dump(self):
        return {'kind': 'bpe', 'json': self.tk.to_str()}


def tok_train(kind, text, vocab):
    return (BpeTok if kind == 'bpe' else CharTok).train(text, vocab)


def tok_load(d):
    if d.get('kind') == 'bpe':
        from tokenizers import Tokenizer
        return BpeTok(Tokenizer.from_str(d['json']))
    return CharTok(d['chars'])


# ─── the transformer ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def init_params(c, vocab, seed=0, dtype=np.float32):
    r = np.random.default_rng(seed); d, L = c['d'], c['layers']; s = 0.02; sp = 0.02 / math.sqrt(2 * L)
    P = {'wte': r.normal(0, s, (vocab, d)), 'wpe': r.normal(0, s, (c['ctx'], d)), 'lnf_g': np.ones(d), 'lnf_b': np.zeros(d)}
    for i in range(L):
        P.update({f'{i}.ln1_g': np.ones(d), f'{i}.ln1_b': np.zeros(d), f'{i}.wqkv': r.normal(0, s, (d, 3 * d)), f'{i}.bqkv': np.zeros(3 * d),
                  f'{i}.wo': r.normal(0, sp, (d, d)), f'{i}.bo': np.zeros(d), f'{i}.ln2_g': np.ones(d), f'{i}.ln2_b': np.zeros(d),
                  f'{i}.w1': r.normal(0, s, (d, 4 * d)), f'{i}.b1': np.zeros(4 * d), f'{i}.w2': r.normal(0, sp, (4 * d, d)), f'{i}.b2': np.zeros(d)})
    return {k: v.astype(dtype) for k, v in P.items()}


def _ln(x, g, b):
    mu = x.mean(-1, keepdims=True); var = x.var(-1, keepdims=True); rstd = 1.0 / np.sqrt(var + EPS); xh = (x - mu) * rstd
    return xh * g + b, (xh, rstd, g)


def _ln_back(dy, cache):
    xh, rstd, g = cache; dxh = dy * g
    dx = rstd * (dxh - dxh.mean(-1, keepdims=True) - xh * (dxh * xh).mean(-1, keepdims=True))
    return dx, (dy * xh).reshape(-1, xh.shape[-1]).sum(0), dy.reshape(-1, xh.shape[-1]).sum(0)


_A = math.sqrt(2 / math.pi)


def _gelu(x):
    t = np.tanh(_A * (x + 0.044715 * x ** 3)); return 0.5 * x * (1 + t), t


def _gelu_back(dy, x, t):
    return dy * (0.5 * (1 + t) + 0.5 * x * (1 - t * t) * _A * (1 + 3 * 0.044715 * x * x))


def forward(P, c, idx, targets=None):
    """idx (B, T) token ids → logits (B, T, V), the mean cross-entropy when targets are given, and everything backward needs."""
    B, T = idx.shape; d, H = c['d'], c['heads']; hs = d // H
    x = P['wte'][idx] + P['wpe'][:T]; caches = []
    mask = np.triu(np.ones((T, T), dtype=bool), 1)
    for i in range(c['layers']):
        h1, ln1 = _ln(x, P[f'{i}.ln1_g'], P[f'{i}.ln1_b'])
        qkv = h1 @ P[f'{i}.wqkv'] + P[f'{i}.bqkv']
        q, k, v = (a.reshape(B, T, H, hs).transpose(0, 2, 1, 3) for a in np.split(qkv, 3, axis=-1))
        att = (q @ k.transpose(0, 1, 3, 2)) / math.sqrt(hs); att = np.where(mask, -1e9, att)
        att = np.exp(att - att.max(-1, keepdims=True)); att /= att.sum(-1, keepdims=True)
        y = (att @ v).transpose(0, 2, 1, 3).reshape(B, T, d)
        x2 = x + y @ P[f'{i}.wo'] + P[f'{i}.bo']
        h2, ln2 = _ln(x2, P[f'{i}.ln2_g'], P[f'{i}.ln2_b'])
        u = h2 @ P[f'{i}.w1'] + P[f'{i}.b1']; g_, t_ = _gelu(u)
        x3 = x2 + g_ @ P[f'{i}.w2'] + P[f'{i}.b2']
        caches.append((x, h1, ln1, q, k, v, att, y, x2, h2, ln2, u, g_, t_)); x = x3
    hf, lnf = _ln(x, P['lnf_g'], P['lnf_b'])
    logits = hf @ P['wte'].T
    loss = None; probs = None
    if targets is not None:
        z = logits - logits.max(-1, keepdims=True); probs = np.exp(z); probs /= probs.sum(-1, keepdims=True)
        loss = float(-np.log(np.take_along_axis(probs, targets[..., None], -1) + 1e-12).mean())
    return logits, loss, (idx, caches, hf, lnf, probs, targets)


def backward(P, c, fw):
    idx, caches, hf, lnf, probs, targets = fw
    B, T = idx.shape; d, H = c['d'], c['heads']; hs = d // H; G = {k: np.zeros_like(v) for k, v in P.items()}
    dlog = probs.copy(); np.put_along_axis(dlog, targets[..., None], np.take_along_axis(dlog, targets[..., None], -1) - 1, -1); dlog /= B * T
    G['wte'] += dlog.reshape(-1, dlog.shape[-1]).T @ hf.reshape(-1, d)
    dx, G['lnf_g'], G['lnf_b'] = _ln_back(dlog @ P['wte'], lnf)
    for i in reversed(range(c['layers'])):
        x, h1, ln1, q, k, v, att, y, x2, h2, ln2, u, g_, t_ = caches[i]
        G[f'{i}.w2'] += g_.reshape(-1, 4 * d).T @ dx.reshape(-1, d); G[f'{i}.b2'] += dx.reshape(-1, d).sum(0)
        du = _gelu_back(dx @ P[f'{i}.w2'].T, u, t_)
        G[f'{i}.w1'] += h2.reshape(-1, d).T @ du.reshape(-1, 4 * d); G[f'{i}.b1'] += du.reshape(-1, 4 * d).sum(0)
        dh2, G[f'{i}.ln2_g'], G[f'{i}.ln2_b'] = _ln_back(du @ P[f'{i}.w1'].T, ln2)
        dx2 = dx + dh2
        G[f'{i}.wo'] += y.reshape(-1, d).T @ dx2.reshape(-1, d); G[f'{i}.bo'] += dx2.reshape(-1, d).sum(0)
        dy = (dx2 @ P[f'{i}.wo'].T).reshape(B, T, H, hs).transpose(0, 2, 1, 3)
        datt = dy @ v.transpose(0, 1, 3, 2); dv = att.transpose(0, 1, 3, 2) @ dy
        ds = att * (datt - (datt * att).sum(-1, keepdims=True)) / math.sqrt(hs)
        dq = ds @ k; dk = ds.transpose(0, 1, 3, 2) @ q
        dqkv = np.concatenate([a.transpose(0, 2, 1, 3).reshape(B, T, d) for a in (dq, dk, dv)], -1)
        G[f'{i}.wqkv'] += h1.reshape(-1, d).T @ dqkv.reshape(-1, 3 * d); G[f'{i}.bqkv'] += dqkv.reshape(-1, 3 * d).sum(0)
        dh1, G[f'{i}.ln1_g'], G[f'{i}.ln1_b'] = _ln_back(dqkv @ P[f'{i}.wqkv'].T, ln1)
        dx = dx2 + dh1
    np.add.at(G['wte'], idx, dx); G['wpe'][:T] += dx.sum(0)
    return G


class AdamW:
    def __init__(self, P, lr, wd=0.1, b1=0.9, b2=0.95):
        self.m = {k: np.zeros_like(v) for k, v in P.items()}; self.v = {k: np.zeros_like(v) for k, v in P.items()}
        self.lr, self.wd, self.b1, self.b2, self.t = lr, wd, b1, b2, 0

    def step(self, P, G, lr):
        self.t += 1; c1 = 1 - self.b1 ** self.t; c2 = 1 - self.b2 ** self.t
        for k in P:
            g = G[k]; self.m[k] = self.b1 * self.m[k] + (1 - self.b1) * g; self.v[k] = self.b2 * self.v[k] + (1 - self.b2) * g * g
            if P[k].ndim == 2:
                P[k] -= lr * self.wd * P[k]          # decoupled weight decay on matrices only
            P[k] -= lr * (self.m[k] / c1) / (np.sqrt(self.v[k] / c2) + 1e-8)


def lr_at(step, steps, lr):
    warm = max(1, steps // 20)
    return lr * (step + 1) / warm if step < warm else lr * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * (step - warm) / max(1, steps - warm))))


def generate(P, c, tok, prompt, max_new=200, temperature=0.8, top_k=40, seed=None):
    r = np.random.default_rng(seed); ids = tok.encode(prompt) or [0]
    for _ in range(int(max_new)):
        ctx = np.array([ids[-c['ctx']:]]); logits = forward(P, c, ctx)[0][0, -1].astype(np.float64)
        if top_k and top_k < logits.size:
            cut = np.partition(logits, -top_k)[-top_k]; logits = np.where(logits < cut, -1e9, logits)
        z = logits / max(1e-3, temperature); p = np.exp(z - z.max()); p /= p.sum()
        ids.append(int(r.choice(p.size, p=p)))
    return tok.decode(ids[len(tok.encode(prompt)):])


# ─── guardrails ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def clean_rails(r):
    r = {**RAILS_DEFAULT, **(r or {})}
    words = lambda xs: [str(x).strip()[:60] for x in (xs or []) if str(x).strip()][:30]
    return {'refuse': words(r.get('refuse')), 'block': words(r.get('block')), 'scrub': bool(r.get('scrub')),
            'max_chars': int(min(4000, max(40, int(r.get('max_chars') or 600)))), 'footer': str(r.get('footer') or '')[:120]}


def guard(prompt, reply, rails):
    """→ (what the person sees, the rules that fired). Refused topics stop the answer; the rest clean it."""
    rails = clean_rails(rails); fired = []; low = (prompt or '').lower()
    hit = next((t for t in rails['refuse'] if t.lower() in low), None)
    if hit:
        return f'I will not help with "{hit}". That is one of my guardrails.', [{'rule': 'refuse', 'detail': hit}]
    out = reply or ''
    for w in rails['block']:
        out, n = re.subn(re.escape(w), '█' * len(w), out, flags=re.I)
        if n:
            fired.append({'rule': 'block', 'detail': f'{w} ×{n}'})
    if rails['scrub']:
        from model_lab import scrub
        cleaned = scrub(out)
        if cleaned != out:
            fired.append({'rule': 'scrub', 'detail': 'wallets / keys / emails / phones'}); out = cleaned
    if len(out) > rails['max_chars']:
        out = out[:rails['max_chars']].rstrip() + '…'; fired.append({'rule': 'max_chars', 'detail': str(rails['max_chars'])})
    if rails['footer']:
        out = f"{out.rstrip()}\n\n{rails['footer']}"; fired.append({'rule': 'footer', 'detail': rails['footer']})
    return out, fired


# ─── a build (runs as its own process) ────────────────────────────────────────────────────────────────────────────────────────────────────

def _write(path, obj):
    tmp = path.with_suffix('.tmp'); tmp.write_text(json.dumps(obj)); os.replace(tmp, path)


def train(job_dir, max_seconds=None):
    """Reads job.json + corpus.txt, trains, and keeps progress.json current (status, step, losses, tokens/s, ETA). A `stop` file ends it early;
    the weights it reached are still saved, so a stopped build can still be tried."""
    job_dir = Path(job_dir); job = json.loads((job_dir / 'job.json').read_text()); c = clean_cfg(job['cfg']); text = (job_dir / 'corpus.txt').read_text()
    prog = {'status': 'tokenizing', 'step': 0, 'steps': c['steps'], 'history': [], 'started': time.time(), 'pid': os.getpid()}
    _write(job_dir / 'progress.json', prog)
    try:
        tok = tok_train(c['tok'], text, c['vocab']); data = np.array(tok.encode(text), dtype=np.int64)
        if len(data) < 2 * (c['ctx'] + 2):
            raise ValueError(f'Only {len(data)} tokens to learn from: add text or lower the context.')
        cut = min(int(len(data) * 0.9), len(data) - (c['ctx'] + 2)); tr, va = data[:cut], data[cut:]   # the last 10% is held out: val loss
        P = init_params(c, tok.size, seed=int(job.get('seed') or 0)); opt = AdamW(P, c['lr']); r = np.random.default_rng(1)
        sp = spec(c, tok.size, len(data)); prog.update(status='training', vocab=tok.size, tokens=len(data), spec=sp)
        batch = lambda src: (lambda ix: (np.stack([src[i:i + c['ctx']] for i in ix]), np.stack([src[i + 1:i + c['ctx'] + 1] for i in ix])))(
            r.integers(0, len(src) - c['ctx'] - 1, c['batch']))
        t0 = time.time(); every = max(1, c['steps'] // 60); best = None
        for s in range(c['steps']):
            if (job_dir / 'stop').exists() or (max_seconds and time.time() - t0 > max_seconds):
                prog['status'] = 'stopped'; break
            xb, yb = batch(tr); _, loss, fw = forward(P, c, xb, yb); G = backward(P, c, fw)
            norm = math.sqrt(sum(float((g * g).sum()) for g in G.values()))
            if norm > 1.0:
                G = {k: g / norm for k, g in G.items()}
            opt.step(P, G, lr_at(s, c['steps'], c['lr']))
            if s % every == 0 or s == c['steps'] - 1:
                vx, vy = batch(va); vl = forward(P, c, vx, vy)[1]; el = time.time() - t0; tps = (s + 1) * c['batch'] * c['ctx'] / max(1e-6, el)
                best = vl if best is None else min(best, vl)
                prog['history'].append([s, round(loss, 4), round(vl, 4)]); prog['history'] = prog['history'][-200:]
                prog.update(step=s + 1, loss=round(loss, 4), val=round(vl, 4), tps=round(tps), elapsed=round(el, 1),
                            eta=round((c['steps'] - s - 1) * c['batch'] * c['ctx'] / max(1, tps), 1), gradNorm=round(norm, 3))
                _write(job_dir / 'progress.json', prog)
        np.savez(job_dir / 'weights.npz', **P); (job_dir / 'tokenizer.json').write_text(json.dumps(tok.dump()))
        sample = generate(P, c, tok, job.get('sample_prompt') or 'PoW ', max_new=160, seed=0)
        card = {'name': c['name'], 'cfg': c, 'spec': sp, 'vocab': tok.size, 'tokens': len(data), 'steps': prog['step'], 'loss': prog.get('loss'),
                'val': prog.get('val'), 'bestVal': best, 'perplexity': round(math.exp(min(20, prog.get('val') or 20)), 2),
                'baselinePerplexity': tok.size, 'seconds': round(time.time() - t0, 1), 'sample': sample, 'rails': clean_rails(job.get('rails')),
                'built': time.time()}
        (job_dir / 'card.json').write_text(json.dumps(card))
        prog.update(status='stopped' if prog['status'] == 'stopped' else 'done', card=card)
    except Exception as e:   # noqa: BLE001 — a failed build says why on the page
        prog.update(status='failed', error=str(e)[:300])
    prog['ended'] = time.time(); _write(job_dir / 'progress.json', prog)
    return prog


def load(job_dir):
    job_dir = Path(job_dir); card = json.loads((job_dir / 'card.json').read_text())
    with np.load(job_dir / 'weights.npz') as z:
        P = {k: z[k] for k in z.files}
    return P, card['cfg'], tok_load(json.loads((job_dir / 'tokenizer.json').read_text())), card


if __name__ == '__main__' and len(sys.argv) == 3 and sys.argv[1] == 'train':
    train(sys.argv[2])
