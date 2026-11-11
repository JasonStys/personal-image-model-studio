"""Jason Stys: exact-source draft-only uploads and complete portable verification.
# Index: declarations module.version@L41, module.api@L50, module.successful_source_run@L64, module.source_ready@L100, module.security_ready@L135, module.accepted_build@L183, module.draft_ready@L200, module.release_for_version@L213, module.load_draft@L228, module.prepare_draft@L240, module.assets_ready@L267, module.main@L295; variables value@L43, endpoint@L50, sarif@L50, data@L64, source@L64, workflow@L64, rows@L70, run@L75, source@L100, workflow@L106, data@L107, current@L111, row@L116, raw@L118, run@L129, alerts@L135, analyses@L135, source@L135, expected@L142, current@L143, row@L144, category@L152, name@L155, row@L176, product_version@L183, report@L183, source@L183, product_version@L200, release@L200, source@L200, product_version@L213, rows@L213, row@L218, matches@L219, row@L219, row@L223, product_version@L228, source@L228, listed@L230, release@L232, product_version@L240, source@L240, listed@L243, notes@L245, payload@L250, temporary@L258, path@L259, complete@L267, product_version@L267, release@L267, expected@L269, machine@L270, system@L270, assets@L272, result@L274, asset@L275, name@L276, parser@L297, args@L299, source@L300, product_version@L308, release@L315, attached@L316, machine@L318, system@L318, names@L319, report@L320, files@L324, name@L324, file@L325, binary@L341, manifest@L342, file@L348, fresh@L366, actual@L368. Purposes/parameters: docs/code-map.json.

Called only by the trusted main-branch release workflow. Never overwrites an
existing asset, accepts a published release, or logs token/environment values.
"""

import argparse
import json
import os
import platform
import re
import tempfile
import tomllib
from pathlib import Path

if __package__:
    from .native_distribution import (
        MAX_DOWNLOAD,
        REPO,
        ROOT,
        command,
        digest,
        names_for,
        read_manifest,
        require,
    )
else:
    from native_distribution import (
        MAX_DOWNLOAD,
        REPO,
        ROOT,
        command,
        digest,
        names_for,
        read_manifest,
        require,
    )


def version():
    """Read data-only product metadata without importing or executing the service."""
    value = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    require(bool(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value)), "Invalid release version")
    return value


def api(endpoint, *, sarif=False):
    """Read only fixed repository metadata; writes use explicit gh subcommands below."""
    return json.loads(
        command(
            [
                "gh",
                "api",
                f"repos/{REPO}/{endpoint}",
                *(["-H", "Accept: application/sarif+json"] if sarif else []),
            ]
        )
    )


def successful_source_run(data, source, workflow):
    """Require returned identity/status as well as server-side query filters."""
    require(
        isinstance(data, dict) and isinstance(data.get("workflow_runs"), list),
        "Malformed source workflow response",
    )
    rows = data["workflow_runs"]
    require(
        len(rows) == 1 and data.get("total_count") == 1,
        "Exactly one complete main-push run is required",
    )
    run = rows[0]
    require(
        type(run.get("id")) is int and 0 < run["id"] < 2**63, "Invalid source workflow identity"
    )
    require(
        run.get("head_sha") == source
        and run.get("head_branch") == "main"
        and run.get("event") == "push",
        "Source run does not match the requested main commit",
    )
    require(
        run.get("path")
        in {f".github/workflows/{workflow}", f".github/workflows/{workflow}@refs/heads/main"},
        "Wrong validation workflow",
    )
    require(
        run.get("html_url") == f"https://github.com/{REPO}/actions/runs/{run['id']}",
        "Foreign source run URL",
    )
    require(
        run.get("status") == "completed" and run.get("conclusion") == "success",
        "Source validation must complete successfully",
    )


def source_ready(source):
    """Require original/source/new native gates plus processed security results at exact current main."""
    require(
        api("git/ref/heads/main")["object"]["sha"] == source,
        "Main moved during release preparation",
    )
    for workflow in ("validate.yml", "native-validation.yml", "codeql.yml"):
        data = api(
            f"actions/workflows/{workflow}/runs?branch=main&event=push&head_sha={source}&per_page=100"
        )
        successful_source_run(data, source, workflow)
    current = security_ready(
        api("code-scanning/analyses?ref=refs/heads/main&tool_name=CodeQL&per_page=100"),
        api("code-scanning/alerts?ref=refs/heads/main&state=open&per_page=1"),
        source,
    )
    for row in current:
        require(type(row.get("id")) is int and row["id"] > 0, "Processed analysis ID is required")
        raw = api("code-scanning/analyses/" + str(row["id"]), sarif=True)
        require(
            raw.get("version") == "2.1.0"
            and isinstance(raw.get("runs"), list)
            and bool(raw["runs"]),
            "Actual processed SARIF is required",
        )
        require(
            all(
                run.get("tool", {}).get("driver", {}).get("name") == "CodeQL"
                and run.get("results") == []
                for run in raw["runs"]
            ),
            "Unresolved raw CodeQL findings require review",
        )


def security_ready(analyses, alerts, source):
    """Require actual processed analyses for all configured languages, with no open default-branch alert."""
    require(
        isinstance(analyses, list) and isinstance(alerts, list),
        "Malformed security result response",
    )
    require(not alerts, "Open default-branch code-scanning alerts require review before a release")
    expected = {"/language:python", "/language:javascript-typescript", "/language:actions"}
    current = {}
    for row in analyses:
        if row.get("commit_sha") != source or row.get("ref") != "refs/heads/main":
            continue
        if (
            row.get("tool", {}).get("name") != "CodeQL"
            or row.get("analysis_key") != ".github/workflows/codeql.yml:analyze"
        ):
            continue
        category = next(
            (
                name
                for name in expected
                if row.get("category") == name
                or row.get("category") == ".github/workflows/codeql.yml:analyze" + name
            ),
            None,
        )
        if category is None:
            continue
        # The API returns newest first; do not replace the latest processed run
        # with an older successful analysis of the same source/category.
        if category not in current:
            current[category] = row
    require(
        set(current) == expected, "Every configured language requires processed exact-source CodeQL"
    )
    require(
        all(
            row.get("error") == ""
            and row.get("warning") == ""
            and type(row.get("rules_count")) is int
            and row["rules_count"] > 0
            for row in current.values()
        ),
        "CodeQL must finish actual rules without errors or unresolved analyzer warnings",
    )
    return list(current.values())


def accepted_build(report, source, product_version):
    """A source-server run, old/dirty archive or forced process cleanup cannot authorize an upload."""
    require(
        report.get("mode") == "built"
        and report.get("version") == product_version
        and report.get("built_source") == source
        and report.get("source_dirty") is False
        and report.get("native_ui", {}).get("compiled_native") is True
        and report["native_ui"].get("normal_owned_exit") is True
        and report["native_ui"].get("normal_exit_code") == 0
        and report["native_ui"].get("embedded_identity_matches_archive") is True
        and report["native_ui"].get("original_private_and_ml_browser_journeys") == 6
        and report["native_ui"].get("original_compiled_cpu_checks") == 12,
        "Actual clean exact-source extracted native UI and normal-exit acceptance are required",
    )


def draft_ready(release, source, product_version):
    """Reject published or retargeted releases immediately before every upload/publication."""
    require(
        release.get("draft") is True and release.get("prerelease") is False,
        "A stable unpublished draft is required; published bytes are immutable",
    )
    require(
        release.get("tag_name") == "v" + product_version
        and release.get("target_commitish") == source,
        "Draft tag/version/source differs from this checked workflow",
    )


def release_for_version(rows, product_version):
    """Find one version in the bounded authenticated release listing, including an unpublished draft."""
    require(
        isinstance(rows, list) and len(rows) < 100, "Release listing is malformed or incomplete"
    )
    require(all(isinstance(row, dict) for row in rows), "Malformed release entry")
    matches = [row for row in rows if row.get("tag_name") == "v" + product_version]
    require(len(matches) <= 1, "Ambiguous release version; no release changed")
    if not matches:
        return None
    row = matches[0]
    require(type(row.get("id")) is int and 0 < row["id"] < 2**63, "Invalid release identity")
    return row


def load_draft(source, product_version):
    """Use the actual release ID; a draft need not have a published tag-name endpoint."""
    listed = release_for_version(api("releases?per_page=100"), product_version)
    require(listed is not None, "Create the exact-source unpublished draft first")
    release = api("releases/" + str(listed["id"]))
    require(
        type(release.get("id")) is int and release["id"] == listed["id"], "Release identity changed"
    )
    draft_ready(release, source, product_version)
    return release


def prepare_draft(source, product_version):
    """Create only a missing draft with structured JSON; never retarget or replace an existing release."""
    source_ready(source)
    listed = release_for_version(api("releases?per_page=100"), product_version)
    if listed is None:
        notes = ROOT / "docs/releases" / ("v" + product_version + ".md")
        require(
            notes.is_file() and notes.stat().st_size <= 128 * 1024,
            "Reviewed release notes required",
        )
        payload = {
            "tag_name": "v" + product_version,
            "target_commitish": source,
            "name": "Personal Image Model Studio " + product_version,
            "body": notes.read_text(encoding="utf-8"),
            "draft": True,
            "prerelease": False,
        }
        with tempfile.TemporaryDirectory(prefix="pims-release-request-") as temporary:
            path = Path(temporary) / "release.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            command(
                ["gh", "api", f"repos/{REPO}/releases", "--method", "POST", "--input", str(path)]
            )
    load_draft(source, product_version)


def assets_ready(release, product_version, *, complete):
    """Only the documented six platform artifacts may be attached to this draft."""
    expected = set()
    for system, machine in (("windows", "amd64"), ("linux", "x86_64"), ("darwin", "arm64")):
        expected.update(names_for(system, machine, product_version))
    assets = release.get("assets")
    require(isinstance(assets, list), "Missing draft asset metadata")
    result = {}
    for asset in assets:
        name = asset.get("name")
        require(name in expected and name not in result, "Unexpected or duplicate draft asset")
        require(
            type(asset.get("size")) is int and 0 < asset["size"] <= MAX_DOWNLOAD,
            "Invalid draft asset size",
        )
        require(
            isinstance(asset.get("digest"), str)
            and bool(re.fullmatch(r"sha256:[0-9a-f]{64}", asset["digest"])),
            "Provider SHA-256 digest is required",
        )
        result[name] = asset
    require(
        not complete or set(result) == expected,
        "All three verified platform packages/checksums are required",
    )
    return result


def main():
    """Perform one explicitly named release operation; there is no force/clobber path."""
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("source", "prepare", "draft", "upload", "verify"))
    args = parser.parse_args()
    source = os.environ.get("GITHUB_SHA", "")
    require(
        os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("GITHUB_REF") == "refs/heads/main"
        and os.environ.get("GITHUB_REPOSITORY") == REPO,
        "Release operations require the trusted main workflow",
    )
    require(bool(re.fullmatch(r"[0-9a-f]{40}", source)), "Exact workflow source SHA required")
    product_version = version()
    if args.operation == "source":
        source_ready(source)
        return
    if args.operation == "prepare":
        prepare_draft(source, product_version)
        return
    release = load_draft(source, product_version)
    attached = assets_ready(release, product_version, complete=args.operation == "verify")
    if args.operation == "upload":
        system, machine = platform.system().lower(), platform.machine().lower()
        names = names_for(system, machine, product_version)
        report = json.loads(
            (ROOT / "artifacts" / f"native-acceptance-{system}.json").read_text(encoding="utf-8")
        )
        accepted_build(report, source, product_version)
        files = [(ROOT / "release" / name) for name in names]
        for file in files:
            require(
                file.is_file() and not file.is_symlink(),
                "Release asset must be a regular built file",
            )
            require(file.stat().st_size <= MAX_DOWNLOAD, "Built asset exceeds release budget")
            if file.name in attached:
                require(
                    attached[file.name]["size"] == file.stat().st_size
                    and attached[file.name]["digest"] == "sha256:" + digest(file),
                    "Existing draft asset differs; refusing replacement",
                )
        require(
            digest(files[0]) == report.get("archive_sha256"),
            "Package changed after native acceptance",
        )
        binary = "PersonalImageModelStudio" + (".exe" if system == "windows" else "")
        manifest = read_manifest(files[1], files[0].name, binary)
        require(
            manifest[files[0].name] == report["archive_sha256"]
            and manifest[binary] == report["binary_sha256"],
            "Checksum sidecar changed after native acceptance",
        )
        for file in files:
            if file.name not in attached:
                draft_ready(api("releases/" + str(release["id"])), source, product_version)
                # Fixed official upload host and verified numeric release ID;
                # no tag-name lookup, clobber flag or caller-selected endpoint.
                command(
                    [
                        "gh",
                        "api",
                        f"https://uploads.github.com/repos/{REPO}/releases/{release['id']}/assets?name={file.name}",
                        "--method",
                        "POST",
                        "-H",
                        "Content-Type: application/octet-stream",
                        "--input",
                        str(file),
                    ]
                )
            fresh = api("releases/" + str(release["id"]))
            draft_ready(fresh, source, product_version)
            actual = assets_ready(fresh, product_version, complete=False)[file.name]
            require(
                actual["digest"] == "sha256:" + digest(file)
                and actual["size"] == file.stat().st_size,
                "Provider asset differs from accepted local bytes",
            )
    elif args.operation == "verify":
        source_ready(source)
        print(
            "All six immutable draft assets and exact-source gates verified; release remains unpublished."
        )


if __name__ == "__main__":
    main()
