#!/usr/bin/env python3
"""The fallback parser must agree with PyYAML on every fixture, or the two code
paths diverge and the plugin behaves differently depending on what happens to be
installed."""
import subprocess, sys, tempfile, pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import _yamlcompat as yc

assert yc._restricted_load("value: 'the user''s intent'\n") == {
    "value": "the user's intent"
}, "fallback must decode doubled apostrophes in single-quoted YAML"

try:
    import yaml
except ImportError:
    print("PyYAML absent; cannot compare. Skipping.")
    sys.exit(0)

tmp = pathlib.Path(tempfile.mkdtemp())
subprocess.run([sys.executable, str(HERE / "make_fixtures.py")], cwd=tmp, check=True,
               stdout=subprocess.DEVNULL)

targets = sorted(tmp.glob("*.yaml"))
targets += [HERE.parent / "assets" / "templates" / "network.yaml.template"]

fails = 0
for f in targets:
    text = f.read_text(encoding="utf-8")
    expected = yaml.safe_load(text)
    try:
        got = yc._restricted_load(text)
    except yc.RestrictedYAMLError as e:
        print(f"  FAIL {f.name}: fallback refused: {e}")
        fails += 1
        continue
    if got == expected:
        print(f"  ok   {f.name}")
    else:
        print(f"  FAIL {f.name}: parsers disagree")
        for k in sorted(set(list(expected or {}) + list(got or {}))):
            if (expected or {}).get(k) != (got or {}).get(k):
                print(f"        {k}:\n          pyyaml={(expected or {}).get(k)!r}\n          fallback={(got or {}).get(k)!r}")
        fails += 1

print(f"\n{len(targets)-fails} passed, {fails} failed")
sys.exit(1 if fails else 0)
