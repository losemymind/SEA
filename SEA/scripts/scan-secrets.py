#!/usr/bin/env python3
"""scan-secrets.py — 入库前 PII / secret 扫描（§7.1 治理：PII 脱敏 + 版本审计前置）。

扫描 memory/ 与可选目录（--scan 可传多个路径），检出疑似 secret 或 PII：
  - API 密钥 / token（常见前缀 + 长随机串）
  - AWS / Azure / GCP 密钥格式
  - 私钥块（BEGIN ... PRIVATE KEY）
  - 邮箱地址、手机号（中国大陆 11 位）
  - 内嵌的 bearer token / password= 等赋值

检出项仅提示，不做自动修改（脱敏需人工确认），符合"不自动改数据"纪律。

用法:
    python SEA/scripts/scan-secrets.py [--scan <路径> ...]
    python SEA/scripts/scan-secrets.py --scan SEA/memory --scan skills

退出码: 0 未检出; 1 检出疑似 secret/PII 或路径不存在。
零第三方依赖（仅标准库）。
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCAN = ROOT / "memory"

# 键值型：assignment 后跟高熵串
KEYVALUE_RE = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|passwd|private[_-]?key)"
    r"\s*[=:]\s*['\"]?([A-Za-z0-9_\-]{16,})"
)
# 常见 token 前缀
PREFIX_RE = re.compile(
    r"\b(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|"
    r"xox[baprs]-[A-Za-z0-9\-]{20,}|Bearer\s+[A-Za-z0-9._\-]{20,}|"
    r"AKIA[0-9A-Z]{16})\b"
)
# 私钥块
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
# 云服务商密钥签名
CLOUD_RE = re.compile(
    r"(?i)(AKIA[0-9A-Z]{16}|azs\.[A-Za-z0-9\-_]{20,}|"
    r"AIza[0-9A-Za-z_\-]{30,}|sk-[A-Za-z0-9]{16,})"
)
# PII：邮箱
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
# PII：中国大陆手机号（11 位，1 开头）
CN_PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
# 示例/占位符，不算泄露（常见占位域名与假值）
IGNORE_PATTERNS = [
    re.compile(r"(?i)example\.(com|org|net)"),
    re.compile(r"(?i)your[_-]?key"),
    re.compile(r"(?i)<[^>]{0,40}(key|token|secret|password)[^>]{0,40}>"),
    re.compile(r"sk-<...>|xxx|placeholder", re.IGNORECASE),
]


def ignored(text: str):
    return any(p.search(text) for p in IGNORE_PATTERNS)


def scan_file(path: Path, findings):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        findings.append((str(path), f"读取失败: {e}"))
        return

    checks = [
        ("API key/token 赋值", KEYVALUE_RE),
        ("token 前缀", PREFIX_RE),
        ("私钥块", PRIVATE_KEY_RE),
        ("云服务商密钥签名", CLOUD_RE),
        ("邮箱（PII）", EMAIL_RE),
        ("手机号（PII）", CN_PHONE_RE),
    ]
    for label, rx in checks:
        for m in rx.finditer(text):
            # 整段上下文文本（单行切片）做占位符排除
            line_start = text.rfind("\n", 0, m.start()) + 1
            line_end = text.find("\n", m.end())
            if line_end == -1:
                line_end = len(text)
            context = text[line_start:line_end]
            if ignored(context):
                continue
            findings.append((str(path), f"{label} @{text[:m.start()].count(chr(10)) + 1}: {context.strip()[:120]}"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="append", default=None,
                    help="扫描路径（可多次）。默认只扫 SEA/memory/")
    args = ap.parse_args()

    targets = [Path(p) for p in (args.scan or [str(DEFAULT_SCAN)])]
    findings = []
    for t in targets:
        if not t.exists():
            findings.append((str(t), "路径不存在"))
            continue
        files = [t] if t.is_file() else sorted(p for p in t.rglob("*") if p.is_file())
        for f in files:
            scan_file(f, findings)

    if not findings:
        print("OK：未检出疑似 secret / PII。")
        return 0
    for path, detail in findings:
        print(f"[发现] {path}\n       {detail}")
    print(f"\n{len(findings)} 处疑似泄露，请人工确认并脱敏后重跑。", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
