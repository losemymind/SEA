#!/usr/bin/env python3
"""framework-version.py — 框架版本读取与已安装工作区过期检测（P0 版本兼容性）。

用法:
    python SEA/scripts/framework-version.py                    # 打印框架版本
    python SEA/scripts/framework-version.py --installed <工作区>  # 检查工作区 SEA 版本是否过期
    python SEA/scripts/framework-version.py --check            # 校验 SEA/VERSION 与仓库 VERSION 一致

退出码: 0 正常/无过期; 1 已安装工作区版本过期或 SEA/VERSION 与仓库不一致。
零第三方依赖（仅标准库）。
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent      # SEA/
REPO_ROOT = ROOT.parent                             # 框架仓库根


def read_version(path: Path):
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--installed", type=str, default=None,
                    help="目标工作区路径，检查其 SEA/VERSION 是否过期")
    ap.add_argument("--check", action="store_true",
                    help="校验 SEA/VERSION 与仓库 VERSION 一致")
    args = ap.parse_args()

    sea_ver = read_version(ROOT / "VERSION")
    repo_ver = read_version(REPO_ROOT / "VERSION")

    if args.check:
        if not sea_ver or not repo_ver:
            print("[ERROR] VERSION 文件缺失（SEA/VERSION 或 仓库 VERSION）", file=sys.stderr)
            return 1
        if sea_ver != repo_ver:
            print(f"[ERROR] 版本不一致: SEA/VERSION={sea_ver} 仓库 VERSION={repo_ver}", file=sys.stderr)
            return 1
        print(f"OK：版本一致 {sea_ver}")
        return 0

    if not sea_ver:
        print("[ERROR] SEA/VERSION 缺失", file=sys.stderr)
        return 1

    if args.installed:
        ws = Path(args.installed)
        installed_ver = read_version(ws / "SEA" / "VERSION")
        if installed_ver is None:
            print(f"[ERROR] {ws}\\SEA\\VERSION 缺失（可能未安装或安装损坏）", file=sys.stderr)
            return 1
        if installed_ver != sea_ver:
            print(f"[WARN] 工作区已过期: 已装 {installed_ver}，框架最新 {sea_ver}")
            print(f"      请按 INSTALL.md 升级流程重新复制 SEA/ 与 AGENTS.md")
            return 1
        print(f"OK：工作区版本最新（{installed_ver}）")
        return 0

    print(sea_ver)
    return 0


if __name__ == "__main__":
    sys.exit(main())
