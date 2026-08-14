#!/usr/bin/env python3
"""memory-decay.py — 记忆衰减与遗忘候选检测（硬规则 5：可持续 = 会遗忘）。

对 memory/*.yaml 中每条 active 条目计算健康分，按「久未使用 + 低命中」判定
遗忘候选（建议 deprecated）。主动遗忘防止记忆库膨胀退化。

健康分公式（0~1）：
    age_score   = exp(-age_days / DECAY_HALF_LIFE)          # 越久越旧，指数衰减
    use_score   = min(hits / HIT_REFERENCE, 1.0)            # 命中越多越活跃
    health      = 0.6 * age_score + 0.4 * use_score

遗忘候选阈值：
    health < DECAY_THRESHOLD（默认 0.30）→ 建议 deprecated
    --dry-run 默认只报告；--mark 才实际写入 deprecated: true（人工确认后执行）

用法:
    python SEA/scripts/memory-decay.py [--threshold 0.30] [--half-life 180] [--mark]

退出码: 0 无遗忘候选 或 --mark 后全部处理; 1 存在遗忘候选（dry-run 时）。
零第三方依赖（仅标准库 + PyYAML）。
"""

import argparse
import datetime as dt
import math
import sys
from pathlib import Path

try:
    from yaml import safe_load, safe_dump
except ImportError:  # pragma: no cover
    sys.stderr.write("缺少依赖：请先 `pip install pyyaml`\n")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = ROOT / "memory"
DEFAULT_HALF_LIFE = 180      # 衰减半衰期（天）：180 天未用，age_score 降到 0.5
DEFAULT_HIT_REF = 5          # 参考命中数：达到即 use_score=1.0
DEFAULT_THRESHOLD = 0.30     # 健康分低于此值 → 遗忘候选


def parse_date(s):
    try:
        return dt.date.fromisoformat(str(s).strip())
    except (ValueError, AttributeError):
        return None


def health_score(last_used: str, hits, today: dt.date, half_life, hit_ref):
    last = parse_date(last_used)
    if last is None:
        return 0.0  # 日期缺失视为可疑，优先人工检查
    age_days = max(0, (today - last).days)
    age_score = math.exp(-age_days / max(1, half_life))
    use_score = min(max(0, hits or 0) / max(1, hit_ref), 1.0)
    return 0.6 * age_score + 0.4 * use_score


def collect_entries():
    out = []
    for path in sorted(DEFAULT_DIR.glob("*.yaml")):
        with open(path, "r", encoding="utf-8") as f:
            data = safe_load(f)
        if not isinstance(data, dict):
            continue
        for entry in data.get("entries", []) or []:
            if isinstance(entry, dict) and entry.get("id"):
                out.append((path, entry))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                    help=f"健康分阈值（默认 {DEFAULT_THRESHOLD}）")
    ap.add_argument("--half-life", type=int, default=DEFAULT_HALF_LIFE,
                    help=f"衰减半衰期天数（默认 {DEFAULT_HALF_LIFE}）")
    ap.add_argument("--mark", action="store_true",
                    help="实际写入 deprecated: true（默认仅报告）")
    args = ap.parse_args()

    today = dt.date.today()
    items = collect_entries()
    candidates = []

    for path, entry in items:
        if entry.get("deprecated"):
            continue  # 已弃用条目不再评估
        score = health_score(entry.get("last_used"), entry.get("hits"),
                             today, args.half_life, DEFAULT_HIT_REF)
        if score < args.threshold:
            candidates.append((path, entry, score))

    if not candidates:
        print(f"OK：{len(items)} 个 active 条目均健康（阈值 {args.threshold}）。")
        return 0

    for path, entry, score in candidates:
        eid = entry.get("id")
        print(f"[遗忘候选] {eid} 健康分 {score:.2f}（{path.name}）")
        print(f"    claim: {entry.get('claim', '')[:100]}")
        print(f"    last_used: {entry.get('last_used')}  hits: {entry.get('hits')}")
        print("    建议：若确认失效/过时，标记 deprecated: true（保留以审计）。")
        print()

    if not args.mark:
        print(f"{len(candidates)} 条遗忘候选（--mark 可实际写入 deprecated）。",
              file=sys.stderr)
        return 1

    # --mark：写入 deprecated
    for path, entry, _ in candidates:
        entry["deprecated"] = True
        entry["deprecated_at"] = today.isoformat()
        data = safe_load(path.read_text(encoding="utf-8"))
        for e in data.get("entries", []):
            if isinstance(e, dict) and e.get("id") == entry.get("id"):
                e["deprecated"] = True
                e["deprecated_at"] = today.isoformat()
        path.write_text(safe_dump(data, allow_unicode=True, sort_keys=False),
                        encoding="utf-8")
        print(f"已标记 deprecated: {entry.get('id')}（{path.name}）")
    print("请复跑 validate-memory.py 确认。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
