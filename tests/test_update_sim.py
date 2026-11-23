"""Tests for tools/update_sim.py, which pins and updates the simulator's
badgeware-wasm builds (sim/wasm/VERSION.json). gh and git are stubbed:
nothing here needs the network. (Adapted from freemansoft/dice-badgeware.)"""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import update_sim

ROOT = Path(__file__).resolve().parent.parent
MODELS = ("badger", "tufty")

RUNS = [
    {"databaseId": 1, "headSha": "a", "headBranch": "main", "workflowName": "build", "conclusion": "success", "createdAt": "2026-09-11T00:00:00Z"},
    {"databaseId": 2, "headSha": "b", "headBranch": "v3.1.0", "workflowName": "build", "conclusion": "success", "createdAt": "2026-09-24T00:00:00Z"},
    {"databaseId": 3, "headSha": "c", "headBranch": "main", "workflowName": "build", "conclusion": "failure", "createdAt": "2026-09-25T00:00:00Z"},
    {"databaseId": 4, "headSha": "d", "headBranch": "main", "workflowName": "build", "conclusion": "success", "createdAt": "2026-09-23T00:00:00Z"},
]
RELEASES = [
    {"tagName": "v5.0.0", "isPrerelease": False, "isDraft": True, "publishedAt": "2026-10-09T00:00:00Z"},
    {"tagName": "v4.0.0-ide.1", "isPrerelease": True, "isDraft": False, "publishedAt": "2026-10-05T00:00:00Z"},
    {"tagName": "v3.1.1", "isPrerelease": False, "isDraft": False, "publishedAt": "2026-09-23T00:00:00Z"},
    {"tagName": "v3.1.0", "isPrerelease": False, "isDraft": False, "publishedAt": "2026-09-14T00:00:00Z"},
]


def test_latest_build_run():
    assert update_sim.latest_build_run(RUNS)["databaseId"] == 4


def test_latest_build_run_none():
    assert update_sim.latest_build_run([]) is None


def test_latest_release_tag():
    assert update_sim.latest_release_tag(RELEASES) == "v3.1.1"


def test_artifact_names_match_the_committed_builds():
    for model in MODELS:
        assert update_sim.artifact_name(model) == f"badgeware-{model}2350-asyncify"
        for name in update_sim.BUILD_FILES:
            assert (ROOT / "sim" / "wasm" / model / name).is_file()


# --- the committed pin ------------------------------------------------------------

def committed_version():
    return json.loads((ROOT / "sim" / "wasm" / "VERSION.json").read_text())


def test_committed_version_pins_both_badges():
    version = committed_version()
    assert sorted(version["firmware"]) == list(MODELS)
    assert version["wasm"]["repo"] == update_sim.WASM_REPO


def test_source_md_agrees_with_version_json():
    # SOURCE.md is the human-readable record (with artifact ids and the
    # host contract); after an update both must name the same build.
    wasm = committed_version()["wasm"]
    source = (ROOT / "sim" / "wasm" / "SOURCE.md").read_text()
    assert f"`{wasm['commit']}`" in source
    assert f"`{wasm['run_id']}` ({wasm['date']})" in source
    assert "VERSION.json" in source and "tools.update_sim" in source


@pytest.mark.parametrize("model", MODELS)
def test_firmware_submodule_is_at_the_pinned_tag(model):
    tag = committed_version()["firmware"][model]
    result = subprocess.run(["git", "-C", str(ROOT / "vendor" / f"{model}2350"), "describe", "--tags", "--exact-match"],
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        pytest.skip("submodule missing or fetched without tags")
    assert result.stdout.strip() == tag


# --- check and update, against a temporary repo ------------------------------------

@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A temp repo root pinned to run 1 / v3.1.1, with gh and git stubbed."""
    for model in MODELS:
        build = tmp_path / "sim" / "wasm" / model
        build.mkdir(parents=True)
        (build / "micropython.mjs").write_text("old mjs")
        (build / "micropython.wasm").write_text("old wasm")
        (tmp_path / "vendor" / f"{model}2350").mkdir(parents=True)
    pin(tmp_path, 1)
    monkeypatch.setattr(update_sim, "ROOT", tmp_path)
    monkeypatch.setattr(update_sim, "gh_ready", lambda: True)
    monkeypatch.setattr(update_sim, "gh_json", lambda args: RUNS if args[0] == "run" else RELEASES)
    git_calls = []
    monkeypatch.setattr(update_sim, "git", git_calls.append)
    return SimpleNamespace(root=tmp_path, git_calls=git_calls)


def pin(root, run_id, firmware="v3.1.1"):
    version = {
        "wasm": {"repo": "pimoroni/badgeware-wasm", "commit": "x", "run_id": run_id, "date": "2026-09-11"},
        "firmware": {"badger": "v3.1.1", "tufty": firmware},
    }
    (root / "sim" / "wasm" / "VERSION.json").write_text(json.dumps(version))


def snapshot(root):
    wasm = root / "sim" / "wasm"
    return {p.relative_to(wasm).as_posix(): p.read_bytes() for p in sorted(wasm.rglob("*")) if p.is_file()}


def test_check_current_returns_0(repo):
    pin(repo.root, 4)
    assert update_sim.main(["--check"]) == 0


@pytest.mark.usefixtures("repo")
def test_check_newer_build_returns_1(capsys):
    assert update_sim.main(["--check"]) == 1
    out = capsys.readouterr().out
    assert "run 1" in out and "run 4" in out


def test_check_newer_firmware_returns_1(repo, capsys):
    pin(repo.root, 4, firmware="v3.1.0")
    assert update_sim.main(["--check"]) == 1
    out = capsys.readouterr().out
    assert "tufty firmware: pinned v3.1.0, latest v3.1.1" in out
    assert "badger firmware: pinned v3.1.1, latest v3.1.1" in out


def test_check_changes_nothing(repo, monkeypatch):
    def forbidden(args):
        raise AssertionError(f"gh called: {args}")

    before = snapshot(repo.root)
    monkeypatch.setattr(update_sim, "gh_run", forbidden)
    update_sim.main(["--check"])
    assert snapshot(repo.root) == before
    assert repo.git_calls == []


def test_without_gh_returns_2_and_changes_nothing(repo, monkeypatch):
    def forbidden(args):
        raise AssertionError(f"gh called: {args}")

    before = snapshot(repo.root)
    monkeypatch.setattr(update_sim, "gh_ready", lambda: False)
    monkeypatch.setattr(update_sim, "gh_json", forbidden)
    monkeypatch.setattr(update_sim, "gh_run", forbidden)
    assert update_sim.main([]) == 2
    assert snapshot(repo.root) == before
    assert repo.git_calls == []


def test_download_missing_files_changes_nothing(repo, monkeypatch):
    before = snapshot(repo.root)
    monkeypatch.setattr(update_sim, "gh_run", lambda _args: None)
    assert update_sim.main([]) == 1
    assert snapshot(repo.root) == before
    assert repo.git_calls == []


def test_update_replaces_both_builds_and_writes_version(repo, monkeypatch):
    downloads = []

    def download(args):
        downloads.append(args[:7])
        good_download(args)

    monkeypatch.setattr(update_sim, "gh_run", download)
    assert update_sim.main([]) == 0
    # the newest good run's Node build for each pinned model
    assert downloads == [
        ["run", "download", "4", "-R", "pimoroni/badgeware-wasm", "-n", f"badgeware-{model}2350-asyncify"]
        for model in MODELS
    ]
    files = snapshot(repo.root)
    for model in MODELS:
        assert files[f"{model}/micropython.mjs"] == b"new mjs"
        assert files[f"{model}/micropython.wasm"] == b"new wasm"
        assert ["-C", str(repo.root / "vendor" / f"{model}2350"), "checkout", "-q", "v3.1.1"] in repo.git_calls
    version = json.loads(files["VERSION.json"])
    assert version["wasm"]["run_id"] == 4 and version["wasm"]["commit"] == "d"
    assert version["wasm"]["date"] == "2026-09-23"
    assert version["firmware"] == {"badger": "v3.1.1", "tufty": "v3.1.1"}


def good_download(args):
    dest = Path(args[args.index("-D") + 1])
    (dest / "micropython.mjs").write_text("new mjs")
    (dest / "micropython.wasm").write_text("new wasm")


def failing_git(step):
    def git(args):
        if step in args:
            raise subprocess.CalledProcessError(1, ["git", *args])
    return git


@pytest.mark.parametrize("step", ["fetch", "rev-parse", "checkout"])
def test_git_failure_changes_nothing(repo, monkeypatch, step):
    before = snapshot(repo.root)
    monkeypatch.setattr(update_sim, "gh_run", good_download)
    monkeypatch.setattr(update_sim, "git", failing_git(step))
    assert update_sim.main([]) == 1
    assert snapshot(repo.root) == before


def test_download_error_changes_nothing(repo, monkeypatch):
    before = snapshot(repo.root)

    def expired(args):
        raise subprocess.CalledProcessError(1, ["gh", *args])

    monkeypatch.setattr(update_sim, "gh_run", expired)
    assert update_sim.main([]) == 1
    assert snapshot(repo.root) == before
    assert repo.git_calls == []
