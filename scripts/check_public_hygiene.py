from __future__ import annotations

import argparse
import re
from pathlib import Path

TEXT_SUFFIXES = {
    "", ".cfg", ".conf", ".ini", ".json", ".md", ".py", ".toml", ".txt",
    ".xml", ".yaml", ".yml",
}
SKIP_DIRS = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv", "__pycache__"}

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("jwt_or_ha_token", re.compile(
        r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\b"
    )),
    ("credential_url", re.compile(r"https?://[^/\s:@]+:[^@\s/]+@")),
    ("private_ipv4_10", re.compile(r"(?<![\d.])10(?:\.\d{1,3}){3}(?![\d.])")),
    ("private_ipv4_192", re.compile(r"(?<![\d.])192\.168(?:\.\d{1,3}){2}(?![\d.])")),
    ("private_ipv4_172", re.compile(
        r"(?<![\d.])172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}(?![\d.])"
    )),
    ("internal_hostname", re.compile(
        r"\b[A-Za-z0-9._-]+\.(?:internal|corp|lan|local)\b", re.IGNORECASE
    )),
    ("sensitive_header", re.compile(
        r"(?im)^\s*(?:authorization|cookie|set-cookie)\s*:\s*\S+"
    )),
    ("credential_query", re.compile(
        r"(?i)[?&](?:token|api[_-]?key|password|passwd|secret)=[^&\s]+"
    )),
)

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
ALLOWED_EMAIL_DOMAINS = {"example.com", "example.org", "example.net", "users.noreply.github.com"}


def scan(root: Path) -> list[str]:
    findings: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = path.relative_to(root)
        for name, pattern in PATTERNS:
            if pattern.search(text):
                findings.append(f"{rel}: {name}")
        for email in EMAIL_RE.findall(text):
            if email.rsplit("@", 1)[1].lower() not in ALLOWED_EMAIL_DOMAINS:
                findings.append(f"{rel}: personal_email:{email}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", type=Path, nargs="+", help="Directories to scan")
    args = parser.parse_args()
    findings: list[str] = []
    for root in args.roots:
        if not root.is_dir():
            parser.error(f"scan root is not a directory: {root}")
        findings.extend(f"{root}/{item}" for item in scan(root))
    if findings:
        print("Public hygiene gate failed")
        for item in findings:
            print(f"- {item}")
        return 1
    print("Public hygiene gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

