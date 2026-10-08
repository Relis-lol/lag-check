"""Inspect ONLY tracked source files. Never scan or upload local session logs."""

import ipaddress
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent


def violations(name, data):
    issues = []
    path = pathlib.PurePosixPath(name)
    if any(
        p.lower() in {"sessions", "logs", "data", ".venv", "dist", "build", "artifacts"}
        for p in path.parts
    ):
        issues.append("runtime/build directory tracked")
    if (
        path.suffix.lower() in {".csv", ".log", ".pem", ".key", ".zip", ".exe"}
        or path.name in {"active.json", "latest.json", "verification.json"}
        or path.name.startswith(".env")
    ):
        issues.append("private/runtime file type tracked")
    text = data.decode("utf-8", errors="replace")
    if re.search(
        r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)",
        text,
    ):
        issues.append("possible access token / private key")
    if re.search(r"[A-Za-z]:[\\/]+Users[\\/]+(?!<|YOUR|example)[\w.-]+", text, re.I):
        issues.append("absolute personal Windows path")
    for literal in re.findall(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])", text):
        try:
            address = ipaddress.ip_address(literal)
        except ValueError:
            continue
        if str(address) not in {"0.0.0.0", "1.1.1.1", "8.8.8.8"}:
            issues.append("unexpected IP literal")
    return sorted(set(issues))


def main():
    files = (
        subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
        .decode()
        .split("\0")
    )
    findings = []
    for name in filter(None, files):
        path = ROOT / name
        if not path.is_file():
            continue
        for issue in violations(name, path.read_bytes()):
            findings.append(f"{name}: {issue}")
    if findings:
        raise SystemExit("\n".join(findings))
    print(
        f"Publication check passed: {len(list(filter(None, files)))} tracked files. No raw sessions or recognized secrets."
    )


if __name__ == "__main__":
    main()
