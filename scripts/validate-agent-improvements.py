#!/usr/bin/env python3
"""validate-agent-improvements.py — 校验 agents/_improvements/ 下的改进注册表与棘轮基线。

检查项:
  1. improvements.json：schema 字段完整、kind/status 枚举合法、id 唯一
  2. baselines.json：baselines 映射内每个条目含 best_score(数字) / updated
  3. 棘轮一致性：已 approved 的改进若有 score_after，不得低于 baselines 中对应 target 的 best_score

用法:
    python scripts/validate-agent-improvements.py

退出码: 0 全部通过; 1 存在错误。零第三方依赖（仅标准库）。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "agents" / "_improvements"

VALID_KIND = {"FIX", "DERIVED", "REWRITE"}
VALID_STATUS = {"pending", "approved", "rejected", "reverted"}
REQUIRED_IMPROVEMENT = ["id", "target", "kind", "signal", "patch", "status", "created"]


def load_json(path, errors):
    if not path.exists():
        errors.append(f"{path.name}: 文件缺失")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(f"{path.name}: JSON 解析失败: {e}")
        return None


def check_improvements(errors):
    path = DIR / "improvements.json"
    data = load_json(path, errors)
    if data is None:
        return []
    items = data.get("improvements", [])
    if not isinstance(items, list):
        errors.append("improvements.json: improvements 应为数组")
        return []
    seen = set()
    for i, it in enumerate(items, 1):
        for f in REQUIRED_IMPROVEMENT:
            if f not in it:
                errors.append(f"improvements.json 条目#{i}: 缺少 {f}")
        if it.get("kind") not in VALID_KIND:
            errors.append(f"improvements.json 条目#{i}: kind 非法 {it.get('kind')}（应为 {sorted(VALID_KIND)}）")
        if it.get("status") not in VALID_STATUS:
            errors.append(f"improvements.json 条目#{i}: status 非法 {it.get('status')}（应为 {sorted(VALID_STATUS)}）")
        if it.get("id"):
            if it["id"] in seen:
                errors.append(f"improvements.json 条目#{i}: id 重复 {it['id']}")
            seen.add(it["id"])
    return items


def check_baselines(errors):
    path = DIR / "baselines.json"
    data = load_json(path, errors)
    if data is None:
        return {}
    bl = data.get("baselines", {})
    if not isinstance(bl, dict):
        errors.append("baselines.json: baselines 应为映射")
        return {}
    for target, info in bl.items():
        if not isinstance(info, dict):
            errors.append(f"baselines.json: {target} 条目应为对象")
            continue
        s = info.get("best_score")
        if not isinstance(s, (int, float)):
            errors.append(f"baselines.json: {target} 缺少数字 best_score")
        if not info.get("updated"):
            errors.append(f"baselines.json: {target} 缺少 updated")
    return bl


def check_ratchet(improvements, baselines, errors):
    """已 approved 的改进不得使某 target 的最优分低于基线。"""
    for it in improvements:
        if it.get("status") != "approved":
            continue
        tgt = it.get("target")
        after = it.get("score_after")
        if after is None:
            continue
        base = baselines.get(tgt, {}).get("best_score")
        if base is not None and isinstance(after, (int, float)) and after < base:
            errors.append(
                f"棘轮违约: {tgt} approved 改进 {it.get('id')} score_after={after} < 基线 {base}"
            )


def main():
    errors = []
    improvements = check_improvements(errors)
    baselines = check_baselines(errors)
    check_ratchet(improvements, baselines, errors)

    if errors:
        for e in errors:
            print(f"[ERROR] {e}", file=sys.stderr)
        print(f"\n{len(errors)} 个问题，请修正后重跑。", file=sys.stderr)
        return 1
    print("OK：改进注册表与棘轮基线校验通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
