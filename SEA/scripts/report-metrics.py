#!/usr/bin/env python3
"""report-metrics.py — 进化指标仪表盘（§8.4），汇总框架健康状态。

输出指标：
  记忆库     : 总条目 / 分类分布 / deprecated 数 / 平均置信度 / 遗忘候选数
  技能库     : 技能数 / 带评测集技能数 / 平均评测分（调用 evaluate-skill 打分逻辑）
  定义改进   : 注册表条目数 / approved / reverted / rejected 分布
  技能演进   : evolutions.json 条目数 / solidified / pending 分布
  健康提示   : 汇总需要人工关注的点（遗忘候选、pending 待审、回滚率）

用法:
    python SEA/scripts/report-metrics.py [--skills-dir <技能库根目录>]

退出码: 0 正常（无论健康与否均输出报告）。
零第三方依赖（仅标准库 + PyYAML）。
"""

import argparse
import sys
from pathlib import Path

try:
    from yaml import safe_load
except ImportError:  # pragma: no cover
    sys.stderr.write("缺少依赖：请先 `pip install pyyaml`\n")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "evaluate_skill", SCRIPTS_DIR / "evaluate-skill.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
check_skill = _mod.check_skill
MEMORY_DIR = ROOT / "memory"
AGENTS_DIR = ROOT / "agents" / "_improvements"


def load_yaml(path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return safe_load(f)


def resolve_skills_dir(arg):
    """自动探测技能库根目录：显式参数 > .opencode/skills（工作区）> 仓库根 skills/。"""
    if arg:
        return Path(arg)
    candidates = [
        Path.cwd() / ".opencode" / "skills",
        ROOT.parent / "skills",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[-1]


def memory_metrics():
    entries = []
    for p in sorted(MEMORY_DIR.glob("*.yaml")):
        data = load_yaml(p)
        if isinstance(data, dict):
            entries.extend(data.get("entries", []) or [])
    total = len(entries)
    active = [e for e in entries if not e.get("deprecated")]
    by_cat = {}
    for e in entries:
        c = e.get("category") or e.get("type") or "?"
        by_cat[c] = by_cat.get(c, 0) + 1
    confs = [e.get("confidence") for e in active
             if isinstance(e.get("confidence"), (int, float))]
    avg_conf = round(sum(confs) / len(confs), 2) if confs else None
    return {
        "total": total,
        "deprecated": total - len(active),
        "by_category": by_cat,
        "avg_confidence": avg_conf,
    }


def skill_metrics(skills_dir: Path):
    skills = [d for d in sorted(skills_dir.iterdir())
              if d.is_dir() and not d.name.startswith("_")]
    scored = 0
    total_score = 0.0
    for d in skills:
        tp = d / "test-prompts.json"
        if not tp.exists():
            continue
        try:
            _, prompts, scores = check_skill(d)
            if scores:
                scored += 1
                total_score += sum(scores) / len(scores)
        except Exception:
            continue
    return {
        "count": len(skills),
        "with_testset": scored,
        "avg_score": round(total_score / scored, 3) if scored else None,
    }


def improvement_metrics():
    data = load_yaml(AGENTS_DIR / "improvements.json")
    items = data.get("improvements", []) if isinstance(data, dict) else []
    status = {}
    for it in items:
        s = it.get("status", "?")
        status[s] = status.get(s, 0) + 1
    return {"total": len(items), "by_status": status}


def evolution_metrics(skills_dir: Path):
    data = load_yaml(skills_dir / "_evolutions" / "evolutions.json")
    items = data.get("evolutions", []) if isinstance(data, dict) else []
    status = {}
    for it in items:
        s = it.get("status", "?")
        status[s] = status.get(s, 0) + 1
    return {"total": len(items), "by_status": status}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills-dir", type=str, default=None,
                    help="技能库根目录（默认自动探测 .opencode/skills → 仓库根 skills/）")
    args = ap.parse_args()

    skills_dir = resolve_skills_dir(args.skills_dir)

    mem = memory_metrics()
    sk = skill_metrics(skills_dir)
    im = improvement_metrics()
    evo = evolution_metrics(skills_dir)

    print("=== SEA 进化指标报告 ===")
    print(f"记忆库: 总 {mem['total']}（deprecated {mem['deprecated']}）")
    for k, v in sorted(mem["by_category"].items()):
        print(f"  - {k}: {v}")
    if mem["avg_confidence"] is not None:
        print(f"  平均置信度(active): {mem['avg_confidence']}")
    print(f"技能库: {sk['count']} 技能，{sk['with_testset']} 带评测集"
          + (f"，平均评测分 {sk['avg_score']}" if sk["avg_score"] else ""))
    print(f"定义改进: {im['total']} 条目 {im['by_status']}")
    print(f"技能演进: {evo['total']} 候选 {evo['by_status']}")

    # 健康提示
    notices = []
    if mem["deprecated"]:
        notices.append(f"{mem['deprecated']} 条记忆已 deprecated（正常衰减留痕）")
    im_pending = im["by_status"].get("pending", 0)
    if im_pending:
        notices.append(f"{im_pending} 条定义改进待审（pending）")
    evo_pending = evo["by_status"].get("pending", 0)
    if evo_pending:
        notices.append(f"{evo_pending} 个技能演进候选待审（pending）")
    reverted = evo["by_status"].get("reverted", 0) + im["by_status"].get("reverted", 0)
    if reverted:
        notices.append(f"回滚 {reverted} 次（棘轮生效，需关注评估器-生成器匹配）")
    if notices:
        print("\n健康提示:")
        for n in notices:
            print(f"  - {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
