#!/usr/bin/env python3
"""evaluate-skill.py — 独立评测器（替代生成器自评，为棘轮提供可复现基线）。

两种模式:
  1. 技能评测（默认）: 确定性覆盖度打分。对每个技能自带的 test-prompts.json：
     - 从每个用例的 expect 中提取关键短语（去除标点后的子串特征）
     - 检查这些特征是否出现在 SKILL.md 正文中（覆盖度 = 命中的特征 / 总特征）
     - 用例得分 = 覆盖度；技能得分 = 所有用例得分的均值
     - failure 类用例要求 SKILL.md 有"反例/不要这样"约束，故对 failure 用例
       额外检查反例章节存在性
  2. 拓扑评测（--mode topology, §10.1）: 对 SEA/agents/topology.json 中的每个
     agent 拓扑候选打分，分量 = 结构完整性(0.4) + agent 定义覆盖(0.3) +
     调用边一致性(0.3)。
  3. LLM-as-Judge（--mode judge, §8.2）: 对单个技能的 verifiable test-prompts 调用
     外部 LLM 判官打分（Agent-as-a-Judge 思路，缓解生成器自评偏差）。判官端点经
     环境变量配置：SEA_JUDGE_URL（OpenAI 兼容 base）/ SEA_JUDGE_API_KEY /
     SEA_JUDGE_MODEL；--model 可覆盖（直接用当前任务模型）；未配置时回退确定性
     打分（eval_source=l0）。L1 真实评估（eval_source=l1）只评 verifiable=true 用例。

用途：在技能/拓扑创建或演进前后各跑一次，得到 score_before / score_after，
供 P2/P3 生命周期与棘轮使用。--split heldout 只评留出集（棘轮计分用，防过拟合）。

用法:
    python SEA/scripts/evaluate-skill.py [--skills-dir <技能库根目录>] [--json] [--split heldout]
    python SEA/scripts/evaluate-skill.py --mode topology [--json]
    python SEA/scripts/evaluate-skill.py --mode judge --skill <技能名> [--split heldout] [--model <模型>]

输出:
    无 --json: 逐技能/拓扑打印每个用例得分与总分（含 eval_source 标记）
    --json:    输出 JSON 供脚本消费（含 name、score、per_prompt/components、eval_source）

退出码: 0 正常（即使分数低也正常，分数仅供对比）；1 参数/IO 错误。
零第三方依赖（仅标准库）。
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 跳过这些字符（中文/英文标点、空白），其余视为"特征字符"
SKIP = set(" \t\n\r，。；：、（）()【】[]{}《》<>\"'‘’“”·—…!?！？,.!:;/-")
# 特征长度阈值：过短的短语（<2 个有效字符）易误报，直接忽略
MIN_FEATURE_LEN = 2
# failure 用例要求存在这些反例章节标记（任一即可）
COUNTER_EXAMPLE_MARKERS = [
    "反例", "不要这样", "不要", "禁止", "DO NOT", "Don't", "Avoid", "切勿", "危险",
]
# success 用例允许 SKILL.md 明确指出生成产物/流程
SUCCESS_EXTRAS = ["流程", "步骤", "输出", "产出", "验收", "何时使用"]


def extract_features(text: str):
    """把文本切成 2~4 个有效字符的滑动窗口短语集合，作为匹配特征。"""
    cleaned = [ch.lower() for ch in text if ch not in SKIP]
    if len(cleaned) < MIN_FEATURE_LEN:
        return set()
    features = set()
    for size in (2, 3):
        for i in range(len(cleaned) - size + 1):
            gram = "".join(cleaned[i:i + size])
            if len(gram) >= MIN_FEATURE_LEN:
                features.add(gram)
    return features


def coverage(haystack: str, features):
    if not features:
        return 1.0
    text = "".join(ch.lower() for ch in haystack if ch not in SKIP)
    if not text:
        return 0.0
    hit = sum(1 for f in features if f in text)
    return hit / len(features)


def filter_prompts(prompts, split=None, verifiable_only=False):
    """按 split 与 verifiable 过滤用例。

    split: None=全部 | train | heldout（棘轮计分只用 heldout，防过拟合）
    verifiable_only: True 时只保留 verifiable=true 的用例（L1 真实评估对象）
    """
    out = []
    for p in prompts:
        if not isinstance(p, dict):
            continue
        if split and p.get("split", "train") != split:
            continue
        if verifiable_only and not p.get("verifiable"):
            continue
        out.append(p)
    return out


def check_skill(skill_dir: Path):
    """返回 (skill_name, prompts, per_prompt_scores) 或抛异常。"""
    md = skill_dir / "SKILL.md"
    tp = skill_dir / "test-prompts.json"
    name = skill_dir.name
    if not md.exists():
        raise FileNotFoundError(f"{name}: 缺少 SKILL.md")
    skill_text = md.read_text(encoding="utf-8")
    if not tp.exists():
        return name, [], []
    data = json.loads(tp.read_text(encoding="utf-8"))
    prompts = data.get("prompts", [])
    scores = []
    for i, p in enumerate(prompts, 1):
        task = p.get("task", "")
        expect = p.get("expect", "")
        category = p.get("category", "")
        features = extract_features(expect)
        base = coverage(skill_text, features)
        score = base
        if category == "failure":
            # 反例用例：必须存在显式约束章节，否则视为未满足（惩罚）
            has_counter = any(marker.lower() in skill_text.lower()
                              for marker in COUNTER_EXAMPLE_MARKERS)
            if not has_counter:
                score = min(score, 0.3)
        elif category == "success":
            # 正向用例：正文应含流程性内容，缺失则微降
            has_process = any(marker in skill_text for marker in SUCCESS_EXTRAS)
            if not has_process:
                score = min(score, 0.8)
        scores.append(round(score, 3))
    return name, prompts, scores


def resolve_skills_dir(args_skills_dir):
    if args_skills_dir:
        return Path(args_skills_dir)
    candidates = [
        Path.cwd() / ".opencode" / "skills",
        ROOT.parent / "skills",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[-1]


# ---- 拓扑评测（§10.1） ----
TOPO_FIELDS = ["id", "name", "description", "agents", "status"]
EDGE_FIELDS = ["from", "to"]


def evaluate_topology(topo: dict, agents_dir: Path, templates_dir: Path):
    """对一个拓扑候选打分（0~1，确定性启发式）。

    分量:
      structure  (0.4): 字段完整、agents/edges 非空且格式正确
      coverage   (0.3): 引用的 agent 定义文件真实存在（agents_dir 或 templates）
      coherence  (0.3): 边端点都指向拓扑内 agent、无悬空引用
    """
    missing = [f for f in TOPO_FIELDS if not topo.get(f)]
    struct = 0.0 if missing else 1.0

    agents = topo.get("agents", [])
    edges = topo.get("edges", [])
    agent_names = set()
    cov_total, cov_hit = 0, 0
    if isinstance(agents, list):
        for a in agents:
            if isinstance(a, str):
                agent_names.add(a)
                cov_total += 1
                fname = f"{a}.md"
                if (agents_dir / fname).exists() or (templates_dir / fname).exists():
                    cov_hit += 1
            else:
                cov_total += 1  # 非字符串 agent 视为格式错误，不算命中
    coverage = (cov_hit / cov_total) if cov_total else 0.0

    coh_bad = 0
    coh_total = 0
    if isinstance(edges, list):
        for e in edges:
            if not isinstance(e, dict):
                coh_bad += 1
                coh_total += 1
                continue
            ef = [f for f in EDGE_FIELDS if not e.get(f)]
            coh_total += 1
            if ef:
                coh_bad += 1
            elif e["from"] not in agent_names or e["to"] not in agent_names:
                coh_bad += 1  # 边端点悬空
    coherence = (coh_total - coh_bad) / coh_total if coh_total else (1.0 if agents else 0.5)

    score = 0.4 * struct + 0.3 * coverage + 0.3 * coherence
    return round(score, 3), {
        "structure": round(struct, 3),
        "coverage": round(coverage, 3),
        "coherence": round(coherence, 3),
    }


def run_topology_mode(args, templates_dir):
    topo_path = ROOT / "agents" / "topology.json"
    if not topo_path.exists():
        print(f"[ERROR] 拓扑注册表不存在: {topo_path}", file=sys.stderr)
        return 1
    import json as _json
    try:
        data = _json.loads(topo_path.read_text(encoding="utf-8"))
    except ValueError as e:
        print(f"[ERROR] topology.json 解析失败: {e}", file=sys.stderr)
        return 1
    topologies = data.get("topologies", []) or []
    agents_dir = Path.cwd() / ".opencode" / "agents"

    results = []
    for t in topologies:
        score, parts = evaluate_topology(t, agents_dir, templates_dir)
        results.append({
            "topology": t.get("id"),
            "name": t.get("name"),
            "score": score,
            "components": parts,
            "status": t.get("status"),
        })

    if args.json:
        print(_json.dumps({"schema_version": 1, "mode": "topology",
                           "results": results}, ensure_ascii=False, indent=2))
        return 0
    for r in results:
        c = r["components"]
        print(f"{r['topology']} {r['name']}: {r['score']:.3f} "
              f"(struct={c['structure']:.2f} cov={c['coverage']:.2f} coh={c['coherence']:.2f}) "
              f"[{r['status']}]")
    if not results:
        print("拓扑注册表为空，无候选。")
    return 0


def resolve_judge_model(args):
    """判官模型解析：--model（会话模型）> SEA_EVAL_MODEL（便宜模型切换）> SEA_JUDGE_MODEL > 默认。"""
    import os
    return (args.model
            or os.environ.get("SEA_EVAL_MODEL")
            or os.environ.get("SEA_JUDGE_MODEL")
            or "gpt-4o-mini")


def judge_prompt_text(skill_text, index, p):
    return (
        "你是技能评估判官。判断技能是否满足用例的预期。\n"
        f"== 技能 SKILL.md ==\n{skill_text[:3000]}\n\n"
        f"== 用例 #{index}（{p.get('category')}） ==\n"
        f"任务: {p.get('task')}\n预期: {p.get('expect')}\n\n"
        "请仅输出 0.0~1.0 的一个分数（数字），表示满足程度。"
    )


def apply_budget(cases, budget):
    """预算控制：budget>0 时只评前 N 个用例；<=0 不设上限。"""
    if budget and budget > 0:
        return cases[:budget]
    return cases


def run_judge_mode(args, skills_dir):
    """LLM-as-Judge（§8.2/L1 真实评估）。

    两种判官来源：
      1. 内联判官（推荐，免配置）—— --emit/--apply 协议：
         --emit <file>  生成判定请求文件（skill 正文 + verifiable 用例），agent 用
                         当前会话模型逐条判定，写回 <file>.answers.json（scores 数组）
         --apply <file> 读取判定结果，计算总分输出（eval_source=l1）
         模型来源：--model（会话模型）> SEA_EVAL_MODEL（便宜模型）> 默认
      2. HTTP 判官（传统）—— 配置 SEA_JUDGE_URL/API_KEY 时直接调用
         未配置 → 回退确定性打分（eval_source=l0）并提示。

    预算：--budget N（>0 只评前 N 个 verifiable 用例；自动评估用推荐值，
          主动评估传 0 不设上限）。
    --split heldout 只评留出集（棘轮计分用）。
    """
    import os

    skill = args.skill
    if not skill:
        print("[ERROR] --mode judge 需要 --skill <技能名>", file=sys.stderr)
        return 1
    skill_dir = skills_dir / skill
    md = skill_dir / "SKILL.md"
    tp = skill_dir / "test-prompts.json"
    if not md.exists() or not tp.exists():
        print(f"[ERROR] 技能缺少 SKILL.md 或 test-prompts.json: {skill}",
              file=sys.stderr)
        return 1

    skill_text = md.read_text(encoding="utf-8")
    data = json.loads(tp.read_text(encoding="utf-8"))
    prompts = data.get("prompts", [])
    verifiable = filter_prompts(prompts, split=args.split, verifiable_only=True)
    verifiable = apply_budget(verifiable, args.budget)
    if not verifiable:
        print(f"[WARN] {skill} 没有 verifiable 用例（--split {args.split}），无可评对象",
              file=sys.stderr)
        return 0

    model = resolve_judge_model(args)

    # ---- 内联判官协议：emit（生成判定请求） ----
    if args.emit:
        req = {
            "protocol": "sea-inline-judge",
            "version": 1,
            "skill": skill,
            "judge_model": model,
            "skill_text": skill_text[:3000],
            "cases": [
                {"index": i, "id": p.get("id"), "category": p.get("category"),
                 "task": p.get("task"), "expect": p.get("expect")}
                for i, p in enumerate(verifiable, 1)
            ],
        }
        emit_path = Path(args.emit)
        emit_path.write_text(json.dumps(req, ensure_ascii=False, indent=2),
                             encoding="utf-8")
        print(f"[EMIT] 判定请求已写入 {emit_path}")
        print(f"请用当前会话模型（{model}）逐条判定，将 scores 数组写回 "
              f"{emit_path}.answers.json，然后运行 --apply {emit_path}")
        return 0

    # ---- 内联判官协议：apply（收集判定结果） ----
    if args.apply:
        apply_path = Path(args.apply)
        if not apply_path.exists():
            print(f"[ERROR] 判定请求不存在: {apply_path}", file=sys.stderr)
            return 1
        answers_path = apply_path.with_suffix(apply_path.suffix + ".answers.json")
        if not answers_path.exists():
            print(f"[ERROR] 判定结果不存在: {answers_path}（请先用会话模型判定并写回）",
                  file=sys.stderr)
            return 1
        try:
            ans = json.loads(answers_path.read_text(encoding="utf-8"))
        except ValueError as e:
            print(f"[ERROR] 判定结果解析失败: {e}", file=sys.stderr)
            return 1
        scores = ans.get("scores") if isinstance(ans, dict) else ans
        if not isinstance(scores, list) or len(scores) != len(verifiable):
            print(f"[ERROR] scores 应为长度 {len(verifiable)} 的数组（实际 {len(scores) if isinstance(scores, list) else '?'}）",
                  file=sys.stderr)
            return 1
        results = [max(0.0, min(1.0, float(s))) for s in scores]
        results = [round(s, 3) for s in results]
        total = round(sum(results) / len(results), 3) if results else 0.0
        if args.json:
            print(json.dumps({"schema_version": 1, "mode": "judge",
                              "skill": skill, "judge_model": model,
                              "eval_source": "l1", "split": args.split,
                              "judge_protocol": "inline",
                              "verifiable_cases": len(verifiable),
                              "score": total, "per_prompt": results},
                             ensure_ascii=False, indent=2))
        else:
            per = " ".join(f"p{i}={s:.2f}" for i, s in enumerate(results, 1))
            print(f"{skill}: {total}  (judge={model} split={args.split} "
                  f"inline l1: {per})")
        return 0

    # ---- HTTP 判官（传统路径） ----
    import urllib.request
    url = os.environ.get("SEA_JUDGE_URL")
    api_key = os.environ.get("SEA_JUDGE_API_KEY")
    if not url or not api_key:
        # 无 HTTP 配置时，推荐走内联协议（--emit/--apply）
        name, _, scores = check_skill(skill_dir)
        total = round(sum(scores) / len(scores), 3) if scores else 0.0
        print(f"[WARN] 未配置 SEA_JUDGE_URL/API_KEY。建议使用内联判官协议：", file=sys.stderr)
        print(f"      python {sys.argv[0]} --mode judge --skill {skill} --split {args.split or 'heldout'} --emit <file>", file=sys.stderr)
        print(f"      用会话模型判定后 --apply <file>。当前回退确定性打分 (score={total}, l0)", file=sys.stderr)
        print(f"{name}: {total}  (fallback heuristic)")
        return 0

    results = []
    for i, p in enumerate(verifiable, 1):
        judge_prompt = judge_prompt_text(skill_text, i, p)
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": judge_prompt}],
            "temperature": 0,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{url.rstrip('/')}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {api_key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            raw = body["choices"][0]["message"]["content"].strip()
            score = float(raw.split("\n")[0].split()[0])
            score = max(0.0, min(1.0, score))
        except Exception as e:
            print(f"[ERROR] 判官调用失败 用例#{i}: {e}", file=sys.stderr)
            score = 0.0
        results.append(round(score, 3))

    total = round(sum(results) / len(results), 3) if results else 0.0
    if args.json:
        print(json.dumps({"schema_version": 1, "mode": "judge",
                          "skill": skill, "judge_model": model,
                          "eval_source": "l1", "split": args.split,
                          "judge_protocol": "http",
                          "verifiable_cases": len(verifiable),
                          "score": total, "per_prompt": results},
                         ensure_ascii=False, indent=2))
    else:
        per = " ".join(f"p{i}={s:.2f}" for i, s in enumerate(results, 1))
        print(f"{skill}: {total}  (judge={model} split={args.split} "
              f"http l1: {per})")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills-dir", type=str, default=None,
                    help="技能库根目录（默认自动探测 .opencode/skills → 仓库根 skills/）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--mode", choices=["skill", "topology", "judge"], default="skill",
                    help="评测对象：技能（默认）、agent 拓扑（§10.1）或 LLM-as-Judge（§8.2）")
    ap.add_argument("--skill", type=str, default=None,
                    help="--mode judge 时指定技能名")
    ap.add_argument("--split", choices=["train", "heldout"], default=None,
                    help="只评指定 split 的用例（棘轮计分固定用 heldout）")
    ap.add_argument("--model", type=str, default=None,
                    help="LLM 判官模型（优先于 SEA_EVAL_MODEL/SEA_JUDGE_MODEL；agent 评估时直接传会话模型名）")
    ap.add_argument("--budget", type=int, default=0,
                    help="单次评估最多评 N 个 verifiable 用例（>0；0 不设上限。自动评估用推荐值，主动评估传 0）")
    ap.add_argument("--emit", type=str, default=None,
                    help="内联判官协议：生成判定请求文件（用会话模型判定后 --apply）")
    ap.add_argument("--apply", type=str, default=None,
                    help="内联判官协议：读取判定请求并计算分数（需 <file>.answers.json 含 scores 数组）")
    args = ap.parse_args()

    if args.mode == "topology":
        return run_topology_mode(args, ROOT / "templates")
    if args.mode == "judge":
        skills_dir = resolve_skills_dir(args.skills_dir)
        return run_judge_mode(args, skills_dir)

    skills_dir = resolve_skills_dir(args.skills_dir)
    if not skills_dir.exists():
        print(f"[ERROR] 技能库目录不存在: {skills_dir}", file=sys.stderr)
        return 1

    results = []
    for sub in sorted(skills_dir.iterdir()):
        if not sub.is_dir() or sub.name.startswith("_"):
            continue
        try:
            name, prompts, scores = check_skill(sub)
        except Exception as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            continue
        if not prompts:
            continue  # 无评测集的技能不参与打分
        # L0 启发式打分：--split 时按 split 过滤，eval_source=l0
        if args.split:
            kept = filter_prompts(prompts, split=args.split)
            kept_ids = {p.get("id") for p in kept}
            scores = [s for i, s in enumerate(scores)
                      if prompts[i].get("id") in kept_ids]
        total = round(sum(scores) / len(scores), 3) if scores else 0.0
        results.append({
            "skill": name,
            "score": total,
            "prompts": len(scores),
            "per_prompt": scores,
            "eval_source": "l0",
        })

    if args.json:
        print(json.dumps({"schema_version": 1, "eval_source": "l0",
                          "split": args.split, "results": results},
                         ensure_ascii=False, indent=2))
        return 0

    for r in results:
        per = " ".join(f"p{i}={s:.2f}" for i, s in enumerate(r["per_prompt"], 1))
        print(f"{r['skill']}: {r['score']:.3f}  ({r['prompts']} 用例: {per}) "
              f"[l0{split_label(args.split)}]")
    if not results:
        print("没有技能带 test-prompts.json，无评测对象。")
    return 0


def split_label(split):
    return f"/{split}" if split else ""


if __name__ == "__main__":
    sys.exit(main())
