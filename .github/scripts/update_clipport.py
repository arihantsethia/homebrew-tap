#!/usr/bin/env python3
"""Prepare and apply a strictly versioned Clipport formula update."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

REPOSITORY = "arihantsethia/clipport"
API = f"https://api.github.com/repos/{REPOSITORY}"
TAG = r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
URL = re.compile(r'^  url "https://github\.com/arihantsethia/clipport/archive/refs/tags/(' + TAG + r')\.tar\.gz"$', re.M)
CHECKSUM = re.compile(r'^  sha256 "([0-9a-f]{64})"$', re.M)


def version(tag):
    match = re.fullmatch(TAG, tag)
    if not match:
        raise ValueError(f"Not a stable vMAJOR.MINOR.PATCH tag: {tag!r}")
    return tuple(map(int, match.groups()))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def api(path):
    request = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "clipport-homebrew-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def current_tag(formula):
    urls = list(URL.finditer(formula))
    if len(urls) != 1 or len(CHECKSUM.findall(formula)) != 1:
        raise ValueError("Expected exactly one stable Clipport URL and SHA-256")
    return urls[0].group(1)


def release_tag(release):
    if release.get("draft") or release.get("prerelease") or not release.get("published_at"):
        raise ValueError("Refusing an unpublished or prerelease release")
    tag = release["tag_name"]
    version(tag)
    return tag


def prepare(formula, fetch=api, download=None):
    release = fetch("/releases/latest")
    tag = release_tag(release)
    old_tag = current_tag(formula)
    if version(tag) <= version(old_tag):
        return None  # Never downgrade or replace the checksum of an existing version.
    commit = fetch(f"/commits/{tag}")["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid release commit SHA")
    if fetch(f"/compare/{commit}...main")["status"] not in {"ahead", "identical"}:
        raise ValueError("Release commit is not on main")
    url = f"https://github.com/{REPOSITORY}/archive/refs/tags/{tag}.tar.gz"
    if download is None:
        with urllib.request.urlopen(url, timeout=120) as response:
            sha = hashlib.file_digest(response, "sha256").hexdigest()
    else:
        sha = digest(download(url))
    if fetch(f"/commits/{tag}")["sha"] != commit:
        raise ValueError("Release tag moved while preparing the update")
    return {"tag": tag, "url": url, "sha256": sha, "commit": commit,
            "release_id": release["id"], "formula_sha256": digest(formula.encode())}


def render(formula, proposal):
    tag = proposal["tag"]
    if version(tag) <= version(current_tag(formula)):
        raise ValueError("Update must advance the stable version")
    expected_url = f"https://github.com/{REPOSITORY}/archive/refs/tags/{tag}.tar.gz"
    if proposal["url"] != expected_url or not re.fullmatch(r"[0-9a-f]{64}", proposal["sha256"]):
        raise ValueError("Invalid release URL or SHA-256")
    if digest(formula.encode()) != proposal["formula_sha256"]:
        raise ValueError("Formula changed since validation; rerun the updater")
    formula = URL.sub(lambda _: f'  url "{expected_url}"', formula)
    return CHECKSUM.sub(lambda _: f'  sha256 "{proposal["sha256"]}"', formula)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "apply", "verify"])
    parser.add_argument("--formula", type=Path, default=Path("Formula/clipport.rb"))
    parser.add_argument("--proposal", type=Path, required=True)
    args = parser.parse_args()
    formula = args.formula.read_text()
    if args.mode == "prepare":
        proposal = prepare(formula)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as output:
                output.write(f"changed={str(proposal is not None).lower()}\n")
                if proposal:
                    output.write(f'tag={proposal["tag"]}\ncommit={proposal["commit"]}\n')
        if proposal:
            args.proposal.write_text(json.dumps(proposal, indent=2) + "\n")
            print(f'Prepared {proposal["tag"]} ({proposal["commit"]})')
        else:
            print("Formula already covers the latest stable release")
    else:
        proposal = json.loads(args.proposal.read_text())
        updated = render(formula, proposal)
        if args.mode == "verify":
            # Recheck public metadata and archive in the isolated writer job.
            # Never execute upstream source with a write-enabled token.
            if prepare(formula) != proposal:
                raise ValueError("Release changed since validation; rerun the updater")
        args.formula.write_text(updated)


if __name__ == "__main__":
    main()
