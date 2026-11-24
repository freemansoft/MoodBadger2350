"""The project skills in .claude/skills load: each SKILL.md starts with
front matter naming its folder and giving a description. (What they cite
is checked with the other docs, in test_docs.py.)"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKILLS = sorted(p.parent for p in (ROOT / ".claude" / "skills").glob("*/SKILL.md"))


@pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.name)
def test_skill_has_frontmatter_name_and_description(skill):
    text = (skill / "SKILL.md").read_text()
    assert text.startswith(f"---\nname: {skill.name}\ndescription: ")
