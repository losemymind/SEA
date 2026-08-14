#!/usr/bin/env python3
"""audit-skill.py — 技能供应链审计（§5.4：技能如软件包，入库前必查）。

对技能库（或指定技能目录）做静态审计，检出危险信号：
  - 读取敏感路径（~/.ssh、/etc、.aws 等）
  - 执行危险命令（rm -rf、curl|sh、wget|sh、base64 -d 管道执行、eval 动态执行）
  - 下载远程脚本（curl/wget/Invoke-WebRequest 取远程内容）
  - 写入 secret（把密钥写入文件/输出）
  - 污染他方（写 .opencode/skills、其他技能目录、memory/）

审计范围：每个技能目录的 SKILL.md、test-prompts.json 与附属脚本（*.py/*.sh/*.ps1/*.js）。
纯静态启发式；检出项需人工复核，不自动改文件。

用法:
    python SEA/scripts/audit-skill.py [--skills-dir <技能库根目录>] [--skill <技能名>]

退出码: 0 通过（无危险信号）; 1 检出危险信号。
零第三方依赖（仅标准库）。
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 敏感路径读取
SENSITIVE_PATH_RE = [
    re.compile(r"(?i)\.ssh|/etc/passwd|\.aws\b|/etc/shadow"),
    re.compile(r"(?i)appdata|%appdata%|$HOME|~\\\\"),
]
# 危险命令
DANGEROUS_CMD_RE = [
    re.compile(r"rm\s+(-[a-z]*f[a-z]*\s+)?-?.*(/|\.|~)"),
    re.compile(r"curl[^\n|]*\|\s*(ba)?sh"),
    re.compile(r"wget[^\n|]*\|\s*(ba)?sh"),
    re.compile(r"Invoke-Expression|iex\s*\("),
    re.compile(r"base64\s*-d\s*[^\n|]*\|"),
    re.compile(r"(?i)(eval|exec)\s*\(\s*(os\.system|subprocess)"),
]
# 远程脚本下载（在技能正文/脚本中出现远程 URL 拉取）
REMOTE_FETCH_RE = [
    re.compile(r"curl\s+-[a-zA-Z]*[oO]?\s+https?://"),
    re.compile(r"wget\s+-[a-zA-Z]*[oO]\s+https?://"),
    re.compile(r"Invoke-WebRequest.*-OutFile"),
]
# 写 secret / 导出环境变量含 token
SECRET_WRITE_RE = [
    re.compile(r"(?i)export\s+(API_KEY|TOKEN|SECRET|PASSWORD)\s*="),
    re.compile(r"set\s+(API_KEY|TOKEN|SECRET|PASSWORD)\s*="),
    re.compile(r"write.*(api[_-]?key|token|secret)", re.IGNORECASE),
]
# 污染他方：写入其他技能目录（非自身）或全局技能库，或覆盖 AGENTS.md。
# 仅当上下文含写操作动词（Copy/Write/Set/Add/Move/Install）时才判定，
# 纯路径说明（如安装文档引用）不构成污染。
POLLUTION_WRITE_VERBS = r"Copy-Item|Copy|Write|Set-Content|Out-File|Add-Content|Move-Item|Install"
POLLUTION_RE = [
    re.compile(
        r"(?i)(" + POLLUTION_WRITE_VERBS + r").{0,80}?"
        r"(\.opencode[/\\\\]skills[/\\\\](task-retrospective|skill-craft|agent-improvement|agent-craft|version-verify)[/\\\\]"
        r"|\.config[/\\\\]opencode[/\\\\]skills[/\\\\]"
        r"|\.claude[/\\\\]skills[/\\\\])"
    ),
    re.compile(r"(?i)Copy-Item.*AGENTS\.md|Copy-Item.*[\\\\/]AGENTS\.md"),
]

CHECKS = [
    ("敏感路径读取", SENSITIVE_PATH_RE),
    ("危险命令", DANGEROUS_CMD_RE),
    ("远程脚本下载", REMOTE_FETCH_RE),
    ("写入 secret", SECRET_WRITE_RE),
    ("污染他方技能/全局库", POLLUTION_RE),
]


def audit_text(text: str):
    findings = []
    for label, patterns in CHECKS:
        for rx in patterns:
            for m in rx.finditer(text):
                line_start = text.rfind("\n", 0, m.start()) + 1
                line_end = text.find("\n", m.end())
                if line_end == -1:
                    line_end = len(text)
                findings.append((label, text[line_start:line_end].strip()[:140]))
    return findings


def audit_dir(skill_dir: Path):
    files = [skill_dir / "SKILL.md", skill_dir / "test-prompts.json"]
    files += sorted(skill_dir.glob("*.py")) + sorted(skill_dir.glob("*.sh")) \
        + sorted(skill_dir.glob("*.ps1")) + sorted(skill_dir.glob("*.js"))
    out = []
    for f in files:
        if not f.exists():
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for label, snippet in audit_text(text):
            out.append((str(f.relative_to(skill_dir.parent)), label, snippet))
    return out


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
    ap.add_argument("--skill", type=str, default=None, help="只审计指定技能名")
    args = ap.parse_args()

    skills_dir = resolve_skills_dir(args.skills_dir)
    if not skills_dir.exists():
        print(f"[ERROR] 技能库目录不存在: {skills_dir}", file=sys.stderr)
        return 1

    targets = []
    if args.skill:
        d = skills_dir / args.skill
        if not d.is_dir():
            print(f"[ERROR] 技能不存在: {args.skill}", file=sys.stderr)
            return 1
        targets = [d]
    else:
        targets = [d for d in sorted(skills_dir.iterdir())
                   if d.is_dir() and not d.name.startswith("_")]

    all_findings = []
    for d in targets:
        findings = audit_dir(d)
        if findings:
            print(f"== {d.name} ==")
            for fpath, label, snippet in findings:
                print(f"  [{label}] {fpath}\n       {snippet}")
            all_findings.extend(findings)

    if all_findings:
        print(f"\n{len(all_findings)} 处危险信号，请人工复核。", file=sys.stderr)
        return 1
    print(f"OK：{len(targets)} 个技能供应链审计通过（{skills_dir}）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
