#!/usr/bin/env python3
"""validate-skill.py — 校验技能库的 frontmatter 与 _evolutions/evolutions.json。

检查项:
  1. 每个技能目录（排除 _ 开头）必须含 SKILL.md，且 frontmatter 有非空 name / description
  2. frontmatter 解析：--- 包裹的 YAML
  3. 技能目录内的 test-prompts.json 必须是合法 JSON 且符合 schema
  4. _evolutions/evolutions.json：schema 字段完整、kind/status 枚举合法、id 唯一

用法:
    python SEA/scripts/validate-skill.py [--skills-dir <技能库根目录>]

技能库根目录：显式传入，或自动探测 .opencode/skills → 仓库根 skills/（默认）。
退出码: 0 全部通过; 1 存在错误。零第三方依赖（仅标准库 + PyYAML）。
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from yaml import safe_load
except ImportError:  # pragma: no cover
    sys.stderr.write("缺少依赖：请先 `pip install pyyaml`\n")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent

FM_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

VALID_KIND = {"FIX", "DERIVED", "CAPTURED"}
VALID_STATUS = {"pending", "solidified", "rejected", "reverted"}
REQUIRED_EVO = ["id", "skill", "kind", "signal", "proposal", "status", "created"]
PROMPT_CATEGORIES = {"success", "failure", "boundary"}


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


def parse_frontmatter(text: str):
    m = FM_RE.match(text)
    if not m:
        return None
    try:
        return safe_load(m.group(1))
    except Exception:
        return None


def check_test_prompts(subdir, errors):
    """校验技能目录下的 test-prompts.json（若有）。"""
    path = subdir / "test-prompts.json"
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(f"{subdir.name}/test-prompts.json: JSON 解析失败: {e}")
        return
    if not isinstance(data, dict):
        errors.append(f"{subdir.name}/test-prompts.json: 顶层应为对象")
        return
    if not isinstance(data.get("schema_version"), int):
        errors.append(f"{subdir.name}/test-prompts.json: 缺少整数 schema_version")
    if not isinstance(data.get("prompts"), list):
        errors.append(f"{subdir.name}/test-prompts.json: 缺少 prompts 数组")
        return
    for i, p in enumerate(data["prompts"], 1):
        if not isinstance(p, dict):
            errors.append(f"{subdir.name}/test-prompts.json 用例#{i}: 应为对象")
            continue
        for f in ("id", "task", "expect", "category"):
            if not p.get(f):
                errors.append(f"{subdir.name}/test-prompts.json 用例#{i}: 缺少 {f}")
        if p.get("category") not in PROMPT_CATEGORIES:
            errors.append(f"{subdir.name}/test-prompts.json 用例#{i}: category 非法（应为 {sorted(PROMPT_CATEGORIES)}）")
        # 新字段校验：verifiable(布尔) / split(train|heldout)
        if "verifiable" in p and not isinstance(p.get("verifiable"), bool):
            errors.append(f"{subdir.name}/test-prompts.json 用例#{i}: verifiable 应为布尔")
        if "split" in p and p.get("split") not in ("train", "heldout"):
            errors.append(f"{subdir.name}/test-prompts.json 用例#{i}: split 非法（应为 train|heldout）")


def check_skills(skills_dir, errors):
    if not skills_dir.exists():
        errors.append(f"技能库目录不存在: {skills_dir}")
        return 0
    count = 0
    for sub in sorted(skills_dir.iterdir()):
        if not sub.is_dir() or sub.name.startswith("_"):
            continue
        count += 1
        md = sub / "SKILL.md"
        if not md.exists():
            errors.append(f"{sub.name}: 缺少 SKILL.md")
            continue
        fm = parse_frontmatter(md.read_text(encoding="utf-8"))
        if fm is None:
            errors.append(f"{sub.name}: SKILL.md frontmatter 缺失或 YAML 解析失败")
            continue
        if not isinstance(fm, dict):
            errors.append(f"{sub.name}: frontmatter 应为映射")
            continue
        if not fm.get("name"):
            errors.append(f"{sub.name}: frontmatter 缺少非空 name")
        if not fm.get("description"):
            errors.append(f"{sub.name}: frontmatter 缺少非空 description")
        check_test_prompts(sub, errors)
    return count


def check_evolutions(skills_dir, errors):
    path = skills_dir / "_evolutions" / "evolutions.json"
    if not path.exists():
        errors.append("_evolutions/evolutions.json 缺失")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(f"evolutions.json: JSON 解析失败: {e}")
        return
    evos = data.get("evolutions", [])
    seen = set()
    # 第一遍：收集 id 与字段级校验
    for i, evo in enumerate(evos, 1):
        for field in REQUIRED_EVO:
            if field not in evo:
                errors.append(f"evolutions.json 条目#{i}: 缺少 {field}")
        if evo.get("kind") not in VALID_KIND:
            errors.append(f"evolutions.json 条目#{i}: kind 非法 {evo.get('kind')}（应为 {sorted(VALID_KIND)}）")
        if evo.get("status") not in VALID_STATUS:
            errors.append(f"evolutions.json 条目#{i}: status 非法 {evo.get('status')}（应为 {sorted(VALID_STATUS)}）")
        eid = evo.get("id")
        if eid:
            if eid in seen:
                errors.append(f"evolutions.json 条目#{i}: id 重复 {eid}")
            seen.add(eid)
        if evo.get("parent_id") is not None and not isinstance(evo.get("parent_id"), str):
            errors.append(f"evolutions.json 条目#{i}: parent_id 应为字符串")
    # 第二遍：parent_id 引用完整性（允许指向自身=根节点标记）
    for i, evo in enumerate(evos, 1):
        pid = evo.get("parent_id")
        if pid is not None and pid not in seen:
            errors.append(f"evolutions.json 条目#{i}: parent_id {pid} 指向不存在的演进条目")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills-dir", type=str, default=None,
                    help="技能库根目录（默认自动探测 .opencode/skills → 仓库根 skills/）")
    args = ap.parse_args()

    skills_dir = resolve_skills_dir(args.skills_dir)
    errors = []
    skill_count = check_skills(skills_dir, errors)
    check_evolutions(skills_dir, errors)

    if errors:
        for e in errors:
            print(f"[ERROR] {e}", file=sys.stderr)
        print(f"\n{len(errors)} 个问题，请修正后重跑。", file=sys.stderr)
        return 1
    print(f"OK：{skill_count} 个技能（{skills_dir}）+ evolutions.json 校验通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
