#!/usr/bin/env python3
"""validate-skill.py — 校验 skills/ 下技能资产的 frontmatter 与 _evolutions/evolutions.json。

检查项:
  1. 每个技能目录（排除 _ 开头）必须含 SKILL.md，且 frontmatter 有非空 name / description
  2. frontmatter 解析：--- 包裹的 YAML
  3. _evolutions/evolutions.json：schema 字段完整、kind/status 枚举合法、id 唯一

用法:
    python scripts/validate-skill.py

退出码: 0 全部通过; 1 存在错误。零第三方依赖（仅标准库 + PyYAML）。
"""

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
SKILLS_DIR = ROOT / "skills"

FM_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

VALID_KIND = {"FIX", "DERIVED", "CAPTURED"}
VALID_STATUS = {"pending", "solidified", "rejected", "reverted"}
REQUIRED_EVO = ["id", "skill", "kind", "signal", "proposal", "status", "created"]


def parse_frontmatter(text: str):
    m = FM_RE.match(text)
    if not m:
        return None
    try:
        return safe_load(m.group(1))
    except Exception:
        return None


def check_skills(errors):
    count = 0
    for sub in sorted(SKILLS_DIR.iterdir()):
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
    return count


def check_evolutions(errors):
    evo_dir = SKILLS_DIR / "_evolutions"
    path = evo_dir / "evolutions.json"
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


def main():
    errors = []
    skill_count = check_skills(errors)
    check_evolutions(errors)

    if errors:
        for e in errors:
            print(f"[ERROR] {e}", file=sys.stderr)
        print(f"\n{len(errors)} 个问题，请修正后重跑。", file=sys.stderr)
        return 1
    print(f"OK：{skill_count} 个技能 + evolutions.json 校验通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
