"""The development tools are pinned, each in one place: Python tools in
requirements-dev.txt, prettier in .prettier-version (read by the
pre-commit hook and CI). Unpinned tools let a new release change what
the checks accept, or reformat files nobody touched."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".githooks" / "pre-commit"
CI = ROOT / ".github" / "workflows" / "ci.yml"
# Split so this file doesn't match itself.
HARD_CODED_PRETTIER = re.compile(rb"prettier@" + rb"\d")


def requirements():
    lines = (ROOT / "requirements-dev.txt").read_text().splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def test_every_dev_requirement_is_pinned():
    for line in requirements():
        assert re.fullmatch(r"[A-Za-z0-9_.-]+==[A-Za-z0-9_.+-]+", line), line


def test_dev_requirements_include_mpremote():
    # Dropping any other dev tool fails CI (which runs it) or a test (which
    # imports it); only the badge tools need mpremote.
    assert "mpremote" in {line.split("==")[0].lower() for line in requirements()}


def test_prettier_version_file_holds_one_version():
    assert re.fullmatch(r"\d+\.\d+\.\d+", (ROOT / ".prettier-version").read_text().strip())


def repo_files():
    """Tracked files plus new ones not yet added (but not ignored ones)."""
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                             cwd=ROOT, capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    return [ROOT / name for name in out.decode().split("\0") if name]


def test_only_prettier_version_names_the_prettier_version():
    offenders = [str(path.relative_to(ROOT)) for path in repo_files()
                 if path.is_file() and path.name != ".prettier-version"
                 and HARD_CODED_PRETTIER.search(path.read_bytes())]
    assert offenders == [], "use the version in .prettier-version instead"


def test_hook_and_ci_read_prettier_version():
    # The hook's comments name the file too, so look for the line that reads it.
    assert '<"$root/.prettier-version"' in HOOK.read_text()
    assert "prettier@$(cat .prettier-version)" in CI.read_text()


@pytest.mark.skipif(shutil.which("sh") is None, reason="no sh")
def test_hook_is_valid_posix_sh():
    subprocess.run(["sh", "-n", str(HOOK)], check=True)
