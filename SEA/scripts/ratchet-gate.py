#!/usr/bin/env python3
"""ratchet-gate.py — 棘轮变更门 + 主动评估门（L1 真实评估的统一入口）。

两种触发方式:
  1. 自动评估（默认，选项 B 变更门）：
     - 扫描 evolutions.json 与 improvements.json 的 pending 候选
     - 对候选涉及的技能跑 L1 真实评估
     - 通过线（默认 0.7）裁决：PASS 建议保留 / FAIL 建议回滚
     - 无候选 → 不评估（token 零开销）
     - token 预算：默认推荐值（--budget 默认 20），可覆盖
  2. 主动评估（--active，用户输入「SEA评估」等关键词触发）：
     - 评估全部带 verifiable 用例的技能（不受 pending 限制）
     - token 预算：不设上限（--budget 0）
     - 用于全面体检，不进棘轮裁决，仅报告

判官来源（内联判官协议，免 URL/Key 配置）：
  ratchet-gate 调 evaluate-skill --emit 生成判定请求
  → agent 用当前会话模型逐条判定（--model 传会话模型名）
  → 写回 .answers.json → ratchet-gate 用 --apply 收集分数

用法:
    python SEA/scripts/ratchet-gate.py [--skills-dir <技能库根目录>]
                                       [--threshold 0.7]
                                       [--budget 20|0]
                                       [--model <会话模型>]
                                       [--active]
                                       [--json]
    python SEA/scripts/ratchet-gate.py --dry-run   # 只列出待裁决候选，不评估

退出码: 0 无待裁决候选 或 全部通过; 1 存在待裁决候选（dry-run）或有失败候选。
零第三方依赖（仅标准库 + PyYAML）。
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

try:
    from yaml import safe_load
except ImportError:  # pragma: no cover
    sys.stderr.write("缺少依赖：请先 `pip install pyyaml`\n")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
IMPROVEMENTS = ROOT / "agents" / "_improvements" / "improvements.json"
DEFAULT_THRESHOLD = 0.7
DEFAULT_BUDGET_AUTO = 20   # 自动评估推荐 token 预算（用例数）
DEFAULT_BUDGET_ACTIVE = 0  # 主动评估不设上限


def load_json(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


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


def pending_skill_candidates(skills_dir):
    """收集有 pending 候选的技能演进（evolutions.json，在技能库根目录的 _evolutions 下）。"""
    data = load_json(skills_dir / "_evolutions" / "evolutions.json")
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


def all_evaluable_skills(skills_dir):
    """主动评估：收集全部带 verifiable 用例的技能。"""
    out = []
    for sub in sorted(skills_dir.iterdir()):
        if not sub.is_dir() or sub.name.startswith("_"):
            continue
        tp = sub / "test-prompts.json"
        if not tp.exists():
            continue
        try:
            data = json.loads(tp.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        has_verifiable = any(p.get("verifiable") for p in data.get("prompts", []))
        if has_verifiable:
            out.append(sub.name)
    return out


def inline_l1(skill, skills_dir, model, split):
    """内联判官协议：--emit 生成判定请求，提示 agent 判定。

    返回 (request_path, error)。判定由 agent 用会话模型完成。
    """
    import subprocess
    tmp = Path(tempfile.mkdtemp(prefix="sea-judge-")) / f"{skill}.json"
    cmd = [sys.executable, str(ROOT / "scripts" / "evaluate-skill.py"),
           "--mode", "judge", "--skill", skill, "--split", split,
           "--skills-dir", str(skills_dir), "--emit", str(tmp)]
    if model:
        cmd += ["--model", model]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stdout + r.stderr
    return tmp, None


def collect_scores(request_path, skills_dir, model, split):
    """收集 agent 写回的判定结果（--apply）。模型优先用请求文件内记录的判官模型。"""
    import subprocess
    try:
        req_data = json.loads(request_path.read_text(encoding="utf-8"))
        model = req_data.get("judge_model") or model
    except (ValueError, OSError):
        pass
    cmd = [sys.executable, str(ROOT / "scripts" / "evaluate-skill.py"),
           "--mode", "judge", "--skill", request_path.stem, "--split", split,
           "--skills-dir", str(skills_dir), "--apply", str(request_path), "--json"]
    if model:
        cmd += ["--model", model]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stdout + r.stderr
    try:
        return json.loads(r.stdout), None
    except ValueError:
        return None, r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills-dir", type=str, default=None,
                    help="技能库根目录（默认自动探测 .opencode/skills → 仓库根 skills/）")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                    help=f"L1 真实分数通过线（默认 {DEFAULT_THRESHOLD}）")
    ap.add_argument("--budget", type=int, default=None,
                    help=f"单次评估最大用例数（自动评估默认 {DEFAULT_BUDGET_AUTO}，主动评估默认 0 不设上限）")
    ap.add_argument("--model", type=str, default=None,
                    help="判官模型（agent 评估时传当前会话模型名；便宜模型可传 SEA_EVAL_MODEL）")
    ap.add_argument("--active", action="store_true",
                    help="主动评估：评估全部技能（用户输入 SEA评估 触发），无预算上限，不进棘轮")
    ap.add_argument("--collect", type=str, default=None,
                    help="主动评估收集：对指定技能读回判定结果并计算分数（<request>.answers.json 需已写回）")
    ap.add_argument("--request", type=str, default=None,
                    help="--collect 时指定判定请求文件路径（不填则用临时目录中该技能的请求）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--dry-run", action="store_true",
                    help="只列出待裁决候选，不评估")
    args = ap.parse_args()

    skills_dir = resolve_skills_dir(args.skills_dir)
    model = args.model
    split = "heldout"

    # ---- 主动评估收集（--collect）----
    if args.collect:
        skill = args.collect
        req = None
        if args.request:
            req = Path(args.request)
        else:
            # 在临时目录中找该技能的判定请求
            for d in Path(tempfile.gettempdir()).glob("sea-judge-*"):
                cand = d / f"{skill}.json"
                if cand.exists():
                    req = cand
                    break
        if req is None:
            print(f"[ERROR] 找不到 {skill} 的判定请求（请先 --active 生成，或 --request 指定路径）",
                  file=sys.stderr)
            return 1
        out, err = collect_scores(req, skills_dir, model, split)
        if out is None:
            print(f"[ERROR] 判定收集失败（请确认 {req}.answers.json 已写回）: {err}",
                  file=sys.stderr)
            return 1
        score = out.get("score", 0.0)
        source = out.get("eval_source", "l0")
        print(f"[主动评估] {skill}: L1={score:.3f} ({source}, judge={out.get('judge_model')})")
        if args.json:
            print(json.dumps({"schema_version": 1, "mode": "active-collect",
                              "skill": skill, "score": score, "eval_source": source,
                              "per_prompt": out.get("per_prompt")},
                             ensure_ascii=False, indent=2))
        return 0

    # ---- 主动评估（--active）----
    if args.active:
        skills = all_evaluable_skills(skills_dir)
        budget = args.budget if args.budget is not None else DEFAULT_BUDGET_ACTIVE
        if not skills:
            print("没有技能带 verifiable 用例，主动评估无对象。")
            return 0
        print(f"[主动评估] {len(skills)} 个技能（budget={budget} 不设上限，模型={model or '会话模型'}）")
        print("流程：对每个技能生成判定请求 → 用会话模型判定 → 收集分数。")
        results = []
        for skill in skills:
            req, err = inline_l1(skill, skills_dir, model, split)
            if req is None:
                print(f"  [ERROR] {skill}: {err}", file=sys.stderr)
                continue
            print(f"  [判定] {skill}: 请用会话模型判定 {req}（scores 写回 {req}.answers.json）")
            results.append({"skill": skill, "request": str(req), "status": "pending-judge"})
        print(f"\n请逐技能判定后，以 --collect <技能名> 收集分数。")
        if args.json:
            print(json.dumps({"schema_version": 1, "mode": "active",
                              "results": results}, ensure_ascii=False, indent=2))
        return 0

    # ---- 自动评估（变更门）----
    skill_cands = pending_skill_candidates(skills_dir)
    defn_cands = pending_definition_candidates()
    budget = args.budget if args.budget is not None else DEFAULT_BUDGET_AUTO

    if not skill_cands and not defn_cands:
        print("无 pending 候选，无需评估（变更门未触发，token 零开销）。")
        return 0

    print(f"待裁决: {len(skill_cands)} 个技能演进 + {len(defn_cands)} 个定义改进 "
          f"（budget={budget}，模型={model or '会话模型'}）")

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
        req, err = inline_l1(skill, skills_dir, model, split)
        if req is None:
            print(f"[ERROR] {skill} 评估启动失败: {err}", file=sys.stderr)
            failures += 1
            continue
        print(f"  [裁决] {skill}: 用会话模型判定 {req}")
        out, err = collect_scores(req, skills_dir, model, split)
        if out is None:
            print(f"[ERROR] {skill} 判定收集失败（请确认 {req}.answers.json 已写回）: {err}",
                  file=sys.stderr)
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

    for c in defn_cands:
        print(f"  [improvements] {c['target']}: 定义改进暂无 verifiable 用例，"
              f"维持 HITL 人工评估（不走 L1 自动）")

    if args.json:
        print(json.dumps({"schema_version": 1, "threshold": args.threshold,
                          "mode": "auto", "budget": budget,
                          "results": results}, ensure_ascii=False, indent=2))

    if failures:
        print(f"\n{failures} 个候选 L1 未达通过线或未完成判定，棘轮建议回滚/重判。",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
