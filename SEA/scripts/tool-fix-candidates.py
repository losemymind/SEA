#!/usr/bin/env python3
"""tool-fix-candidates.py — 工具修复候选生成（§10.3 后半：从失败信号聚合出修复候选）。

读 tool-signals.json（失败信号）+ tools.json（工具注册表），按工具聚合：
  - 同工具 pending 信号数 >= THRESHOLD（默认 3）→ 生成修复候选（走 HITL 审批）
  - 更新工具注册表状态：degraded（1-2 条）/ broken（>=3 条）
  - --promote 把候选写入候选区（tools/_registry/_candidates/）

用法:
    python SEA/scripts/tool-fix-candidates.py [--threshold 3] [--dry-run]
    python SEA/scripts/tool-fix-candidates.py --promote <工具名>

退出码: 0 无候选或已处理; 1 存在待处理候选（dry-run 时）。
零第三方依赖（仅标准库）。
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG_DIR = ROOT / "tools" / "_registry"
SIGNALS_PATH = REG_DIR / "tool-signals.json"
TOOLS_PATH = REG_DIR / "tools.json"
CAND_DIR = REG_DIR / "_candidates"
DEFAULT_THRESHOLD = 3


def load(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD,
                    help=f"同工具触发修复候选的 pending 信号数（默认 {DEFAULT_THRESHOLD}）")
    ap.add_argument("--dry-run", action="store_true", help="只报告不写入")
    ap.add_argument("--promote", default=None,
                    help="把指定工具的候选写入候选区（tools/_registry/_candidates/）")
    args = ap.parse_args()

    signals = load(SIGNALS_PATH).get("signals", [])
    tools = load(TOOLS_PATH).get("tools", [])

    # 按工具聚合 pending 信号
    by_tool = {}
    for s in signals:
        if s.get("status") != "pending":
            continue
        t = s.get("tool", "?")
        by_tool.setdefault(t, []).append(s)

    if args.promote:
        tgt = args.promote
        sigs = by_tool.get(tgt, [])
        if len(sigs) < args.threshold:
            print(f"[ERROR] {tgt} 只有 {len(sigs)} 条 pending 信号（阈值 {args.threshold}）",
                  file=sys.stderr)
            return 1
        cand = {
            "id": f"tfc-{dt.date.today().strftime('%Y%m%d')}-{tgt}",
            "tool": tgt,
            "signal_count": len(sigs),
            "signals": [{"id": s.get("id"), "type": s.get("signal", {}).get("type"),
                         "detail": s.get("signal", {}).get("detail")} for s in sigs],
            "suggested_fix": f"修复 {tgt}：核对信号细节后走工具修复流程（详见 skill tool-craft）",
            "status": "pending",
            "created": dt.date.today().isoformat(),
        }
        CAND_DIR.mkdir(parents=True, exist_ok=True)
        out = CAND_DIR / f"{tgt}.json"
        if not args.dry_run:
            out.write_text(json.dumps(cand, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        print(f"候选已写入: {out}")
        print(f"  建议：展示候选 → HITL 审批 → 修复 → 状态置 fixed")
        return 0

    # 报告聚合结果
    candidates = []
    for t in sorted(by_tool):
        n = len(by_tool[t])
        status = "degraded" if n < args.threshold else "broken"
        if n >= args.threshold:
            candidates.append(t)
        print(f"  {t}: {n} 条 pending 信号 → {status}")
        # 更新工具注册表状态
        entry = next((x for x in tools if x.get("name") == t), None)
        if entry is None:
            entry = {"name": t, "kind": "custom", "description": "",
                     "first_seen": dt.date.today().isoformat(), "signals": 0}
            tools.append(entry)
        entry["status"] = status
        entry["signals"] = n
        entry["updated"] = dt.date.today().isoformat()

    if not args.dry_run and tools:
        TOOLS_PATH.write_text(json.dumps(
            {"_doc": load(TOOLS_PATH).get("_doc", ""), "tools": tools},
            ensure_ascii=False, indent=2), encoding="utf-8")

    if candidates:
        print(f"\n{candidates} 达阈值，可用 --promote <工具名> 生成修复候选。",
              file=sys.stderr)
        return 1
    print("\n无达阈值的工具（--promote 或更多信号触发）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
