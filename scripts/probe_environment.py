#!/usr/bin/env python3
"""Probe runtime capabilities without inferring authentication from config files.

Model access is deliberately distinct from installation, authentication, and
MCP transport readiness.  Codex model access is marked unverified unless the
caller explicitly requests a bounded live check with --verify-codex-model.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any


LANGUAGE_SUFFIXES = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".kt": "kotlin",
    ".swift": "swift",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
    ".md": "markdown",
}

IGNORED_DIRS = {
    ".git",
    ".next",
    "node_modules",
    "dist",
    "build",
    "target",
    "__pycache__",
    ".venv",
    "venv",
}


def run(args: list[str], cwd: Path, timeout: int = 10) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return None


def version_of(command: str, cwd: Path) -> str | None:
    result = run([command, "--version"], cwd)
    if result and result.returncode == 0:
        return (result.stdout or result.stderr).strip() or None
    return None


def claude_status(cwd: Path) -> dict[str, Any]:
    command = shutil.which("claude")
    if not command:
        return {
            "installed": False,
            "authenticated": False,
            "version": None,
            "models": [],
        }
    auth = run([command, "auth", "status"], cwd)
    authenticated = False
    if auth and auth.returncode == 0:
        try:
            authenticated = bool(json.loads(auth.stdout).get("loggedIn"))
        except (json.JSONDecodeError, AttributeError):
            authenticated = "logged" in (auth.stdout + auth.stderr).lower()
    return {
        "installed": True,
        "authenticated": authenticated,
        "version": version_of(command, cwd),
        # These are current Claude Code aliases, not organization allowlist
        # discovery. Authentication and full IDs are still validated at smoke.
        "models": ["haiku", "sonnet", "opus", "fable", "inherit"],
    }


def codex_mcp_tools(command: str, cwd: Path) -> list[str]:
    """Initialize codex mcp-server and return its advertised tool names."""
    try:
        process = subprocess.Popen(
            [command, "mcp-server"],
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except OSError:
        return []
    lines: list[str] = []

    def reader() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            lines.append(line)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    try:
        assert process.stdin is not None
        messages = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "agentic-probe", "version": "2"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ]
        for message in messages:
            process.stdin.write(json.dumps(message) + "\n")
            process.stdin.flush()
            time.sleep(0.1)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            for line in list(lines):
                try:
                    response = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if response.get("id") == 2:
                    tools = ((response.get("result") or {}).get("tools") or [])
                    return sorted(
                        tool.get("name")
                        for tool in tools
                        if isinstance(tool, dict) and isinstance(tool.get("name"), str)
                    )
            time.sleep(0.05)
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
    return []


def verify_codex_model(command: str, model: str, cwd: Path) -> bool:
    result = run(
        [
            command,
            "exec",
            "--ephemeral",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--ask-for-approval",
            "never",
            "--model",
            model,
            "Return exactly READY. Do not use tools.",
        ],
        cwd,
        timeout=90,
    )
    return bool(result and result.returncode == 0 and "READY" in result.stdout)


def codex_status(cwd: Path, verify_model: str | None) -> dict[str, Any]:
    command = shutil.which("codex")
    if not command:
        return {
            "installed": False,
            "authenticated": False,
            "version": None,
            "mcp_available": False,
            "mcp_tools": [],
            "model_access": "unavailable",
            "models": [],
        }
    auth = run([command, "login", "status"], cwd)
    authenticated = bool(
        auth
        and auth.returncode == 0
        and "logged in" in (auth.stdout + auth.stderr).lower()
    )
    tools = codex_mcp_tools(command, cwd) if authenticated else []
    verified = bool(
        verify_model
        and authenticated
        and {"codex", "codex-reply"}.issubset(set(tools))
        and verify_codex_model(command, verify_model, cwd)
    )
    return {
        "installed": True,
        "authenticated": authenticated,
        "version": version_of(command, cwd),
        "mcp_available": {"codex", "codex-reply"}.issubset(set(tools)),
        "mcp_tools": tools,
        "model_access": "verified" if verified else ("unverified" if authenticated else "unavailable"),
        "models": [verify_model] if verified and verify_model else [],
    }


def walk_project(root: Path) -> tuple[list[Path], int]:
    files: list[Path] = []
    total_bytes = 0
    for current, dirs, names in os.walk(root):
        dirs[:] = [name for name in dirs if name not in IGNORED_DIRS]
        base = Path(current)
        for name in names:
            path = base / name
            try:
                size = path.stat().st_size
            except OSError:
                continue
            files.append(path)
            total_bytes += size
    return files, total_bytes


def detect_test_command(root: Path) -> str | None:
    candidates = [
        ("package.json", "npm test"),
        ("pyproject.toml", "python -m pytest"),
        ("pytest.ini", "python -m pytest"),
        ("Cargo.toml", "cargo test"),
        ("go.mod", "go test ./..."),
        ("pom.xml", "mvn test"),
        ("build.gradle", "gradle test"),
    ]
    for filename, command in candidates:
        if (root / filename).is_file():
            return command
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument(
        "--verify-codex-model",
        metavar="MODEL",
        help="perform a bounded live model call; omitted by default",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        sys.stderr.write(f"not a directory: {root}\n")
        return 2

    files, total_bytes = walk_project(root)
    language_counts: dict[str, int] = {}
    for path in files:
        language = LANGUAGE_SUFFIXES.get(path.suffix.lower())
        if language:
            language_counts[language] = language_counts.get(language, 0) + 1
    languages = [
        language
        for language, _ in sorted(language_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    git_result = run(["git", "rev-parse", "--is-inside-work-tree"], root) if shutil.which("git") else None
    git = bool(git_result and git_result.returncode == 0)
    claude = claude_status(root)
    codex = codex_status(root, args.verify_codex_model)

    # Retrieval breadth is an input signal, not a topology decision.  File
    # count alone is deliberately insufficient.
    relevant_files = sum(1 for path in files if path.suffix.lower() in LANGUAGE_SUFFIXES)
    large_files = sum(
        1
        for path in files
        if path.suffix.lower() in LANGUAGE_SUFFIXES
        and path.stat().st_size > 100_000
    )
    search_breadth = (
        "broad"
        if total_bytes > 5_000_000 or relevant_files > 150 or large_files > 10
        else "bounded"
    )

    output = {
        "schema_version": 2,
        "root": str(root),
        "platform": platform.system().lower(),
        "python_command": Path(sys.executable).name,
        "python_version": platform.python_version(),
        "git": git,
        "test_command": detect_test_command(root),
        "languages": languages,
        "project_files": len(files),
        "relevant_files": relevant_files,
        "project_bytes": total_bytes,
        "large_relevant_files": large_files,
        "search_breadth": search_breadth,
        "existing": {
            "claude_md": (root / "CLAUDE.md").exists(),
            "agents_md": (root / "AGENTS.md").exists(),
            "network_yaml": (root / ".agentic" / "network.yaml").exists(),
        },
        "claude": claude,
        "codex": codex,
        # Flat compatibility fields used by the strict validator's --probe path.
        "claude_models": claude["models"],
        "codex_installed": codex["installed"],
        "codex_authenticated": codex["authenticated"],
        "codex_mcp_available": codex["mcp_available"],
        "codex_mcp_tools": codex["mcp_tools"],
        "codex_model_access": codex["model_access"],
        "codex_models": codex["models"],
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
