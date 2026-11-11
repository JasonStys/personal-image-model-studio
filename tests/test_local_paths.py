"""Jason Stys: real local grant/HTTP boundaries and fixed artifact layouts, not scanner exclusions."""
# Index: declarations module.test_canonical_identity_rejects_ambiguous_or_nonserver_keys@L28, module.test_grants_normalize_before_component_check_and_cannot_be_root@L35, module.test_valid_legacy_schemas_cannot_reach_readers_outside_launcher_grants@L57, test_valid_legacy_schemas_cannot_reach_readers_outside_launcher_grants.forbidden@L74, module.test_explicit_legacy_grant_preserves_real_import_and_trusted_runtime_selection@L100, module.test_legacy_fixed_artifact_paths_ignore_tampered_absolute_bodies@L130, module.test_malformed_route_ids_fail_before_lookup_and_file_read@L165, test_malformed_route_ids_fail_before_lookup_and_file_read.forbidden@L172, module.test_actual_directory_alias_cannot_escape_a_launcher_grant@L189, test_actual_directory_alias_cannot_escape_a_launcher_grant.forbidden@L215; variables TOKEN@L21, value@L28, tmp_path@L35, approved@L37, paths@L40, value@L42, monkeypatch@L58, route@L58, selection@L58, tmp_path@L58, approved@L64, choices@L66, app@L71, called@L72, args@L74, kwargs@L74, data@L82, client@L94, response@L95, tmp_path@L100, source@L102, image@L104, app@L107, client@L112, imported@L113, record@L118, runtime@L126, tmp_path@L130, outside@L132, original@L133, app@L135, client@L138, dataset@L139, glossary@L141, response@L144, saved@L146, stream@L150, image@L151, uploaded@L153, downloaded@L158, image@L160, monkeypatch@L165, tmp_path@L165, app@L167, client@L170, args@L172, kwargs@L172, data@L177, method@L177, route@L177, response@L185, monkeypatch@L189, tmp_path@L189, approved@L193, outside@L193, sentinel@L196, alias@L198, command@L200, result@L201, grants@L210, app@L213, args@L215, kwargs@L215, client@L222, response@L223. Purposes/parameters: docs/code-map.json.

from __future__ import annotations

import base64
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from studio.api import create_app
from studio.local_paths import LocalPaths, canonical_id

TOKEN = "synthetic-path-boundary-" + "x" * 40


@pytest.mark.parametrize(
    "value",
    ["a" * 31, "a" * 33, "A" * 32, "../private", "..\\private", "a" * 31 + "\n", True, None],
)
def test_canonical_identity_rejects_ambiguous_or_nonserver_keys(value):
    """Only the actual internally generated lowercase UUID32 grammar can select an artifact."""
    with pytest.raises(KeyError):
        canonical_id(value)
    assert canonical_id("0" * 32) == "0" * 32


def test_grants_normalize_before_component_check_and_cannot_be_root(tmp_path):
    """A sibling-prefix and normalized traversal escape fail despite sharing the approved textual prefix."""
    approved = tmp_path / "approved"
    approved.mkdir()
    (approved / "child").mkdir()
    paths = LocalPaths((approved,))
    assert paths.selected(approved / "child" / "..") == approved.resolve()
    for value in (
        tmp_path / "approved-shadow",
        approved / ".." / "private",
        "\\\\server\\share",
        "//server/share",
        "bad\x00path",
    ):
        with pytest.raises(ValueError):
            paths.selected(value)
    with pytest.raises(ValueError):
        LocalPaths((Path(approved.anchor),))


@pytest.mark.parametrize("route", ["datasets", "models"])
@pytest.mark.parametrize("selection", ["outside", "sibling", "normalized-escape"])
def test_valid_legacy_schemas_cannot_reach_readers_outside_launcher_grants(
    tmp_path, monkeypatch, route, selection
):
    """The whole authorized HTTP request is rejected before dataset/model bytes are inspected."""
    import studio.api as api
    import studio.checkpoints as checkpoints

    approved = tmp_path / "approved"
    approved.mkdir()
    choices = {
        "outside": tmp_path / "outside",
        "sibling": tmp_path / "approved-shadow",
        "normalized-escape": approved / ".." / "outside",
    }
    app = create_app(tmp_path / "workspace", TOKEN, import_roots=(approved,))
    called = []

    def forbidden(*args, **kwargs):
        """Any path reaching an import reader makes the denial fixture fail immediately."""
        called.append(True)
        raise AssertionError("Unauthorised selection reached reader")

    monkeypatch.setattr(api, "import_dataset", forbidden)
    monkeypatch.setattr(api, "inspect_diffusers", forbidden)
    monkeypatch.setattr(checkpoints, "verify", forbidden)
    data = (
        {"name": "owned", "paths": [str(choices[selection])], "rights_confirmed": True}
        if route == "datasets"
        else {
            "name": "owned",
            "path": str(choices[selection]),
            "kind": "native",
            "license_note": "Owned fixture",
        }
    )
    with TestClient(
        app, base_url="http://127.0.0.1:8016", headers={"Authorization": "Bearer " + TOKEN}
    ) as client:
        response = client.post("/api/" + route, json=data)
        assert response.status_code == 400 and not called
        assert str(choices[selection]) not in response.text


def test_explicit_legacy_grant_preserves_real_import_and_trusted_runtime_selection(tmp_path):
    """An independent startup grant admits real local pixels, while runtime selection remains explicit and idle-only."""
    source = tmp_path / "external-approved"
    source.mkdir()
    with Image.new("RGB", (16, 16), "green") as image:
        image.save(source / "owned.png")
    (source / "owned.txt").write_text("owned green fixture", encoding="utf8")
    app = create_app(
        tmp_path / "workspace", TOKEN, import_roots=(source, Path(sys.executable).parent)
    )
    with TestClient(
        app, base_url="http://127.0.0.1:8016", headers={"Authorization": "Bearer " + TOKEN}
    ) as client:
        imported = client.post(
            "/api/datasets",
            json={"name": "owned", "paths": [str(source)], "rights_confirmed": True},
        )
        assert imported.status_code == 200
        record = imported.json()
        assert record["counts"] == {"total": 1, "flagged": 0}
        assert (
            client.get(f"/api/datasets/{record['id']}/review").json()["inspection"][
                "verified_images"
            ]
            == 1
        )
        runtime = client.put("/api/runtime", json={"python": sys.executable, "trusted": True})
        assert runtime.status_code == 200 and runtime.json() == {"configured": True}


def test_legacy_fixed_artifact_paths_ignore_tampered_absolute_bodies(tmp_path):
    """A registered lookup never lets saved absolute text redirect a glossary write or image download."""
    outside = tmp_path / "unrelated-sensitive.txt"
    original = b"private outside sentinel"
    outside.write_bytes(original)
    app = create_app(tmp_path / "workspace", TOKEN)
    with TestClient(
        app, base_url="http://127.0.0.1:8016", headers={"Authorization": "Bearer " + TOKEN}
    ) as client:
        dataset = client.post("/api/datasets/synthetic").json()
        app.state.store.put("dataset", dataset["id"], {**dataset, "path": str(outside)})
        glossary = {
            "entries": {"owned": {"definition": "known", "source": "fixture", "reviewed": True}}
        }
        response = client.put(f"/api/datasets/{dataset['id']}/glossary", json=glossary)
        assert response.status_code == 200
        saved = json.loads(
            (app.state.store.root / "datasets" / dataset["id"] / "glossary.json").read_bytes()
        )
        assert saved == {"schema": 1, **glossary}
        stream = io.BytesIO()
        with Image.new("RGB", (16, 16), "red") as image:
            image.save(stream, format="PNG")
        uploaded = client.post(
            "/api/images",
            json={"name": "owned", "content": base64.b64encode(stream.getvalue()).decode()},
        ).json()
        app.state.store.put("image", uploaded["id"], {**uploaded, "path": str(outside)})
        downloaded = client.get(f"/api/images/{uploaded['id']}/file")
        assert downloaded.status_code == 200 and downloaded.content != original
        with Image.open(io.BytesIO(downloaded.content)) as image:
            assert image.size == (16, 16) and image.getpixel((0, 0)) == (255, 0, 0)
    assert outside.read_bytes() == original


def test_malformed_route_ids_fail_before_lookup_and_file_read(tmp_path, monkeypatch):
    """Every relevant route rejects malformed identifiers before querying the store or touching files."""
    app = create_app(tmp_path / "workspace", TOKEN)
    with TestClient(
        app, base_url="http://127.0.0.1:8016", headers={"Authorization": "Bearer " + TOKEN}
    ) as client:

        def forbidden(*args, **kwargs):
            """A malformed key reaching SQL/file access is a hard regression, never a mocked success."""
            raise AssertionError("Malformed key reached lookup")

        monkeypatch.setattr(app.state.store, "get", forbidden)
        for method, route, data in [
            ("GET", "images/bad/file", None),
            ("GET", "datasets/bad/glossary", None),
            ("PUT", "datasets/bad/glossary", {"entries": {}}),
            ("GET", "datasets/bad/review", None),
            ("GET", "jobs/bad/report", None),
            ("POST", "jobs/bad/cancel", {}),
        ]:
            response = client.request(method, "/api/" + route, json=data)
            assert response.status_code == 404


def test_actual_directory_alias_cannot_escape_a_launcher_grant(tmp_path, monkeypatch):
    """A real NTFS junction/POSIX symlink target outside the grant is refused before any reader."""
    import studio.api as api

    approved, outside = tmp_path / "approved", tmp_path / "outside"
    approved.mkdir()
    outside.mkdir()
    sentinel = outside / "original"
    sentinel.write_bytes(b"retained outside data")
    alias = approved / "redirected"
    if os.name == "nt":
        command = Path(os.environ.get("SYSTEMROOT", "C:/Windows")) / "System32/cmd.exe"
        result = subprocess.run(
            [str(command), "/d", "/c", "mklink", "/J", str(alias), str(outside)],
            capture_output=True,
            check=False,
            timeout=5,
        )
        assert result.returncode == 0, "Actual owned junction fixture could not be created"
    else:
        alias.symlink_to(outside, target_is_directory=True)
    grants = LocalPaths((approved,))
    with pytest.raises(ValueError, match="approved"):
        grants.selected(alias)
    app = create_app(tmp_path / "workspace", TOKEN, import_roots=(approved,))

    def forbidden(*args, **kwargs):
        """The actual alias must be refused without invoking a dataset reader."""
        raise AssertionError("Outside linked input reached reader")

    monkeypatch.setattr(api, "import_dataset", forbidden)
    with TestClient(
        app, base_url="http://127.0.0.1:8016", headers={"Authorization": "Bearer " + TOKEN}
    ) as client:
        response = client.post(
            "/api/datasets", json={"name": "owned", "paths": [str(alias)], "rights_confirmed": True}
        )
        assert response.status_code == 400
    assert sentinel.read_bytes() == b"retained outside data"
