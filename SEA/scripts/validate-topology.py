#!/usr/bin/env python3
"""validate-topology.py — 校验 SEA/agents/topology.json（§10.1 拓扑注册表）。

检查项:
  1. 顶层结构：topologies 数组存在
  2. 每个候选：id 唯一、必填字段完整（id/name/description/agents/status）
  3. status 枚举合法：pending / approved / reverted
  4. agents 为字符串数组，且每个 agent 有对应定义文件（.opencode/agents/ 或 templates/）
  5. edges 中的 from/to 都指向拓扑内 agent（无悬空引用）
  6. edges 格式完整（from/to 必填）

用法:
    python SEA/scripts/validate-topology.py [--agents-dir <agent 定义目录>]

退出码: 0 全部通过; 1 存在错误。
零第三方依赖（仅标准库）。
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOPO_PATH = ROOT / "agents" / "topology.json"
VALID_STATUS = {"pending", "approved", "reverted"}
REQUIRED_FIELDS = ["id", "name", "description", "agents", "status"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents-dir", type=str, default=None,
                    help="agent 定义目录（默认 cwd/.opencode/agents，回退模板目录）")
    args = ap.parse_args()

    if not TOPO_PATH.exists():
        print(f"[ERROR] 拓扑注册表不存在: {TOPO_PATH}", file=sys.stderr)
        return 1
    try:
        data = json.loads(TOPO_PATH.read_text(encoding="utf-8"))
    except ValueError as e:
        print(f"[ERROR] topology.json 解析失败: {e}", file=sys.stderr)
        return 1

    agents_dir = Path(args.agents_dir) if args.agents_dir \
        else Path.cwd() / ".opencode" / "agents"
    templates_dir = ROOT / "templates"

    topos = data.get("topologies", [])
    if not isinstance(topos, list):
        print("[ERROR] topologies 应为数组", file=sys.stderr)
        return 1

    errors = []
    seen_ids = set()
    for i, t in enumerate(topos, 1):
        loc = f"topologies 候选#{i}"
        if not isinstance(t, dict):
            errors.append(f"{loc}: 应为对象")
            continue
        for f in REQUIRED_FIELDS:
            if f not in t or t[f] in (None, ""):
                errors.append(f"{loc} ({t.get('id', '?')}): 缺少必填字段 {f}")
        eid = t.get("id")
        if eid:
            if eid in seen_ids:
                errors.append(f"{loc}: id 重复 {eid}")
            seen_ids.add(eid)
        if t.get("status") not in VALID_STATUS:
            errors.append(f"{loc} ({eid}): status 非法 {t.get('status')}（应为 {sorted(VALID_STATUS)}）")

        agents = t.get("agents", [])
        if not isinstance(agents, list) or not agents:
            errors.append(f"{loc} ({eid}): agents 应为非空字符串数组")
            continue
        agent_names = set()
        for a in agents:
            if not isinstance(a, str):
                errors.append(f"{loc} ({eid}): agent 应为字符串: {a}")
                continue
            agent_names.add(a)
            fname = f"{a}.md"
            if not (agents_dir / fname).exists() and not (templates_dir / fname).exists():
                errors.append(f"{loc} ({eid}): agent 定义文件缺失 {fname}")

        for j, edge in enumerate(t.get("edges", []) or [], 1):
            eloc = f"{loc} ({eid}) 边#{j}"
            if not isinstance(edge, dict):
                errors.append(f"{eloc}: 应为对象")
                continue
            frm, to = edge.get("from"), edge.get("to")
            if not frm or not to:
                errors.append(f"{eloc}: from/to 必填")
                continue
            if frm not in agent_names or to not in agent_names:
                errors.append(f"{eloc}: 悬空引用 {frm}→{to}（不在拓扑内）")

    if errors:
        for e in errors:
            print(f"[ERROR] {e}", file=sys.stderr)
        print(f"\n{len(errors)} 个问题，请修正后重跑。", file=sys.stderr)
        return 1
    print(f"OK：{len(topos)} 个拓扑候选校验通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
