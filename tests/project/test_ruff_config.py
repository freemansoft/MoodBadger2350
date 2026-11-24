"""ruff.toml can extend only one of Pimoroni's two rule files. The app
runs on both badges, so the two must say the same thing: if a firmware
update makes them differ, this fails and someone decides which rules to
follow (see ruff.toml). (Adapted from freemansoft/dice-badgeware.)"""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

VENDOR_RULES = ["vendor/badger2350/ci/ruff.toml", "vendor/tufty2350/ci/ruff.toml"]


def rules(path):
    with open(ROOT / path, "rb") as f:
        return tomllib.load(f)


def test_badger_and_tufty_lint_rules_match():
    badger, tufty = (rules(p) for p in VENDOR_RULES)
    assert badger == tufty


def test_ruff_toml_extends_pimoronis_rules():
    assert rules("ruff.toml")["extend"] in VENDOR_RULES
