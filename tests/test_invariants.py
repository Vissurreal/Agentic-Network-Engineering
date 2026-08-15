#!/usr/bin/env python3
"""Strict-schema and adversarial network validation."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import SCRIPTS, Suite, make_fixtures, py, run  # noqa: E402

MUST_PASS = {"00-valid.yaml", "01-direct-valid.yaml"}


def main() -> int:
    suite = Suite("invariants")
    temp = Path(tempfile.mkdtemp())
    make_fixtures(temp)
    for fixture in sorted(temp.glob("*.yaml")):
        result = run(
            [
                py(),
                SCRIPTS / "validate_network.py",
                fixture,
                "--probe",
                temp / "probe-ok.json",
            ]
        )
        suite.check(
            fixture.name,
            result.returncode,
            0 if fixture.name in MUST_PASS else 1,
        )

    valid = temp / "00-valid.yaml"
    result = run(
        [
            py(),
            SCRIPTS / "validate_network.py",
            valid,
            "--probe",
            temp / "probe-unverified.json",
        ]
    )
    suite.check("unverified Codex model is rejected", result.returncode, 1)

    malformed = temp / "malformed.yaml"
    malformed.write_text("agents:\n  - id: a\n   bad indent\n", encoding="utf-8")
    result = run([py(), SCRIPTS / "validate_network.py", malformed])
    suite.check("malformed YAML exits 2", result.returncode, 2)

    result = run([py(), SCRIPTS / "validate_network.py", temp / "missing.yaml"])
    suite.check("missing YAML exits 2", result.returncode, 2)
    return suite.report()


if __name__ == "__main__":
    raise SystemExit(main())
