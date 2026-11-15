"""The badgeware-platforms skill: its frontmatter, and that every firmware
file it cites as evidence exists in the pinned submodules."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "badgeware-platforms" / "SKILL.md"


def test_skill_has_frontmatter_name_and_description():
    text = SKILL.read_text()
    assert text.startswith("---\nname: badgeware-platforms\ndescription: ")


def test_every_vendor_path_cited_in_the_skill_exists():
    cited = set(re.findall(r"vendor/(?:badger2350|tufty2350)/[\w./-]+", SKILL.read_text()))
    assert cited, "the skill must cite firmware source"
    missing = [p for p in sorted(cited) if not (ROOT / p.rstrip(".")).exists()]
    assert missing == []


def test_tufty_submodule_is_pinned_to_v3_1_1():
    assert (ROOT / "vendor" / "tufty2350" / "firmware" / "main.py").exists()
    assert "tufty2350" in (ROOT / ".gitmodules").read_text()


def test_other_skills_and_claude_md_point_to_it():
    for path in (ROOT / "CLAUDE.md",
                 ROOT / ".claude/skills/badge-deploy/SKILL.md",
                 ROOT / ".claude/skills/badge-firmware/SKILL.md"):
        assert "badgeware-platforms" in path.read_text(), path


# --- badge-verify: the test and verification process ------------------------

VERIFY = ROOT / ".claude" / "skills" / "badge-verify" / "SKILL.md"


def test_verify_skill_has_frontmatter():
    assert VERIFY.read_text().startswith("---\nname: badge-verify\ndescription: ")


def test_verify_skill_commands_and_files_exist():
    text = VERIFY.read_text()
    modules = set(re.findall(r"python3 -m tools\.(\w+)", text))
    assert modules >= {"badge_info", "install", "badge_check"}
    assert all((ROOT / "tools" / (m + ".py")).exists() for m in modules)
    for path in ("tests/fake_badgeware.py", "tests/test_sim.py", "sim/stage.py",
                 "sim/run_headless.mjs", "vendor/badger2350/ci/ruff.toml"):
        assert path in text and (ROOT / path).exists(), path


def test_verify_skill_is_pointed_to_from_the_docs():
    for path in (ROOT / "CLAUDE.md", ROOT / "README.md"):
        assert "badge-verify" in path.read_text(), path
    assert "tools.badge_check" in (ROOT / "README.md").read_text()
