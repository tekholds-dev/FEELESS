// 🧠 Model Desk fixture (tests + /dev/brain) — shaped from what LM Studio / NEXA's llamafile / FEELESS MCP really returned on 2026-10-23.
const now = () => Date.now() / 1000;
export const desk = (infer = {}) => ({
  at: now(), bounds: { temp: [0, 1.5], maxTok: [32, 4096] },
  mcp: { ok: true, ms: 14, endpoint: ':8765/mcp', n: 6, err: null, tools: [['now', "Today's date and time"], ['feeless_card', 'The REAL Fuse card right now'], ['feeless_coin', "FEELESS's full read of one Solana coin"],
    ['trench_now', 'The trench right now: weather + the live launch list'], ['web_search', 'Search the internet'], ['deep_research', 'DEEP research on anything']].map(([name, desc]) => ({ name, desc })) },
  models: [
    { key: 'lan', name: 'G4', state: 'ONLINE', model: 'Qwen3 4B 2507',
      info: { model: 'qwen/qwen3-4b-2507', name: 'Qwen3 4B 2507', publisher: 'qwen', arch: 'qwen3', format: 'MLX', quant: '4bit', bits: 4, sizeGb: 2.28, params: '4B', maxCtx: 262144, loadedCtx: 8704, parallel: 2, instances: 1, variant: 'qwen/qwen3-4b-2507@4bit', toolUse: true, vision: false, reasoning: null },
      server: { endpoint: 'http://10.0.0.249:1236', api: 'LM Studio · OpenAI /v1 + REST /api/v1', ok: true, ms: 31, listed: 2, instances: 1, keySet: true, timeout: 90, parallel: 2, perMin: 4, state: 'ONLINE', lastOkAt: now() - 40 },
      vitals: { calls: 18, okPct: 100, medMs: 15600, p90Ms: 23300, tokPerSec: 38.2, queue: 1, ctxFill: 0.58, lastOkAt: now() - 40, errors: 0, mindset: 'progressive' },
      inference: { infer: infer.lan || {}, desk: { temp: 0.1, maxTok: 700 }, runtime: null, reasoning: null, mindset: { set: 'progressive', seen: { set: 'progressive', at: now() - 40, ok: true } } } },
    { key: 'local', name: 'OSSY', state: 'ONLINE', model: 'GPT-OSS 20B',
      info: { model: 'openai/gpt-oss-20b', name: 'GPT-OSS 20B', publisher: 'openai', arch: 'gpt_oss', format: 'MLX', quant: 'MXFP4', bits: 4, sizeGb: 12.1, params: '20B', maxCtx: 131072, loadedCtx: 8192, parallel: 2, instances: 1, variant: 'openai/gpt-oss-20b@mxfp4', toolUse: true, vision: false, reasoning: { options: ['low', 'medium', 'high'], default: 'low' } },
      server: { endpoint: 'http://localhost:1234', api: 'LM Studio · OpenAI /v1 + REST /api/v1', ok: true, ms: 9, listed: 2, instances: 1, keySet: false, timeout: 60, parallel: 1, perMin: 4, state: 'ONLINE', lastOkAt: now() - 95 },
      vitals: { calls: 14, okPct: 93, medMs: 51200, p90Ms: 61000, tokPerSec: 21.4, queue: 0, ctxFill: 0.42, lastOkAt: now() - 95, errors: 1, lastErr: 'no answer in 60s' },
      inference: { infer: infer.local || {}, desk: { temp: 0.1, maxTok: 700 }, runtime: null, reasoning: { options: ['low', 'medium', 'high'], default: 'low' }, mindset: null } },
    { key: 'win', name: 'NEXA', state: 'ONLINE', model: 'Qwen2.5-1.5B-Instruct-Q4_K_M.gguf',
      info: { model: 'Qwen2.5-1.5B-Instruct-Q4_K_M.gguf', name: 'Qwen2.5-1.5B-Instruct-Q4_K_M.gguf', format: 'GGUF', quant: 'Q4_K_M', ctxPerSlot: 2048, slots: 1, busy: 0, speculative: false, defaults: { temperature: 0.8, top_k: 40, top_p: 0.95, min_p: 0.05, repeat_penalty: 1 } },
      server: { endpoint: 'http://10.0.0.5:8080', api: 'llamafile (llama.cpp) · OpenAI /v1 + /props /slots /health', ok: true, ms: 120, slots: 1, busy: 0, keySet: true, timeout: 240, parallel: 1, perMin: 2, state: 'ONLINE', lastOkAt: now() - 300 },
      vitals: { calls: 6, okPct: 100, medMs: 17300, p90Ms: 22000, tokPerSec: 6.1, queue: 0, ctxFill: 0.3, lastOkAt: now() - 300, errors: 0 },
      inference: { infer: infer.win || {}, desk: { temp: 0.1, maxTok: 700 }, runtime: { temperature: 0.8, top_k: 40, top_p: 0.95, min_p: 0.05, repeat_penalty: 1 }, reasoning: null, mindset: null, speculative: false } },
  ],
});
