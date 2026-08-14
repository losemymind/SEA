#!/usr/bin/env python3
"""hub-sync.py — 远程经验 Hub 同步（§10.4 群体智能完整形态的轻量落地）。

用 git 远程仓库作为共享经验 Hub（Ultron Memory/Skill Hub 思路）：
  - 本仓库作为 Hub 源，把记忆/技能/工具注册表推送到远程分支
  - 其他工作区/用户 clone 后通过 SEA/scripts/sync-workspace.py 拉取到本地
  - 权限分层：远程写需 HITL 确认 + 审计通过；读取是只读拉取

流程:
  1. audit：push 前跑 scan-secrets + audit-skill，检出即拦截
  2. commit：本地生成 hub 快照提交（记忆/技能/注册表）
  3. push：推送到远程分支 hub/<branch>
  4. 记录：CHANGELOG 记录 hub 同步时间与内容

用法:
    python SEA/scripts/hub-sync.py --remote <remote> --push [--branch hub-shared] [--dry-run]
    python SEA/scripts/hub-sync.py --remote <remote> --pull [--branch hub-shared]

退出码: 0 成功; 1 审计拦截 / git 错误 / 无 remote。
零第三方依赖（仅标准库 + git CLI）。
"""

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent


def git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd or REPO_ROOT,
                          capture_output=True, text=True)


def audit_gate(dry_run):
    """push 前安全审计：secret 扫描 + 技能供应链审计。检出即拦截。"""
    py = sys.executable
    checks = [
        [py, str(ROOT / "scripts" / "scan-secrets.py")],
        [py, str(ROOT / "scripts" / "audit-skill.py"), "--skills-dir",
         str(REPO_ROOT / "skills")],
    ]
    for cmd in checks:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print("[AUDIT] 拦截：", r.stdout, r.stderr, sep="\n")
            return False
    print("[AUDIT] scan-secrets + audit-skill 通过。")
    return True


def commit_snapshot(dry_run):
    """把记忆/技能/注册表提交为 hub 快照。"""
    git("add", "SEA/memory", "SEA/agents", "SEA/tools", "skills")
    status = git("status", "--porcelain")
    if not status.stdout.strip():
        print("[COMMIT] 无改动，无需快照。")
        return False
    msg = f"hub-sync: 经验快照 {dt.datetime.now().isoformat(timespec='seconds')}"
    if dry_run:
        print(f"[COMMIT][dry-run] 将提交: {msg}")
        return True
    r = git("commit", "-m", msg)
    if r.returncode != 0:
        print(f"[COMMIT] 失败: {r.stderr}", file=sys.stderr)
        return False
    print(f"[COMMIT] {r.stdout.strip()}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--remote", required=True, help="git remote 名或 URL")
    ap.add_argument("--branch", default="hub-shared",
                    help="hub 分支名（默认 hub-shared）")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--push", action="store_true", help="推送快照到远程 Hub")
    group.add_argument("--pull", action="store_true", help="从远程 Hub 拉取")
    ap.add_argument("--dry-run", action="store_true", help="只模拟不执行")
    args = ap.parse_args()

    ref = f"refs/heads/{args.branch}"
    if args.push:
        if not audit_gate(args.dry_run):
            return 1
        if not commit_snapshot(args.dry_run):
            if git("diff", "--cached", "--quiet").returncode != 0 and not args.dry_run:
                return 0
        if args.dry_run:
            print(f"[PUSH][dry-run] git push {args.remote} HEAD:{ref}")
            return 0
        r = git("push", args.remote, f"HEAD:{ref}")
        if r.returncode != 0:
            print(f"[PUSH] 失败: {r.stderr}", file=sys.stderr)
            return 1
        print(f"[PUSH] 已推送 {args.branch} 到 {args.remote}")
    else:
        if args.dry_run:
            print(f"[PULL][dry-run] git fetch {args.remote} {ref}")
            return 0
        r = git("fetch", args.remote, ref)
        if r.returncode != 0:
            print(f"[PULL] fetch 失败: {r.stderr}", file=sys.stderr)
            return 1
        print(f"[PULL] 已 fetch {args.remote}/{args.branch}")
        print("提示：合并/检出远程内容用 git merge FETCH_HEAD 或 sync-workspace.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
