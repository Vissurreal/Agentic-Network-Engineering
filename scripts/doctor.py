#!/usr/bin/env python3
"""Report installed, authenticated, transport-ready, and model-ready states."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verify-codex-model",
        metavar="MODEL",
        help="perform the optional bounded live model check",
    )
    args = parser.parse_args()
    probe = Path(__file__).resolve().with_name("probe_environment.py")
    command = [sys.executable, str(probe), str(Path.cwd())]
    if args.verify_codex_model:
        command.extend(["--verify-codex-model", args.verify_codex_model])
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode
    data = json.loads(result.stdout)
    claude = data["claude"]
    codex = data["codex"]
    print("agentic-engineering readiness")
    print(f"  Python: {data['python_version']} ({data['python_command']})")
    print(
        "  Claude: "
        f"installed={claude['installed']} authenticated={claude['authenticated']} "
        f"version={claude['version'] or 'unknown'}"
    )
    print(
        "  Codex: "
        f"installed={codex['installed']} authenticated={codex['authenticated']} "
        f"mcp={codex['mcp_available']} model_access={codex['model_access']}"
    )
    if codex["model_access"] == "unverified":
        print(
            "  Cross-vendor roles remain disabled until a model is verified. "
            "Run doctor.py --verify-codex-model <model> if a bounded live call is acceptable."
        )
    hard_failure = not claude["installed"] or sys.version_info < (3, 9)
    return 1 if hard_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
