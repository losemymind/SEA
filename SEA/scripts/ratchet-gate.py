#!/usr/bin/env python3
"""ratchet-gate.py — 棘轮变更门（选项 B：有 pending 候选时才触发 L1 真实评估）。

机制（触发时机 = 变更门）:
  1. 扫描 evolutions.json（技能演进）与 improvements.json（定义改进）的 pending 候选
  2. 对每个候选涉及的技能（有 verifiable 用例）跑 L1 真实评估（evaluate-skill --mode judge）
  3. 棘轮裁决：score_after >= PASS_THRESHOLD（默认 0.7）才建议保留；否则建议回滚
  4. 无候选 / 无 verifiable 用例 → 不评估（token 零开销）

与选项 B 对齐：只有"要裁决是否保留改动"时才发生真实评估；日常任务零增量。

用法:
    python SEA/scripts/ratchet-gate.py [--skills-dir <技能库根目录>]
                                       [--threshold 0.7]
                                       [--model <判官模型，直接用当前任务模型>]
                                       [--json]
    python SEA/scripts/ratchet-gate.py --dry-run   # 只列出待裁决候选，不评估

退出码: 0 无待裁决候选 或 全部通过; 1 存在待裁决候选（dry-run）或有失败候选。
零第三方依赖（仅标准库 + PyYAML）。
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from yaml import safe_load
except ImportError:  # pragma: no cover
    sys.stderr.write("缺少依赖：请先 `pip install pyyaml`\n")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
IMPROVEMENTS = ROOT / "agents" / "_improvements" / "improvements.json"
EVOLUTIONS = ROOT / "agents" / "_improvements" / "baselines.json"
EVOLUTIONS_SKILL = ROOT.parent / "skills" / "_evolutions" / "evolutions.json"
DEFAULT_THRESHOLD = 0.7


def load_json(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def load_yaml(path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = safe_load(f)
    return data if isinstance(data, list) else []


def pending_skill_candidates():
    """收集有 pending 候选的技能演进（evolutions.json）。"""
    data = load_json(EVOLUTIONS_SKILL)
    cands = []
    for e in data.get("evolutions", []) or []:
        if e.get("status") == "pending" and e.get("skill"):
            cands.append({"source": "evolutions", "skill": e["skill"], "entry": e})
    return cands


def pending_definition_candidates():
    """收集有 pending 候选的定义改进（improvements.json）。"""
    data = load_json(IMPROVEMENTS)
    cands = []
    for e in data.get("improvements", []) or []:
        if e.get("status") == "pending" and e.get("target"):
            cands.append({"source": "improvements", "target": e["target"], "entry": e})
    return cands


def run_l1(skill, skills_dir, model):
    """调 evaluate-skill --mode judge 对 verifiable heldout 用例做 L1 真实评估。"""
    import subprocess
    cmd = [sys.executable, str(ROOT / "scripts" / "evaluate-skill.py"),
           "--mode", "judge", "--skill", skill, "--split", "heldout",
           "--skills-dir", str(skills_dir), "--json"]
    if model:
        cmd += ["--model", model]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stdout + r.stderr
    try:
        out = json.loads(r.stdout)
        return out, None
    except ValueError:
        return None, r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills-dir", type=str, default=str(ROOT.parent / "skills"),
                    help="技能库根目录")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                    help=f"L1 真实分数通过线（默认 {DEFAULT_THRESHOLD}）")
    ap.add_argument("--model", type=str, default=None,
                    help="判官模型（直接用当前任务模型名）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--dry-run", action="store_true",
                    help="只列出待裁决候选，不评估")
    args = ap.parse_args()

    skills_dir = Path(args.skills_dir)
    skill_cands = pending_skill_candidates()
    defn_cands = pending_definition_candidates()

    if not skill_cands and not defn_cands:
        print("无 pending 候选，无需评估（变更门未触发，token 零开销）。")
        return 0

    print(f"待裁决: {len(skill_cands)} 个技能演进 + {len(defn_cands)} 个定义改进")

    if args.dry_run:
        for c in skill_cands:
            print(f"  [evolutions] {c['skill']}: {c['entry'].get('id')}")
        for c in defn_cands:
            print(f"  [improvements] {c['target']}: {c['entry'].get('id')}")
        print("dry-run：未触发评估。")
        return 1

    results = []
    failures = 0
    for c in skill_cands:
        skill = c["skill"]
        out, err = run_l1(skill, skills_dir, args.model)
        if out is None:
            print(f"[ERROR] {skill} L1 评估失败: {err}", file=sys.stderr)
            failures += 1
            continue
        score = out.get("score", 0.0)
        source = out.get("eval_source", "l0")
        verdict = "PASS" if score >= args.threshold else "FAIL"
        if verdict == "FAIL":
            failures += 1
        print(f"  [evolutions] {skill}: L1={score:.3f} ({source}) -> {verdict} "
              f"(通过线 {args.threshold})")
        results.append({"skill": skill, "score": score, "eval_source": source,
                        "verdict": verdict, "threshold": args.threshold})

    # 定义改进：目标是 .md 文件，暂无可执行 verifiable 用例 → 提示需人工评估
    for c in defn_cands:
        print(f"  [improvements] {c['target']}: 定义改进暂无 verifiable 用例，"
              f"维持 HITL 人工评估（不走 L1 自动）")

    if args.json:
        print(json.dumps({"schema_version": 1, "threshold": args.threshold,
                          "results": results}, ensure_ascii=False, indent=2))

    if failures:
        print(f"\n{failures} 个候选 L1 未达通过线，棘轮建议回滚。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
