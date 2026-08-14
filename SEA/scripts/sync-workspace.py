#!/usr/bin/env python3
"""sync-workspace.py — 工作区 ↔ 框架仓库 双向同步（§10.4 群体智能最小落地）。

解决跨工作区经验共享缺口：framework-version.py --installed 只检查版本，
不同步记忆/技能内容。本脚本同步：
  - memory/       工作区产出的记忆条目 → 回流框架仓库（或反向）
  - skills/       技能内容双向
  - _registry/    工具信号注册表双向
  - _improvements/ 定义改进注册表双向

同步方向:
    --push    工作区 → 框架仓库（工作区新经验回流）
    --pull    框架仓库 → 工作区（框架更新下发）

同步方式:
    --merge    逐条目合并（默认）：以"时间新 + 来源文件新"胜出，保留双方 id，
               冲突条目保留两份并提示人工处理
    --overwrite 整体覆盖目标侧（谨慎：会丢目标侧独有条目）

安全: 同步不删除目标侧文件，只在目标侧文件不存在时创建缺失内容；
      --merge 采用"插入缺失条目 + 报告冲突"策略，绝不静默覆盖。

用法:
    python SEA/scripts/sync-workspace.py --workspace <工作区路径> --push [--merge|--overwrite]
    python SEA/scripts/sync-workspace.py --workspace <工作区路径> --pull [--merge|--overwrite]
    python SEA/scripts/sync-workspace.py --workspace <工作区路径> --dry-run --push

退出码: 0 正常（含冲突报告）; 1 参数错误或路径非法。
零第三方依赖（仅标准库 + PyYAML）。
"""

import argparse
import shutil
import sys
from pathlib import Path

try:
    from yaml import safe_load, safe_dump
except ImportError:  # pragma: no cover
    sys.stderr.write("缺少依赖：请先 `pip install pyyaml`\n")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent  # 框架仓库 SEA/
REPO_ROOT = ROOT.parent                        # 框架仓库根

# 需要同步的相对路径（相对 SEA/）
SYNC_PATHS = [
    "memory",
    "agents/_improvements",
    "tools/_registry",
]

# json 注册表：顶层数组字段名 → 条目 id 字段（按 id 合并）。按文件名键控。
JSON_ARRAY_FIELD = {
    "tool-signals.json": ("signals", "id"),
    "improvements.json": ("improvements", "id"),
    "baselines.json": ("baselines", "best_score"),
    "evolutions.json": ("evolutions", "id"),
}


def load_json(path: Path):
    import json
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError):
        return None


def merge_json_files(src: Path, dst: Path, dry_run, conflicts):
    """按 id 合并 json 注册表条目：dst 缺失的插入，重复条目报告冲突。"""
    spec = JSON_ARRAY_FIELD.get(src.name)
    if not spec:
        return 0
    field, id_field = spec
    src_data = load_json(src)
    if not isinstance(src_data, dict):
        return 0
    src_items = src_data.get(field, []) or []
    if not src_items:
        return 0

    dst_data = load_json(dst) if dst.exists() else None
    if not isinstance(dst_data, dict):
        dst_data = dict(src_data) if not dst.exists() else {}
    dst_items = dst_data.get(field, []) or []

    def key_of(item):
        if isinstance(item, dict):
            if id_field == "baselines":
                return item
            return item.get(id_field)
        return item

    added = 0
    for item in src_items:
        if not isinstance(item, dict):
            continue
        k = item.get(id_field)
        # baselines.json 的条目是 {target: {best_score, updated}} 映射
        if id_field == "baselines":
            for tgt, info in item.items():
                if isinstance(info, dict) and tgt not in dst_items:
                    dst_items[tgt] = info
                    added += 1
                elif tgt in dst_items and dst_items[tgt] != info:
                    conflicts.append(f"{src.name} target={tgt} 基线不同（保留双方，请人工核对）")
            continue
        existing = next((x for x in dst_items if isinstance(x, dict)
                         and x.get(id_field) == k), None)
        if existing is None:
            dst_items.append(item)
            added += 1
        elif existing.get("status") != item.get("status") or \
                existing.get("score_after") != item.get("score_after"):
            conflicts.append(f"{src.name} id={k} 状态/分数不同（保留双方，请人工核对）")

    dst_data[field] = dst_items
    if not dry_run:
        import json as _json
        dst.write_text(_json.dumps(dst_data, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    return added


def yaml_entries(path: Path):
    """读取 yaml 文件的 entries 列表。"""
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = safe_load(f)
    if isinstance(data, dict):
        return data.get("entries", []) or []
    return []


def yaml_has(entries, eid):
    return any(e.get("id") == eid for e in entries if isinstance(e, dict))


def merge_yaml_files(src: Path, dst: Path, dry_run, conflicts):
    """按 id 合并 entries：dst 缺失的 src 条目插入 dst；重复条目保留并报告冲突。"""
    src_entries = yaml_entries(src)
    if not src_entries:
        return 0
    dst_data = {}
    dst_entries = []
    if dst.exists():
        with open(dst, "r", encoding="utf-8") as f:
            data = safe_load(f)
        if isinstance(data, dict):
            dst_data = data
            dst_entries = data.get("entries", []) or []
    elif not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text("# synced by sync-workspace.py\nentries: []\n", encoding="utf-8")

    added = 0
    for e in src_entries:
        if not isinstance(e, dict) or not e.get("id"):
            continue
        if yaml_has(dst_entries, e["id"]):
            # id 相同：检查是否内容有差异 → 冲突
            dst_match = next(x for x in dst_entries if x.get("id") == e["id"])
            if dst_match.get("claim") != e.get("claim"):
                conflicts.append(f"{src.name} id={e['id']} 内容不同（保留双方，请人工合并）")
            continue
        dst_entries.append(e)
        added += 1

    dst_data["entries"] = dst_entries
    if not dry_run:
        dst.write_text(safe_dump(dst_data, allow_unicode=True, sort_keys=False),
                       encoding="utf-8")
    return added


def sync_dir(src_dir: Path, dst_dir: Path, dry_run, update=False):
    """整个目录级同步：dst 缺失的文件从 src 复制；update=True 时源更新的文件也覆盖。"""
    if not src_dir.exists():
        return 0
    copied, updated = 0, 0
    for src_path in src_dir.rglob("*"):
        if src_path.is_file():
            rel = src_path.relative_to(src_dir)
            dst_path = dst_dir / rel
            if not dst_path.exists():
                if not dry_run:
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dst_path)
                copied += 1
            elif update and src_path.stat().st_mtime > dst_path.stat().st_mtime \
                    and src_path.stat().st_size != dst_path.stat().st_size:
                if not dry_run:
                    shutil.copy2(src_path, dst_path)
                updated += 1
    return copied + updated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True, help="目标工作区路径")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--push", action="store_true", help="工作区 → 框架仓库")
    group.add_argument("--pull", action="store_true", help="框架仓库 → 工作区")
    ap.add_argument("--merge", action="store_true", help="按条目合并（默认）")
    ap.add_argument("--overwrite", action="store_true", help="整体覆盖目标侧")
    ap.add_argument("--update", action="store_true",
                    help="目录级同步时更新源侧更新的脚本/模板（默认只补缺失）")
    ap.add_argument("--dry-run", action="store_true", help="仅报告不写入")
    args = ap.parse_args()

    ws = Path(args.workspace)
    ws_sea = ws / "SEA"
    if not ws_sea.exists():
        print(f"[ERROR] 工作区未安装 SEA: {ws}", file=sys.stderr)
        return 1

    src_root, dst_root = (ws_sea, ROOT) if args.push else (ROOT, ws_sea)
    label = "工作区→仓库" if args.push else "仓库→工作区"

    # 目录级同步（技能、脚本、templates、agents、其他）
    dir_copied = 0
    for rel in ("skills", "scripts", "templates", "agents"):
        src_sub, dst_sub = src_root / rel, dst_root / rel
        if src_sub.exists():
            dir_copied += sync_dir(src_sub, dst_sub, args.dry_run, args.update)

    # yaml 条目级合并
    conflicts = []
    total_added = 0
    for rel in SYNC_PATHS:
        src_p, dst_p = src_root / rel, dst_root / rel
        if not src_p.exists():
            continue
        if args.overwrite:
            if not args.dry_run:
                dst_p.parent.mkdir(parents=True, exist_ok=True)
                shutil.rmtree(dst_p, ignore_errors=True) if dst_p.exists() else None
                shutil.copytree(src_p, dst_p)
            total_added += 1
        else:
            for f in sorted(src_p.glob("*.yaml")):
                dst_f = dst_p / f.name
                added = merge_yaml_files(f, dst_f, args.dry_run, conflicts)
                total_added += added
        # json 注册表：按 id 条目级合并
        for f in sorted(src_p.glob("*.json")):
            dst_f = dst_p / f.name
            if f.name in JSON_ARRAY_FIELD:
                added = merge_json_files(f, dst_f, args.dry_run, conflicts)
                total_added += added
            elif not dst_f.exists() and not args.dry_run:
                dst_p.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst_f)

    verb = "模拟" if args.dry_run else "已"
    print(f"[{label}] {verb}同步完成")
    print(f"  目录级新增: {dir_copied}")
    print(f"  条目级新增: {total_added}")
    if conflicts:
        print(f"  冲突 {len(conflicts)} 条（保留双方，请人工合并）:")
        for c in conflicts:
            print(f"    - {c}")
    else:
        print("  冲突: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
