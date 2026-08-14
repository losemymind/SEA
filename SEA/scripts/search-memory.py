#!/usr/bin/env python3
"""search-memory.py — 记忆检索召回（补齐"只写不检"短板）。

对 memory/*.yaml 的条目做关键词 + 结构索引检索，返回相关条目 + 置信度。
agent 在需要经验时用它检索，而非靠读文件碰运气。

检索算法（零依赖、确定性）:
  1. 查询分词：中英文标点切分，保留有效词
  2. 对每条 active 条目，在 claim / evidence / contrast / category 字段
     做词频匹配（二元组 + 整词）
  3. 置信度 = 0.7 * 查询覆盖度（命中查询词比例）
            + 0.2 * 条目 confidence 字段
            + 0.1 * 热度（hits 归一化）
  4. 按置信度降序返回

用法:
    python SEA/scripts/search-memory.py "复制漂移" [--top 5] [--category experience] [--json]
    python SEA/scripts/search-memory.py --all           # 列出全部 active 条目

退出码: 0 完成（有或无结果）；1 参数错误。
零第三方依赖（仅标准库 + PyYAML）。
"""

import argparse
import re
import sys
from pathlib import Path

try:
    from yaml import safe_load
except ImportError:  # pragma: no cover
    sys.stderr.write("缺少依赖：请先 `pip install pyyaml`\n")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = ROOT / "memory"

# 中文/英文标点与空白，分词时剔除
SPLIT_RE = re.compile(r"[\s，。；：、（）()【】\[\]{}《》<>\"'‘’“”·—…!?！？,.!:;/-]+")
# 无意义高频词（停用词）
STOPWORDS = {
    "一个", "这个", "那个", "进行", "以及", "用于", "因为", "所以", "如果",
    "需要", "应该", "必须", "不要", "没有", "可以", "通过", "以下", "本仓库",
    "相关", "首先", "最后", "then", "and", "the", "for", "with", "that",
}


def load_entries():
    """返回 [(file, entry), ...]，含全部 yaml 条目。"""
    out = []
    for path in sorted(DEFAULT_DIR.glob("*.yaml")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = safe_load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        for entry in data.get("entries", []) or []:
            if isinstance(entry, dict) and entry.get("id"):
                out.append((path.name, entry))
    return out


def tokenize(text: str):
    """分词：去标点、去停用词，返回词列表。"""
    words = [w.lower() for w in SPLIT_RE.split(str(text)) if w and w not in STOPWORDS]
    return words


def text_features(text: str):
    """文本特征集合：整词 + 相邻字符二元组（中文短语切分不足时靠二元组匹配）。"""
    words = tokenize(text)
    feats = set(words)
    # 对每个词内的相邻字符二元组（中文 2-gram，兼顾英文子串）
    for w in words:
        for i in range(len(w) - 1):
            feats.add(w[i:i + 2])
    return feats


def bigrams(words):
    return {f"{a} {b}" for a, b in zip(words, words[1:])} | set(words)


def search(query, entries, category=None, top=5):
    """返回 [(score, file, entry, matched_fields), ...]。"""
    q_words = tokenize(query)
    if not q_words:
        return []
    q_feats = text_features(query)          # 查询特征（整词 + 字符二元组）
    q_bigrams = bigrams(q_words)

    results = []
    for fname, entry in entries:
        if entry.get("deprecated"):
            continue
        if category and entry.get("category") != category:
            continue

        # 可检索文本：claim / evidence / contrast / category
        texts = {
            "claim": str(entry.get("claim", "")),
            "evidence": " ".join(str(x) for x in (entry.get("evidence") or [])),
            "contrast": str(entry.get("contrast", "")),
            "category": str(entry.get("category", "")),
        }
        all_text = " ".join(texts.values())
        text_feats = text_features(all_text)          # 条目特征
        text_words = set(tokenize(all_text))
        text_bigrams = bigrams(tokenize(all_text))

        if not text_words:
            continue

        # 整词命中 + 二元组命中 + 字符二元组命中
        word_hits = sum(1 for w in q_words if w in text_words)
        bg_hits = sum(1 for g in q_bigrams if g in text_bigrams)
        feat_hits = sum(1 for g in q_feats if g in text_feats)
        # 查询覆盖度：字符二元组为主（中文稳健），整词/二元组加成
        cov = (0.5 * feat_hits + 0.3 * word_hits + 0.2 * bg_hits) / max(1, len(q_feats))

        if cov <= 0:
            continue

        # 置信度 = 覆盖度 + 条目 confidence + 热度
        conf_field = entry.get("confidence")
        conf = conf_field if isinstance(conf_field, (int, float)) else 0.5
        hits = entry.get("hits") if isinstance(entry.get("hits"), int) else 0
        heat = min(hits / 5.0, 1.0)
        score = round(0.7 * min(cov, 1.0) + 0.2 * conf + 0.1 * heat, 3)

        matched = [f for f, t in texts.items()
                   if q_feats & text_features(t)]
        results.append((score, fname, entry, matched))

    results.sort(key=lambda x: -x[0])
    return results[:top]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?", default="", help="检索词")
    ap.add_argument("--top", type=int, default=5, help="返回条数（默认 5）")
    ap.add_argument("--category", choices=["preference", "experience", "engineering"],
                    default=None, help="按分类过滤")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--all", action="store_true", help="列出全部 active 条目")
    args = ap.parse_args()

    entries = load_entries()
    if args.all:
        print(f"共 {len([e for _, e in entries if not e.get('deprecated')])} 条 active 记忆：")
        for fname, entry in entries:
            if entry.get("deprecated"):
                continue
            print(f"  [{fname}] {entry.get('id')} ({entry.get('category')}) "
                  f"{str(entry.get('claim', ''))[:70]}")
        return 0

    if not args.query:
        print("[ERROR] 需要检索词，或 --all 列出全部", file=sys.stderr)
        return 1

    results = search(args.query, entries, category=args.category, top=args.top)
    if not results:
        print(f"无匹配（查询：{args.query}）。")
        return 0

    if args.json:
        import json
        out = [{"id": e.get("id"), "file": f, "score": s,
                "category": e.get("category"), "type": e.get("type"),
                "claim": e.get("claim"), "matched": m}
               for s, f, e, m in results]
        print(json.dumps({"query": args.query, "results": out},
                         ensure_ascii=False, indent=2))
        return 0

    print(f"检索「{args.query}」命中 {len(results)} 条：")
    for s, f, e, m in results:
        print(f"\n  [{s:.3f}] {e.get('id')} ({f}, {e.get('category')}/{e.get('type')})")
        print(f"    claim: {str(e.get('claim', ''))[:100]}")
        print(f"    命中字段: {', '.join(m) if m else '模糊'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
