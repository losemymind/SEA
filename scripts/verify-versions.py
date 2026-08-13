#!/usr/bin/env python3
"""verify-versions.py — 校验 memory/verified_facts.yaml 并做 re-verify 健康检查。

检查项:
  1. schema：id / claim / applies_to / verified / verified_on / source / status 完整
  2. status 枚举 active | deprecated；deprecated 需 deprecated_on + deprecated_reason
  3. 逾期检测：active 且 verified 的条目若 verified_on 距今超过 --stale 天，提示 re-verify
  4. 风险：deprecated 或 verified=false 的条目被标记"可引用"的风险仅提示（人工判断）

用法:
    python scripts/verify-versions.py [--stale 90] [--file memory/verified_facts.yaml]

退出码: 0 通过（含提示不报错）; 1 存在 schema 错误。
"""

import argparse
import sys
from datetime import date
from pathlib import Path

try:
    from yaml import safe_load
except ImportError:  # pragma: no cover
    sys.stderr.write("缺少依赖：请先 `pip install pyyaml`\n")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FILE = ROOT / "memory" / "verified_facts.yaml"

REQUIRED = ["id", "claim", "applies_to", "verified", "verified_on", "source", "status"]
VALID_STATUS = {"active", "deprecated"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stale", type=int, default=90, help="逾期天数（默认 90）")
    ap.add_argument("--file", type=str, default=str(DEFAULT_FILE))
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"[ERROR] {path}: 文件缺失", file=sys.stderr)
        return 1
    try:
        data = safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] {path}: YAML 解析失败: {e}", file=sys.stderr)
        return 1

    facts = data.get("facts", []) if isinstance(data, dict) else []
    if not isinstance(facts, list):
        print("[ERROR] facts 应为数组", file=sys.stderr)
        return 1

    errors = []
    warnings = []
    today = date.today()
    seen = set()

    for i, f in enumerate(facts, 1):
        loc = f"facts 条目#{i} ({f.get('id', '?')})"
        for field in REQUIRED:
            if field not in f or f[field] in (None, ""):
                errors.append(f"{loc}: 缺少必填字段 {field}")
        if f.get("status") not in VALID_STATUS:
            errors.append(f"{loc}: status 非法（应为 {sorted(VALID_STATUS)}）")
        if f.get("id"):
            if f["id"] in seen:
                errors.append(f"{loc}: id 重复")
            seen.add(f["id"])

        if f.get("status") == "deprecated":
            if not f.get("deprecated_on") or not f.get("deprecated_reason"):
                errors.append(f"{loc}: deprecated 需 deprecated_on + deprecated_reason")

        if f.get("verified") is False:
            warnings.append(f"{loc}: verified=false，未经核实，不得作为断言依据")

        vd = f.get("verified_on")
        if isinstance(vd, str):
            try:
                parsed = date.fromisoformat(vd)
            except ValueError:
                errors.append(f"{loc}: verified_on 非法日期 {vd}")
                continue
            if f.get("status") == "active" and f.get("verified") is True:
                days = (today - parsed).days
                if days > args.stale:
                    warnings.append(f"{loc}: 已 {days} 天未 re-verify（阈值 {args.stale}），建议核对来源")

    for e in errors:
        print(f"[ERROR] {e}", file=sys.stderr)
    for w in warnings:
        print(f"[WARN]  {w}")
    if errors:
        print(f"\n{len(errors)} 个 schema 错误，请修正后重跑。", file=sys.stderr)
        return 1
    print(f"OK：{len(facts)} 条事实 schema 完整。{len(warnings)} 条提示（非阻塞）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
