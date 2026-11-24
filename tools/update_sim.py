"""Check for, and pull, newer simulator builds and firmware from Pimoroni.

The simulator (sim/) runs Pimoroni's WebAssembly MicroPython builds from
pimoroni/badgeware-wasm (one for the Badger, one for the Tufty) with the
firmware Python from the vendor/badger2350 and vendor/tufty2350
submodules. badgeware-wasm publishes the Node-compatible "asyncify"
builds only as CI artifacts, which GitHub deletes after 90 days, so this
tool downloads them and the repo commits them. sim/wasm/VERSION.json
records what is in use; sim/wasm/SOURCE.md says the same for people,
with the artifact ids and the host contract.

    python3 -m tools.update_sim --check     # pinned vs latest; exit 1 if newer
    python3 -m tools.update_sim             # download newest, move submodule(s)
    python3 -m tools.update_sim --run 35841227054 --firmware-tag v3.1.1

Needs the GitHub CLI, logged in (gh auth login), and the network.
Standard library only. After updating: bring sim/wasm/SOURCE.md up to
date (tests/tools/test_update_sim.py checks it agrees with VERSION.json), run
.venv/bin/pytest, then commit sim/wasm and vendor/.

(Adapted from freemansoft/dice-badgeware.)
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WASM_REPO = "pimoroni/badgeware-wasm"
RUN_FIELDS = "databaseId,headSha,headBranch,workflowName,conclusion,createdAt"
RELEASE_FIELDS = "tagName,isPrerelease,isDraft,publishedAt"
BUILD_FILES = ("micropython.mjs", "micropython.wasm")


# -- thin wrappers, replaced in tests -----------------------------------------

def gh_ready():
    if shutil.which("gh") is None:
        return False
    return subprocess.run(["gh", "auth", "status"], check=False, capture_output=True).returncode == 0


def gh_json(args):
    out = subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def gh_run(args):
    subprocess.run(["gh", *args], check=True)


def git(args):
    subprocess.run(["git", *args], check=True)


# -- choosing versions ----------------------------------------------------------

def latest_build_run(runs):
    """Newest successful 'build' workflow run on main, or None."""
    good = [
        r for r in runs
        if r.get("workflowName") == "build" and r.get("headBranch") == "main" and r.get("conclusion") == "success"
    ]
    return max(good, key=lambda r: r["createdAt"]) if good else None


def latest_release_tag(releases):
    """Newest published, non-prerelease, non-draft release tag, or None."""
    good = [r for r in releases if not r.get("isPrerelease") and not r.get("isDraft")]
    return max(good, key=lambda r: r["publishedAt"])["tagName"] if good else None


def artifact_name(model):
    return f"badgeware-{model}2350-asyncify"


def firmware_repo(model):
    return f"pimoroni/{model}2350"


# -- files ----------------------------------------------------------------------

def wasm_dir():
    return ROOT / "sim" / "wasm"


def read_version():
    path = wasm_dir() / "VERSION.json"
    return json.loads(path.read_text()) if path.exists() else None


def write_version(run, tags):
    version = {
        "wasm": {
            "repo": WASM_REPO,
            "commit": run["headSha"],
            "run_id": run["databaseId"],
            "date": run["createdAt"][:10],
        },
        "firmware": dict(sorted(tags.items())),
    }
    (wasm_dir() / "VERSION.json").write_text(json.dumps(version, indent=2) + "\n")


# -- commands -------------------------------------------------------------------

def find_latest(models, run_id=None, firmware_tag=None):
    if run_id is not None:
        run = gh_json(["run", "view", str(run_id), "-R", WASM_REPO, "--json", RUN_FIELDS])
    else:
        run = latest_build_run(gh_json(["run", "list", "-R", WASM_REPO, "--json", RUN_FIELDS, "--limit", "30"]))
    tags = {}
    for model in models:
        tags[model] = firmware_tag or latest_release_tag(
            gh_json(["release", "list", "-R", firmware_repo(model), "--json", RELEASE_FIELDS])
        )
    return run, tags


def check(models, pinned):
    run, tags = find_latest(models)
    newer = False
    pinned_run = pinned["wasm"]["run_id"] if pinned else None
    latest_run = run["databaseId"] if run else None
    print("wasm: pinned run {}, latest run {} ({})".format(
        pinned_run, latest_run, run["createdAt"][:10] if run else "none found"))
    newer |= latest_run is not None and latest_run != pinned_run
    for model in models:
        pinned_tag = pinned["firmware"].get(model) if pinned else None
        print(f"{model} firmware: pinned {pinned_tag}, latest {tags[model]}")
        newer |= tags[model] is not None and tags[model] != pinned_tag
    print("updates available" if newer else "up to date")
    return 1 if newer else 0


def download_builds(run, models, tmp):
    """Download each model's build into tmp; {model: dir}, or None if a
    build is missing a file. Raises CalledProcessError if gh fails."""
    downloads = {}
    for model in models:
        dest = tmp / model
        dest.mkdir()
        gh_run(["run", "download", str(run["databaseId"]), "-R", WASM_REPO, "-n", artifact_name(model), "-D", str(dest)])
        missing = [name for name in BUILD_FILES if not (dest / name).is_file()]
        if missing:
            print("{} from run {} is missing {}; nothing changed".format(
                artifact_name(model), run["databaseId"], ", ".join(missing)))
            return None
        downloads[model] = dest
    return downloads


def update(models, run_id, firmware_tag):
    for model in models:
        submodule = ROOT / "vendor" / f"{model}2350"
        if not submodule.exists():
            print(f"missing firmware submodule; add it first:\n  git submodule add https://github.com/{firmware_repo(model)} vendor/{model}2350")
            return 1

    run, tags = find_latest(models, run_id, firmware_tag)
    if run is None or None in tags.values():
        print("could not find a successful build run or a firmware release")
        return 1

    # Everything that can fail happens before anything in the repo changes:
    # downloads, fetching tags, resolving them, and the submodule checkouts
    # (which can fail on local changes). Only then are the builds swapped
    # in and VERSION.json written.
    with tempfile.TemporaryDirectory() as tmp:
        try:
            downloads = download_builds(run, models, Path(tmp))
            if downloads is None:
                return 1
            for model, tag in tags.items():
                submodule = str(ROOT / "vendor" / f"{model}2350")
                git(["-C", submodule, "fetch", "--tags", "-q"])
                git(["-C", submodule, "rev-parse", "-q", "--verify", tag + "^{commit}"])
            for model, tag in tags.items():
                git(["-C", str(ROOT / "vendor" / f"{model}2350"), "checkout", "-q", tag])
        except subprocess.CalledProcessError as e:
            print("failed: {}; sim/wasm and VERSION.json are unchanged".format(" ".join(map(str, e.cmd))))
            print("if a submodule moved, `git submodule update` puts it back")
            return 1

        for model, dest in downloads.items():
            target = wasm_dir() / model
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True)
            for name in BUILD_FILES:
                shutil.copy2(dest / name, target / name)

    write_version(run, tags)
    print("simulator: badgeware-wasm run {} ({}), firmware {}".format(
        run["databaseId"], run["headSha"][:7], ", ".join(f"{m} {t}" for m, t in sorted(tags.items()))))

    stage = ROOT / "sim" / "stage.py"
    if stage.exists():
        subprocess.run([sys.executable, str(stage)], check=True)
    print("next: update sim/wasm/SOURCE.md (commit, run, artifact ids; recheck the host contract),\n"
          "run .venv/bin/pytest, then commit sim/wasm and vendor/")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="compare pinned and latest versions only")
    parser.add_argument("--run", type=int, help="badgeware-wasm workflow run id to use instead of the latest")
    parser.add_argument("--firmware-tag", help="firmware release tag to use instead of the latest")
    parser.add_argument("--models", help="comma-separated badge models (default: those pinned, or badger,tufty)")
    args = parser.parse_args(argv)

    if not gh_ready():
        print("the GitHub CLI (gh) is missing or not logged in: install it, then run `gh auth login`")
        return 2

    pinned = read_version()
    if args.models:
        models = args.models.split(",")
    elif pinned:
        models = sorted(pinned["firmware"])
    else:
        models = ["badger", "tufty"]

    if args.check:
        return check(models, pinned)
    return update(models, args.run, args.firmware_tag)


if __name__ == "__main__":
    sys.exit(main())
