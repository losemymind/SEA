#!/usr/bin/env python3
"""validate-memory.py — 校验 memory/*.yaml 条目符合 templates/lesson-schema.yaml。

用法:
    python scripts/validate-memory.py [memory/*.yaml ...]

默认扫描 memory/ 下所有 .yaml（README.md / NOTES.md 除外）。
退出码: 0 全部通过; 1 存在错误（必填字段/类型/唯一性）。
零第三方依赖（仅标准库）。
"""

import re
import sys
from pathlib import Path

import yaml  # PyYAML，若缺失则提示

try:
    from yaml import safe_load
except ImportError:  # pragma: no cover
    sys.stderr.write("缺少依赖：请先 `pip install pyyaml`\n")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = ROOT / "memory"
SCHEMA_PATH = ROOT / "templates" / "lesson-schema.yaml"

ID_RE = re.compile(r"^m-\d{8}-\d{3}$")


def load_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return safe_load(f)


def collect_entries(path: Path):
    """返回 (文件名, [条目...]) 列表；文件结构为顶层 entries: [...]。"""
    with open(path, "r", encoding="utf-8") as f:
        data = safe_load(f)
    if not isinstance(data, dict):
        return []
    return data.get("entries", []) or []


def main(argv):
    schema = load_schema()
    required = schema["required_fields"]
    type_enum = set(schema["type_enum"])
    category_enum = set(schema["category_enum"])
    source_enum = set(schema["source_enum"])

    targets = [Path(a) for a in argv] if argv else sorted(DEFAULT_DIR.glob("*.yaml"))
    errors = []
    seen_ids = {}

    for path in targets:
        if not path.exists():
            errors.append(f"{path}: 文件不存在")
            continue
        for i, entry in enumerate(collect_entries(path)):
            loc = f"{path.name} 条目#{i + 1}"
            if not isinstance(entry, dict):
                errors.append(f"{loc}: 非字典条目")
                continue

            eid = entry.get("id")
            if not eid:
                errors.append(f"{loc}: 缺少 id")
            else:
                if not ID_RE.match(str(eid)):
                    errors.append(f"{loc}: id 格式非法（应为 m-YYYYMMDD-NNN）: {eid}")
                if eid in seen_ids:
                    errors.append(f"{loc}: id 重复 {eid}（已见于 {seen_ids[eid]}）")
                else:
                    seen_ids[eid] = path.name

            for field in required:
                if field not in entry or entry[field] in (None, ""):
                    errors.append(f"{loc}: 缺少必填字段 {field}")

            t = entry.get("type")
            if t and t not in type_enum:
                errors.append(f"{loc}: type 非法 {t}（应为 {sorted(type_enum)}）")
            c = entry.get("category")
            if c and c not in category_enum:
                errors.append(f"{loc}: category 非法 {c}（应为 {sorted(category_enum)}）")
            s = entry.get("source")
            if s and s not in source_enum:
                errors.append(f"{loc}: source 非法 {s}（应为 {sorted(source_enum)}）")

            conf = entry.get("confidence")
            if conf is not None and not isinstance(conf, (int, float)):
                errors.append(f"{loc}: confidence 应为数字")
            elif isinstance(conf, (int, float)) and not (0.0 <= conf <= 1.0):
                errors.append(f"{loc}: confidence 越界 {conf}")

            hits = entry.get("hits")
            if hits is not None and not isinstance(hits, int):
                errors.append(f"{loc}: hits 应为整数")

    if errors:
        for e in errors:
            print(f"[ERROR] {e}", file=sys.stderr)
        print(f"\n{len(errors)} 个问题，请修正后重跑。", file=sys.stderr)
        return 1
    print(f"OK：{len(targets)} 个文件校验通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
