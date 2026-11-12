#!/usr/bin/env bash
# 🚀 COMP → its own PRIVATE repo (github: <you>/comp-ai). Copies COMP's code, datasets, exam, market rows, logs and ONLY the picked
# adapter (~21 MB) into ~/comp-ai, commits and pushes. The 9B base stays in LM Studio (5.6 GB, never uploaded). Old checkpoints here are
# pruned after a sync so the Mac keeps just the best one.  Run: bash scripts/comp-sync.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SRC="$ROOT/backend/data/comp_v2"; DST="${COMP_REPO_DIR:-$HOME/comp-ai}"
REPO="${COMP_REPO:-$(gh api user -q .login)/comp-ai}"
if [ ! -d "$DST/.git" ]; then
  gh repo view "$REPO" >/dev/null 2>&1 || gh repo create "$REPO" --private --description "COMP: FEELESS's own model (private)" >/dev/null
  git clone -q "https://github.com/$REPO.git" "$DST" 2>/dev/null || { mkdir -p "$DST"; git -C "$DST" init -q; git -C "$DST" remote add origin "https://github.com/$REPO.git"; }
fi
mkdir -p "$DST/code" "$DST/data" "$DST/adapter"
cp "$ROOT"/backend/comp_v2.py "$ROOT"/backend/comp_v2_exam.py "$ROOT"/backend/comp_market.py "$DST/code/"
for f in dataset.json exam.json market.json train.jsonl valid.jsonl test.jsonl train_rows.json valid_rows.json test_rows.json market_rows.jsonl train.log exam.log; do
  [ -f "$SRC/$f" ] && cp "$SRC/$f" "$DST/data/"
done
[ -f "$SRC/adapter/adapter_config.json" ] && cp "$SRC/adapter/adapter_config.json" "$DST/adapter/"
PICK=$(python3 -c "import json;print(json.load(open('$SRC/exam.json')).get('picked') or '')" 2>/dev/null || true)
CK="$SRC/adapter/adapters.safetensors"; [ -n "$PICK" ] && [ -f "$SRC/adapter/$(printf '%07d' "$PICK")_adapters.safetensors" ] && CK="$SRC/adapter/$(printf '%07d' "$PICK")_adapters.safetensors"
[ -f "$CK" ] && cp "$CK" "$DST/adapter/adapters.safetensors"
cat > "$DST/README.md" <<MD
# COMP (private)
FEELESS's own model: Qwen3.5-9B (Apache-2.0) + a LoRA adapter trained on the owner's settled proofs and self-labelled market rows.
- \`code/\` the trainer, the exam, the internet learner · \`data/\` the rows, the exam results, the logs · \`adapter/\` the picked adapter
- Base: lmstudio-community/Qwen3.5-9B-MLX-4bit (not stored here). Load: \`mlx_lm.load(base, adapter_path="adapter")\`
MD
cd "$DST"; git add -A
git diff --cached --quiet && { echo "comp-ai: nothing new"; exit 0; }
git -c user.name="$(git -C "$ROOT" config user.name)" -c user.email="$(git -C "$ROOT" config user.email)" commit -qm "COMP sync $(date +%Y-%m-%d\ %H:%M)"
git branch -M main; git push -q -u origin main
# keep only the picked checkpoint on this Mac
[ -n "$PICK" ] && find "$SRC/adapter" -name '*_adapters.safetensors' ! -name "$(printf '%07d' "$PICK")_adapters.safetensors" -delete
echo "comp-ai: pushed to $REPO ($(du -sh "$DST" | cut -f1))"
