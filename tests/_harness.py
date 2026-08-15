"""Shared test scaffolding. Kept dependency-free so the suite runs anywhere."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
TESTS = ROOT / "tests"


class Suite:
    def __init__(self, name: str) -> None:
        self.name = name
        self.passed = 0
        self.failed = 0

    def check(self, label: str, got, want) -> None:
        if got == want:
            print(f"  ok   {label}")
            self.passed += 1
        else:
            print(f"  FAIL {label} (want {want!r}, got {got!r})")
            self.failed += 1

    def ok(self, label: str, condition: bool) -> None:
        self.check(label, bool(condition), True)

    def report(self) -> int:
        print(f"\n{self.passed} passed, {self.failed} failed")
        return 1 if self.failed else 0


def run(cmd: list[str], cwd: Path | None = None, env: dict | None = None,
        stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(c) for c in cmd], cwd=cwd, capture_output=True, text=True,
        env=env, input=stdin, timeout=120,
    )


def py() -> str:
    return sys.executable


def make_fixtures(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    r = run([py(), TESTS / "make_fixtures.py"], cwd=dest)
    if r.returncode != 0:
        raise RuntimeError(f"fixture generation failed:\n{r.stderr}")
