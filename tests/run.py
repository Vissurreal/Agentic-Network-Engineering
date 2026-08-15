#!/usr/bin/env python3
"""Run every dependency-free test suite with ASCII-only console output."""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITES = [
    ("yaml compatibility", "test_yamlcompat.py"),
    ("plugin invocation", "test_invocation.py"),
    ("invariants", "test_invariants.py"),
    ("emitter", "test_emitter.py"),
    ("hooks", "test_hooks.py"),
    ("end to end", "test_end_to_end.py"),
]


def main() -> int:
    failed = []
    for label, script in SUITES:
        print(f"-- {label} " + "-" * max(0, 50 - len(label)))
        result = subprocess.run([sys.executable, str(HERE / script)])
        if result.returncode:
            failed.append(label)
        print()
    if failed:
        print("FAILURES: " + ", ".join(failed))
        return 1
    print("ALL SUITES PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
