"""Jason Stys: independent exact-source, draft and portable-asset publication boundaries."""
# Index: declarations module.test_source_gate_reads_actual_processed_sarif@L24, test_source_gate_reads_actual_processed_sarif.provider@L31, module.test_unpublished_verifier_has_draft_visibility_without_publication_operation@L65, module.run_fixture@L74, module.test_source_run_requires_exact_completed_main_identity@L93, module.test_source_run_rejects_unrelated_or_unfinished_metadata@L113, module.test_empty_duplicate_and_incomplete_run_pages_fail_closed@L121, module.test_draft_never_accepts_published_or_different_source@L142, module.assets_fixture@L150, module.test_publication_requires_all_six_platform_assets@L162, module.test_portable_metadata_rejects_duplicates_foreign_and_missing_hashes@L182, module.analyses_fixture@L190, module.test_actual_processed_security_records_are_required@L207, module.test_partial_foreign_and_failed_security_results_fail_closed@L230, module.test_latest_failed_same_source_analysis_cannot_be_hidden_by_an_older_success@L238, module.built_fixture@L246, module.test_upload_rejects_old_dirty_or_source_server_acceptance@L264, module.unpublished_release@L290, module.test_unpublished_draft_uses_listing_and_verified_id_without_published_tag@L302, test_unpublished_draft_uses_listing_and_verified_id_without_published_tag.provider@L307, module.test_ambiguous_incomplete_or_malformed_release_pages_fail_closed@L329, module.test_id_resolution_rejects_changed_published_or_different_source@L346, module.test_prepare_resumes_equal_draft_without_writes_or_retarget@L359, module.test_prepare_creates_only_missing_draft_with_literal_structured_notes@L375, test_prepare_creates_only_missing_draft_with_literal_structured_notes.provider@L385, test_prepare_creates_only_missing_draft_with_literal_structured_notes.command@L393, module.test_linux_native_guards_run_with_an_actual_display@L420; variables SOURCE@L20, monkeypatch@L24, raw_finding@L24, rows@L26, number@L27, row@L27, raw_reads@L29, endpoint@L31, sarif@L31, data@L36, workflow@L37, workflow@L67, verifier@L68, field@L113, value@L113, data@L115, data@L123, change@L142, data@L144, names@L152, machine@L154, system@L154, name@L155, name@L158, data@L164, partial@L166, r@L175, r@L176, r@L177, r@L178, r@L179, mutation@L182, data@L184, language@L203, rows@L209, changed@L211, row@L211, changed@L230, rows@L232, rows@L240, failed@L241, change@L267, change@L276, report@L284, monkeypatch@L302, release@L304, calls@L305, endpoint@L307, rows@L329, change@L346, monkeypatch@L346, endpoint@L351, monkeypatch@L359, source@L362, endpoint@L367, _args@L370, monkeypatch@L375, tmp_path@L375, notes@L377, content@L379, _source@L382, created@L383, endpoint@L385, arguments@L393, payload@L402, name@L422, source@L423, commands@L424, line@L426, command@L431, command@L432. Purposes/parameters: docs/code-map.json.

import copy
import json
from pathlib import Path

import pytest

from scripts import native_release_guard as guard
from scripts.native_release_guard import (
    accepted_build,
    assets_ready,
    draft_ready,
    security_ready,
    successful_source_run,
)
from scripts.native_distribution import names_for

SOURCE = "a" * 40


@pytest.mark.parametrize("raw_finding", [False, True])
def test_source_gate_reads_actual_processed_sarif(monkeypatch, raw_finding):
    """Green workflow metadata alone cannot authorize release when actual processed findings remain."""
    rows = analyses_fixture()
    for number, row in enumerate(rows, 100):
        row["id"] = number
    raw_reads = []

    def provider(endpoint, *, sarif=False):
        """Provide independent exact-main identities and an optional real finding-shaped SARIF result."""
        if endpoint == "git/ref/heads/main":
            return {"object": {"sha": SOURCE}}
        if endpoint.startswith("actions/workflows/"):
            data = run_fixture()
            workflow = endpoint.split("/")[2]
            data["workflow_runs"][0]["path"] = ".github/workflows/" + workflow
            return data
        if endpoint.startswith("code-scanning/analyses?"):
            return rows
        if endpoint.startswith("code-scanning/alerts?"):
            return []
        assert sarif is True and endpoint.startswith("code-scanning/analyses/")
        raw_reads.append(endpoint)
        return {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "CodeQL"}},
                    "results": [{"ruleId": "py/path-injection"}] if raw_finding else [],
                }
            ],
        }

    monkeypatch.setattr(guard, "api", provider)
    if raw_finding:
        with pytest.raises(ValueError, match="raw CodeQL"):
            guard.source_ready(SOURCE)
    else:
        guard.source_ready(SOURCE)
        assert len(raw_reads) == 3


def test_unpublished_verifier_has_draft_visibility_without_publication_operation():
    """A read-only API operation still needs GitHub push-level visibility for unpublished releases."""
    workflow = (guard.ROOT / ".github/workflows/release-native.yml").read_text()
    verifier = workflow.split("\n  verify-draft:\n", 1)[1]
    assert "      contents: write\n" in verifier
    assert "scripts/native_release_guard.py verify" in verifier
    assert "gh release edit" not in verifier and "--draft=false" not in verifier


def run_fixture():
    """A complete main-push record, independent of query filtering and workflow code."""
    return {
        "total_count": 1,
        "workflow_runs": [
            {
                "id": 123,
                "head_sha": SOURCE,
                "head_branch": "main",
                "event": "push",
                "path": ".github/workflows/validate.yml",
                "html_url": "https://github.com/JasonStys/personal-image-model-studio/actions/runs/123",
                "status": "completed",
                "conclusion": "success",
            }
        ],
    }


def test_source_run_requires_exact_completed_main_identity():
    """Passing unrelated jobs cannot stand in for this exact source workflow."""
    successful_source_run(run_fixture(), SOURCE, "validate.yml")


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", True),
        ("id", 0),
        ("head_sha", "b" * 40),
        ("head_branch", "feature"),
        ("event", "workflow_dispatch"),
        ("path", ".github/workflows/other.yml"),
        ("html_url", "https://github.com/Other/repo/actions/runs/123"),
        ("status", "in_progress"),
        ("conclusion", "failure"),
        ("conclusion", "skipped"),
    ],
)
def test_source_run_rejects_unrelated_or_unfinished_metadata(field, value):
    """No guessed branch, event, completion, URL or skip substitutions."""
    data = run_fixture()
    data["workflow_runs"][0][field] = value
    with pytest.raises(ValueError):
        successful_source_run(data, SOURCE, "validate.yml")


def test_empty_duplicate_and_incomplete_run_pages_fail_closed():
    """An ambiguous response is not reduced to a convenient successful entry."""
    for data in (
        {"total_count": 0, "workflow_runs": []},
        {"total_count": 2, "workflow_runs": run_fixture()["workflow_runs"]},
        {"total_count": 2, "workflow_runs": run_fixture()["workflow_runs"] * 2},
    ):
        with pytest.raises(ValueError):
            successful_source_run(data, SOURCE, "validate.yml")


@pytest.mark.parametrize(
    "change",
    [
        {"draft": False},
        {"prerelease": True},
        {"target_commitish": "main"},
        {"target_commitish": "b" * 40},
        {"tag_name": "v0.2.0"},
    ],
)
def test_draft_never_accepts_published_or_different_source(change):
    """Old/public release assets cannot become an upload target."""
    data = {"draft": True, "prerelease": False, "tag_name": "v0.3.0", "target_commitish": SOURCE}
    draft_ready(data, SOURCE, "0.3.0")
    with pytest.raises(ValueError):
        draft_ready({**data, **change}, SOURCE, "0.3.0")


def assets_fixture():
    """Six distinct current platform artifacts, each with an independent provider digest."""
    names = [
        name
        for system, machine in (("windows", "amd64"), ("linux", "x86_64"), ("darwin", "arm64"))
        for name in names_for(system, machine, "0.3.0")
    ]
    return {
        "assets": [{"name": name, "size": 42, "digest": "sha256:" + "a" * 64} for name in names]
    }


def test_publication_requires_all_six_platform_assets():
    """Partial drafts are resumable, but cannot be published as complete releases."""
    data = assets_fixture()
    assert len(assets_ready(data, "0.3.0", complete=True)) == 6
    partial = {"assets": data["assets"][:2]}
    assert len(assets_ready(partial, "0.3.0", complete=False)) == 2
    with pytest.raises(ValueError):
        assets_ready(partial, "0.3.0", complete=True)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r["assets"].append(copy.deepcopy(r["assets"][0])),
        lambda r: r["assets"][0].update(name="unexpected.exe"),
        lambda r: r["assets"][0].update(size=True),
        lambda r: r["assets"][0].update(digest=None),
        lambda r: r["assets"][0].update(size=0),
    ],
)
def test_portable_metadata_rejects_duplicates_foreign_and_missing_hashes(mutation):
    """Never infer a valid bundle from asset count alone."""
    data = assets_fixture()
    mutation(data)
    with pytest.raises(ValueError):
        assets_ready(data, "0.3.0", complete=True)


def analyses_fixture():
    """Three processed analyzer records; no workflow-success proxy or fabricated empty result count."""
    return [
        {
            "ref": "refs/heads/main",
            "commit_sha": SOURCE,
            "analysis_key": ".github/workflows/codeql.yml:analyze",
            "category": "/language:" + language,
            "error": "",
            "warning": "",
            "rules_count": 100,
            "tool": {"name": "CodeQL"},
        }
        for language in ("python", "javascript-typescript", "actions")
    ]


def test_actual_processed_security_records_are_required():
    """Passing jobs without every exact-source language result cannot authorize a draft."""
    rows = analyses_fixture()
    security_ready(rows, [], SOURCE)
    for changed in (rows[:-1], [], [{**row, "commit_sha": "b" * 40} for row in rows]):
        with pytest.raises(ValueError):
            security_ready(changed, [], SOURCE)
    with pytest.raises(ValueError):
        security_ready(rows, [{"state": "open"}], SOURCE)


@pytest.mark.parametrize(
    "changed",
    [
        {"ref": "refs/pull/1/merge"},
        {"analysis_key": "other.yml:analyze"},
        {"tool": {"name": "Other"}},
        {"error": "failed to extract"},
        {"warning": "missing source"},
        {"rules_count": 0},
        {"rules_count": True},
    ],
)
def test_partial_foreign_and_failed_security_results_fail_closed(changed):
    """Unrelated or incomplete scans are never substituted for the required current scan."""
    rows = analyses_fixture()
    rows[0].update(changed)
    with pytest.raises(ValueError):
        security_ready(rows, [], SOURCE)


def test_latest_failed_same_source_analysis_cannot_be_hidden_by_an_older_success():
    """Preserve the API's newest-first semantics when the same source is analyzed twice."""
    rows = analyses_fixture()
    failed = {**rows[0], "error": "analysis interrupted"}
    with pytest.raises(ValueError):
        security_ready([failed, *rows], [], SOURCE)


def built_fixture():
    """A current archive report with actual native lifecycle and embedded-source observations."""
    return {
        "mode": "built",
        "version": "0.3.1",
        "built_source": SOURCE,
        "source_dirty": False,
        "native_ui": {
            "compiled_native": True,
            "normal_owned_exit": True,
            "normal_exit_code": 0,
            "embedded_identity_matches_archive": True,
            "original_private_and_ml_browser_journeys": 6,
            "original_compiled_cpu_checks": 12,
        },
    }


def test_upload_rejects_old_dirty_or_source_server_acceptance():
    """Real byte identity, native execution and normal Quit are all required together."""
    accepted_build(built_fixture(), SOURCE, "0.3.1")
    for change in (
        {"mode": "published"},
        {"version": "0.3.0"},
        {"built_source": "b" * 40},
        {"source_dirty": True},
        {"source_dirty": None},
    ):
        with pytest.raises(ValueError):
            accepted_build({**built_fixture(), **change}, SOURCE, "0.3.1")
    for change in (
        {"compiled_native": False},
        {"normal_owned_exit": False},
        {"normal_exit_code": 1},
        {"embedded_identity_matches_archive": False},
        {"original_private_and_ml_browser_journeys": 5},
        {"original_compiled_cpu_checks": 11},
    ):
        report = built_fixture()
        report["native_ui"].update(change)
        with pytest.raises(ValueError):
            accepted_build(report, SOURCE, "0.3.1")


def unpublished_release():
    """A real-shaped draft with a version but no published Git-tag endpoint."""
    return {
        "id": 123,
        "tag_name": "v0.3.1",
        "target_commitish": SOURCE,
        "draft": True,
        "prerelease": False,
        "assets": [],
    }


def test_unpublished_draft_uses_listing_and_verified_id_without_published_tag(monkeypatch):
    """Regression for actual GitHub404 after successful draft creation."""
    release = unpublished_release()
    calls = []

    def provider(endpoint):
        """Record the exact bounded provider lookup while preserving immutable draft identity."""
        calls.append(endpoint)
        assert "/tags/" not in endpoint
        return [release] if endpoint == "releases?per_page=100" else release

    monkeypatch.setattr(guard, "api", provider)
    assert guard.load_draft(SOURCE, "0.3.1") == release
    assert calls == ["releases?per_page=100", "releases/123"]


@pytest.mark.parametrize(
    "rows",
    [
        [unpublished_release(), unpublished_release()],
        [unpublished_release()] * 100,
        [{**unpublished_release(), "id": True}],
        [{**unpublished_release(), "id": -1}],
        {"releases": []},
        [None],
    ],
)
def test_ambiguous_incomplete_or_malformed_release_pages_fail_closed(rows):
    """Do not guess a draft from an ambiguous page or invalid identity."""
    with pytest.raises(ValueError):
        guard.release_for_version(rows, "0.3.1")


@pytest.mark.parametrize(
    "change",
    [
        {"id": 124},
        {"id": True},
        {"draft": False},
        {"prerelease": True},
        {"tag_name": "v0.3.0"},
        {"target_commitish": "b" * 40},
    ],
)
def test_id_resolution_rejects_changed_published_or_different_source(monkeypatch, change):
    """Both the authenticated listing and fresh ID response must describe the same unpublished source."""
    monkeypatch.setattr(
        guard,
        "api",
        lambda endpoint: [unpublished_release()]
        if "?" in endpoint
        else {**unpublished_release(), **change},
    )
    with pytest.raises(ValueError):
        guard.load_draft(SOURCE, "0.3.1")


def test_prepare_resumes_equal_draft_without_writes_or_retarget(monkeypatch):
    """An existing reviewed version is a read-only resume, never a force/clobber operation."""
    monkeypatch.setattr(
        guard, "source_ready", lambda source: source == SOURCE or pytest.fail("wrong source")
    )
    monkeypatch.setattr(
        guard,
        "api",
        lambda endpoint: [unpublished_release()] if "?" in endpoint else unpublished_release(),
    )
    monkeypatch.setattr(
        guard, "command", lambda _args: pytest.fail("Existing release must not be rewritten")
    )
    guard.prepare_draft(SOURCE, "0.3.1")


def test_prepare_creates_only_missing_draft_with_literal_structured_notes(tmp_path, monkeypatch):
    """Notes containing quotes/newlines/shell-like text stay JSON data rather than shell commands."""
    notes = tmp_path / "docs/releases/v0.3.1.md"
    notes.parent.mkdir(parents=True)
    content = 'Authored notes\n"quoted" and $(literal) `text`\n'
    notes.write_text(content)
    monkeypatch.setattr(guard, "ROOT", tmp_path)
    monkeypatch.setattr(guard, "source_ready", lambda _source: None)
    created = []

    def provider(endpoint):
        """Expose only the expected listing and immutable numeric draft lookup for this provider fixture."""
        return (
            ([unpublished_release()] if created else [])
            if "?" in endpoint
            else unpublished_release()
        )

    def command(arguments):
        """Inspect the exact structured draft creation payload without executing shell text."""
        assert arguments[:5] == [
            "gh",
            "api",
            "repos/JasonStys/personal-image-model-studio/releases",
            "--method",
            "POST",
        ]
        payload = json.loads(Path(arguments[-1]).read_text())
        assert payload == {
            "tag_name": "v0.3.1",
            "target_commitish": SOURCE,
            "name": "Personal Image Model Studio 0.3.1",
            "body": content,
            "draft": True,
            "prerelease": False,
        }
        created.append(payload)
        return json.dumps(unpublished_release())

    monkeypatch.setattr(guard, "api", provider)
    monkeypatch.setattr(guard, "command", command)
    guard.prepare_draft(SOURCE, "0.3.1")
    assert len(created) == 1


def test_linux_native_guards_run_with_an_actual_display():
    """The required notice reader loads actual Tk and must never run in a headless Linux preflight."""
    for name in ("native-validation.yml", "release-native.yml"):
        source = (guard.ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
        commands = [
            line.strip()
            for line in source.splitlines()
            if "pytest" in line and "test_native_notices.py" in line
        ]
        assert len(commands) == 3
        assert commands[0].startswith("xvfb-run -a python -m pytest")
        assert all("tests/test_native_owner.py" in command for command in commands)
        assert all(not command.startswith("- run:") for command in commands)
