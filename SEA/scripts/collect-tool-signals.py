#!/usr/bin/env python3
"""collect-tool-signals.py — 工具失败信号采集（§10.3：把"手工上报损坏工具"升级为"自动检测+修复候选"）。

收尾协议中调用：检测到 MCP/自定义工具调用失败、缺失、行为异常时，
把信号追加到 SEA/tools/_registry/tool-signals.json。

用法:
    python SEA/scripts/collect-tool-signals.py <tool> --type <call-failure|missing|broken|slow|unsafe> --detail "<说明>"
    python SEA/scripts/collect-tool-signals.py --list                 # 列出全部信号
    python SEA/scripts/collect-tool-signals.py --stats                # 按工具聚合统计
    python SEA/scripts/collect-tool-signals.py --prune <id>           # 删除某条（人工确认后）

信号类型:
    call-failure  调用报错/超时/返回异常
    missing       工具不存在/未注册/未连接
    broken        返回结果结构损坏/无法解析
    slow          性能显著劣化
    unsafe        行为可疑（权限越界、读敏感路径等）

退出码: 0 成功; 1 参数错误或文件损坏。
零第三方依赖（仅标准库）。
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "tools" / "_registry" / "tool-signals.json"

VALID_TYPES = {"call-failure", "missing", "broken", "slow", "unsafe"}
VALID_STATUS = {"pending", "analyzed", "fixed", "wonfix"}


def load():
    if not REGISTRY.exists():
        return {"signals": []}
    with open(REGISTRY, "r", encoding="utf-8") as f:
        return json.load(f)


def save(data):
    REGISTRY.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                        encoding="utf-8")


def next_id(data):
    ids = [s.get("id", "") for s in data.get("signals", [])]
    nums = [int(i.split("-")[-1]) for i in ids if i.startswith("t-")]
    return f"t-{dt.date.today().strftime('%Y%m%d')}-{max(nums, default=0) + 1:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tool", nargs="?", default=None, help="工具名（append 模式）")
    ap.add_argument("--type", choices=sorted(VALID_TYPES), default="call-failure")
    ap.add_argument("--detail", default="")
    ap.add_argument("--context", default="")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--prune", default=None, help="删除指定 id 的信号")
    args = ap.parse_args()

    data = load()
    if not isinstance(data, dict):
        print("[ERROR] tool-signals.json 损坏", file=sys.stderr)
        return 1

    if args.prune:
        before = len(data.get("signals", []))
        data["signals"] = [s for s in data.get("signals", [])
                           if s.get("id") != args.prune]
        save(data)
        removed = before - len(data["signals"])
        print(f"已删除 {removed} 条（{args.prune}）。")
        return 0

    if args.list:
        for s in data.get("signals", []):
            print(f"[{s.get('id')}] {s.get('tool')} | {s.get('signal', {}).get('type')} "
                  f"| {s.get('signal', {}).get('detail', '')[:80]}")
            print(f"    @{s.get('timestamp')} status={s.get('status')}")
        print(f"共 {len(data.get('signals', []))} 条。")
        return 0

    if args.stats:
        by_tool = {}
        by_type = {}
        for s in data.get("signals", []):
            tool = s.get("tool", "?")
            by_tool[tool] = by_tool.get(tool, 0) + 1
            t = s.get("signal", {}).get("type", "?")
            by_type[t] = by_type.get(t, 0) + 1
        print("按工具:", dict(sorted(by_tool.items())))
        print("按类型:", dict(sorted(by_type.items())))
        pending = sum(1 for s in data.get("signals", [])
                      if s.get("status") == "pending")
        print(f"pending: {pending}")
        return 0

    if not args.tool:
        print("缺少工具名（使用 --list / --stats / --prune 或提供 <tool>）",
              file=sys.stderr)
        return 1
    if not args.detail:
        print("缺少 --detail 说明", file=sys.stderr)
        return 1

    entry = {
        "id": next_id(data),
        "tool": args.tool,
        "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
        "signal": {
            "type": args.type,
            "detail": args.detail,
            "context": args.context or None,
        },
        "status": "pending",
        "created": dt.date.today().isoformat(),
    }
    data.setdefault("signals", []).append(entry)
    save(data)
    print(f"已记录信号 {entry['id']}: {args.tool} / {args.type}")
    print(f"建议：同工具累计 3+ 条 pending → 走工具修复候选流程")
    return 0


if __name__ == "__main__":
    sys.exit(main())
