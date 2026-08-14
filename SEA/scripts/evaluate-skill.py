#!/usr/bin/env python3
"""evaluate-skill.py — 独立技能评测器（替代生成器自评，为棘轮提供可复现基线）。

原理：确定性覆盖度打分。对每个技能自带的 test-prompts.json：
  1. 从每个用例的 expect 中提取关键短语（去除标点后的子串特征）
  2. 检查这些特征是否出现在 SKILL.md 正文中（覆盖度 = 命中的特征 / 总特征）
  3. 用例得分 = 覆盖度；技能得分 = 所有用例得分的均值
  4. failure 类用例要求 SKILL.md 有"反例/不要这样"约束，故对 failure 用例
     额外检查反例章节存在性

用途：在技能创建/演进前后各跑一次，得到 score_before / score_after，
供 P2 技能生命周期与棘轮使用。分数是确定性的，不依赖 LLM。

用法:
    python SEA/scripts/evaluate-skill.py [--skills-dir <技能库根目录>] [--json]

输出:
    无 --json: 逐技能打印每个用例得分与技能总分
    --json:    输出 JSON 供脚本消费（含 skill、score、per_prompt）

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills-dir", type=str, default=None,
                    help="技能库根目录（默认自动探测 .opencode/skills → 仓库根 skills/）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

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
        total = round(sum(scores) / len(scores), 3) if scores else 0.0
        results.append({
            "skill": name,
            "score": total,
            "prompts": len(prompts),
            "per_prompt": scores,
        })

    if args.json:
        print(json.dumps({"schema_version": 1, "results": results},
                         ensure_ascii=False, indent=2))
        return 0

    for r in results:
        per = " ".join(f"p{i}={s:.2f}" for i, s in enumerate(r["per_prompt"], 1))
        print(f"{r['skill']}: {r['score']:.3f}  ({r['prompts']} 用例: {per})")
    if not results:
        print("没有技能带 test-prompts.json，无评测对象。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
