#!/usr/bin/env python3
"""dedup-check.py — 检测 memory/*.yaml 中的近重复条目。

用法:
    python scripts/dedup-check.py [阈值=0.6]

按 claim 的字符二元组 Jaccard 相似度检测近重复，给出合并建议。
阈值越低越宽松。输出仅提示，合并需人工确认。
退出码: 0 无疑似重复; 1 存在疑似重复。
零第三方依赖（仅标准库）。
"""

import sys
from pathlib import Path

try:
    from yaml import safe_load
except ImportError:  # pragma: no cover
    sys.stderr.write("缺少依赖：请先 `pip install pyyaml`\n")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = ROOT / "memory"


def bigrams(text: str):
    text = "".join(ch for ch in text.lower() if ch.strip())
    return {text[i:i + 2] for i in range(len(text) - 1)}


def jaccard(a: str, b: str):
    ba, bb = bigrams(a), bigrams(b)
    if not ba or not bb:
        return 0.0
    return len(ba & bb) / len(ba | bb)


def collect_all():
    """返回 [(file, entry), ...] 列表，含 id 与 claim。"""
    out = []
    for path in sorted(DEFAULT_DIR.glob("*.yaml")):
        with open(path, "r", encoding="utf-8") as f:
            data = safe_load(f)
        if not isinstance(data, dict):
            continue
        for entry in data.get("entries", []) or []:
            if isinstance(entry, dict) and entry.get("claim"):
                out.append((path.name, entry))
    return out


def main(argv):
    threshold = float(argv[0]) if argv else 0.6
    items = collect_all()
    flagged = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            f1, e1 = items[i]
            f2, e2 = items[j]
            sim = jaccard(str(e1.get("claim", "")), str(e2.get("claim", "")))
            if sim >= threshold:
                flagged.append((sim, f1, e1.get("id"), f2, e2.get("id"),
                                e1.get("claim"), e2.get("claim")))

    if not flagged:
        print(f"OK：{len(items)} 个条目无疑似重复（阈值 {threshold}）。")
        return 0

    for sim, f1, i1, f2, i2, c1, c2 in flagged:
        print(f"[疑似重复] 相似度 {sim:.2f}")
        print(f"  A. {f1} {i1}: {c1}")
        print(f"  B. {f2} {i2}: {c2}")
        print("  建议：保留证据更强、更新时间更新的条目，另一条合并或标记 deprecated。")
        print()
    print(f"{len(flagged)} 组疑似重复，请人工确认。", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
