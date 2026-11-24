"""The docs (README, CLAUDE.md, the app README, sim/wasm/SOURCE.md and the
skills) against the repo: commands people copy, paths and links they
follow, and the licence notice the mood images need."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DOCS = [ROOT / "README.md", ROOT / "CLAUDE.md", ROOT / "badger" / "mood_badger" / "README.md",
        ROOT / "sim" / "wasm" / "SOURCE.md", *sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md"))]


def test_readme_gives_a_mac_copy_command_that_skips_junk_files():
    text = (ROOT / "README.md").read_text()
    assert "rsync -rv --exclude __pycache__ --exclude '.*' badger/mood_badger/ /Volumes/" in text
    assert "diskutil eject" in text


def test_mood_images_carry_their_apache_licence():
    # The images are Google Material icons; Apache 2.0 needs its text shipped with them.
    licence = (ROOT / "badger" / "mood_badger" / "assets" / "LICENSE").read_text()
    assert "Apache License" in licence and "Version 2.0, January 2004" in licence
    for path in ("README.md", "LICENSE", "badger/mood_badger/README.md"):
        text = (ROOT / path).read_text()
        assert "Material" in text and "Apache License 2.0" in text, path
        assert "not cleared for redistribution" not in text and "remain his" not in text, path


def _slug(heading):
    # GitHub's heading anchors: lower case, punctuation dropped, spaces to hyphens.
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def test_readme_internal_links_resolve():
    text = (ROOT / "README.md").read_text()
    anchors = {_slug(h) for h in re.findall(r"^#+ (.+)$", text, re.MULTILINE)}
    links = set(re.findall(r"\]\(#([\w-]+)\)", text))
    assert links and links <= anchors, links - anchors


def test_docs_cite_vendor_paths_that_exist():
    # The firmware source is the evidence for how the badges behave; a
    # submodule bump can move or drop a cited file.
    cited = {p.rstrip(".") for doc in DOCS
             for p in re.findall(r"vendor/(?:badger2350|tufty2350)/[\w./-]+", doc.read_text())}
    assert cited
    assert sorted(p for p in cited if not (ROOT / p).exists()) == []


def test_docs_cite_files_and_tools_that_exist():
    # Files and `python3 -m tools.<name>` commands the docs tell people to
    # read or run; a rename or a moved test file must take the docs along.
    files, modules = set(), set()
    for doc in DOCS:
        text = doc.read_text()
        files |= set(re.findall(r"\b(?:tests|tools|sim|kiosk|badger)/[\w/.-]*\.(?:py|mjs|html|json|md)\b", text))
        modules |= set(re.findall(r"-m tools\.(\w+)", text))
    assert files and modules
    assert sorted(p for p in files if not (ROOT / p).is_file()) == []
    assert sorted(m for m in modules if not (ROOT / "tools" / (m + ".py")).is_file()) == []


def test_docs_call_pimoroni_launcher_the_menu():
    # One word for one thing: "menu", never "app list".
    for path in DOCS:
        assert "app list" not in path.read_text().lower(), path
