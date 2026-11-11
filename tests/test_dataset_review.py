"""Owned synthetic dataset review regressions by Jason Stys.
# Index: declarations module.owned_sources@L26, module.test_difference_hash_has_independent_horizontal_bit_oracle@L56, module.test_actual_import_review_finds_cross_split_candidates_and_preserves_all_bytes@L65, module.test_full_metadata_summary_excludes_ai_and_uncaptioned_data@L95, module.test_changed_pixels_or_missing_file_are_explicit_sample_errors@L121, module.test_review_sample_is_bounded_and_never_claims_unchecked_images_passed@L135, module.test_tampered_manifest_is_rejected_without_export_or_mutation@L160, module.test_json_reader_caps_actual_descriptor_bytes_and_rejects_nonobjects@L172, module.test_legacy_review_requires_auth_and_resolves_only_registered_dataset_ids@L185, module.test_private_report_obeys_login_lock_account_scope_and_encrypted_reopen@L200, module.test_thumbnails_bind_imported_pixels_strip_metadata_and_reject_unknown_or_changed_data@L254, module.test_default_decoded_pixel_budget_stops_before_fifth_maximum_size_image@L273, module.test_product_versions_and_fresh_release_target_are_coherent@L291; variables path@L26, records@L29, index@L30, image@L31, x@L33, y@L33, identity@L36, split@L37, record@L38, file@L39, falling@L58, rising@L58, column@L59, row@L59, column@L60, row@L60, tmp_path@L65, identities@L67, root@L68, manifest@L69, before@L70, file@L72, report@L75, pair@L83, side@L84, record@L85, file@L90, tmp_path@L95, source@L97, caption@L99, index@L99, origin@L99, file@L102, image@L103, root@L106, manifest@L107, report@L108, tmp_path@L121, root@L123, manifest@L124, report@L127, error@L131, tmp_path@L135, root@L137, manifest@L138, report@L139, field@L160, tmp_path@L160, value@L160, root@L162, manifest@L163, before@L166, tmp_path@L172, file@L174, tmp_path@L185, token@L187, app@L188, client@L189, record@L192, report@L193, tmp_path@L200, app@L202, key@L203, salt@L204, client@L207, unknown@L208, response@L219, record@L221, url@L222, report@L223, value@L226, original@L228, imported@L229, thumbnail_url@L230, thumbnail@L231, image@L233, tmp_path@L255, root@L258, manifest@L259, record@L260, thumbnail@L261, image@L262, unknown@L265, tmp_path@L273, source@L275, index@L277, file@L278, image@L279, root@L282, manifest@L283, report@L284, root@L295, release@L303. Purposes/parameters: docs/code-map.json.

Actual image ingestion, fingerprints, bounded sampling, account isolation and
read-only integrity are exercised without models, artwork downloads or API calls.
"""

import base64
import hashlib
import io
import json
import tomllib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from studio.api import create_app
from studio.dataset_review import difference_hash, review_dataset, dataset_thumbnail
from studio.datasets import import_dataset, synthetic_dataset
from studio.files import atomic_json, read_json
from studio.private_api import create_private_app


def owned_sources(path: Path):
    """Create distinct near-identical gradient rasters on both deterministic hash splits."""
    path.mkdir()
    records = []
    for index in range(32):
        with Image.new("RGB", (16, 16)) as image:
            image.putdata(
                [(x * 10 + 10, x * 10 + 10, x * 10 + 10) for y in range(16) for x in range(16)]
            )
            image.putpixel((0, 0), (index, index, index))
            identity = hashlib.sha256(f"{image.size}".encode() + image.tobytes()).hexdigest()
            split = "train" if int(identity[:8], 16) % 10 < 8 else "validation"
            if not any(record["split"] == split for record in records):
                file = path / f"gradient-{split}.png"
                image.save(file)
                file.with_suffix(".txt").write_text("owned grayscale gradient", encoding="utf8")
                atomic_json(
                    file.with_suffix(".json"),
                    {
                        "origin": "synthetic_procedural",
                        "name": "<script>inert gradient</script>",
                        "license": "Created by Jason Stys as a synthetic test fixture",
                    },
                )
                records.append({"split": split, "hash": identity})
        if len(records) == 2:
            return records
    raise AssertionError("Did not create both hash partitions")


def test_difference_hash_has_independent_horizontal_bit_oracle():
    """Rising rows yield zero bits, descending rows all bits; no self-derived expected hash."""
    with Image.new("L", (9, 8)) as rising, Image.new("L", (9, 8)) as falling:
        rising.putdata([column * 20 for row in range(8) for column in range(9)])
        falling.putdata([(8 - column) * 20 for row in range(8) for column in range(9)])
        assert difference_hash(rising) == 0
        assert difference_hash(falling) == 2**64 - 1


def test_actual_import_review_finds_cross_split_candidates_and_preserves_all_bytes(tmp_path):
    """Near-identical owned images are candidates, not asserted semantic duplicates or automatically moved."""
    identities = owned_sources(tmp_path / "source")
    root = tmp_path / "dataset"
    manifest = import_dataset([str(tmp_path / "source")], root, "Owned audit fixture")
    before = {
        file.relative_to(root).as_posix(): file.read_bytes()
        for file in root.rglob("*")
        if file.is_file()
    }
    report = review_dataset(root, manifest["fingerprint"])
    assert report["counts"]["eligible_train"] == report["counts"]["eligible_validation"] == 1
    assert not report["minimum_training_counts_met"]
    assert report["inspection"]["verified_images"] == 2
    assert report["inspection"]["integrity_errors"] == []
    assert report["candidate_pairs_total"] == 1
    assert {
        pair[side]["hash"]
        for pair in report["near_duplicate_candidates"]
        for side in ("left", "right")
    } == {record["hash"] for record in identities}
    assert "not proof" in report["limitations"][0]
    assert review_dataset(root, manifest["fingerprint"]) == report
    assert {
        file.relative_to(root).as_posix(): file.read_bytes()
        for file in root.rglob("*")
        if file.is_file()
    } == before


def test_full_metadata_summary_excludes_ai_and_uncaptioned_data(tmp_path):
    """Counts describe all records while integrity/similarity explicitly cover only the bounded eligible sample."""
    source = tmp_path / "source"
    owned_sources(source)
    for index, (origin, caption) in enumerate(
        [("ai_generated", "generated shape"), ("unknown", "")]
    ):
        file = source / f"extra-{index}.png"
        with Image.new("RGB", (32, 32), (200 + index, 0, 0)) as image:
            image.save(file)
        atomic_json(file.with_suffix(".json"), {"origin": origin, "caption": caption})
    root = tmp_path / "dataset"
    manifest = import_dataset([str(source)], root, "Mixed declarations")
    report = review_dataset(root, manifest["fingerprint"])
    assert report["counts"]["total"] == 4
    assert (
        report["counts"]["ai_excluded"]
        == report["counts"]["missing_captions"]
        == report["counts"]["unknown_origin"]
        == 1
    )
    assert report["counts"]["eligible_train"] + report["counts"]["eligible_validation"] == 2
    assert report["counts"]["default_or_missing_license_note"] == 2
    assert report["inspection"]["verified_images"] == 2


def test_changed_pixels_or_missing_file_are_explicit_sample_errors(tmp_path):
    """Corrupt or absent imported bytes remain explicit unknown integrity failures, never passing samples."""
    root = tmp_path / "dataset"
    manifest = synthetic_dataset(root, count=24)
    (root / manifest["records"][0]["file"]).write_bytes(b"changed raster")
    (root / manifest["records"][1]["file"]).unlink()
    report = review_dataset(root, manifest["fingerprint"])
    assert len(report["inspection"]["integrity_errors"]) == 2
    assert report["inspection"]["verified_images"] == len(manifest["records"]) - 2
    assert all(
        str(tmp_path) not in error["reason"] for error in report["inspection"]["integrity_errors"]
    )


def test_review_sample_is_bounded_and_never_claims_unchecked_images_passed(tmp_path):
    """The default 64-image sample and comparison budget remain visible and cannot imply full inspection."""
    root = tmp_path / "dataset"
    manifest = synthetic_dataset(root, count=128)
    report = review_dataset(root, manifest["fingerprint"])
    assert report["inspection"]["verified_images"] == 64
    assert report["inspection"]["remaining_eligible_not_verified"] == len(manifest["records"]) - 64
    assert report["inspection"]["cross_split_comparisons"] <= 32 * 32
    assert len(report["near_duplicate_candidates"]) <= 32
    assert (
        report["candidate_pairs_total"] - len(report["near_duplicate_candidates"])
        == report["candidate_pairs_not_shown"]
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("caption", "altered caption"),
        ("file", "../../private.png"),
        ("origin", []),
        ("split", []),
        ("hash", "fake"),
    ],
)
def test_tampered_manifest_is_rejected_without_export_or_mutation(tmp_path, field, value):
    """Reject edited content/paths/types rather than reviewing a mislabeled imported fingerprint."""
    root = tmp_path / "dataset"
    manifest = synthetic_dataset(root, count=24)
    manifest["records"][0][field] = value
    atomic_json(root / "dataset.json", manifest)
    before = (root / "dataset.json").read_bytes()
    with pytest.raises(ValueError):
        review_dataset(root, manifest["fingerprint"])
    assert (root / "dataset.json").read_bytes() == before


def test_json_reader_caps_actual_descriptor_bytes_and_rejects_nonobjects(tmp_path):
    """Actual descriptor reads obey caller bounds and invalid files cannot become parsed manifests."""
    file = tmp_path / "source.json"
    file.write_text('{"value":"' + "x" * 64 + '"}')
    with pytest.raises(ValueError, match="limit"):
        read_json(file, limit=32)
    with pytest.raises(ValueError, match="regular file"):
        read_json(tmp_path)
    file.write_bytes(b"\xff")
    with pytest.raises(ValueError):
        read_json(file)


def test_legacy_review_requires_auth_and_resolves_only_registered_dataset_ids(tmp_path):
    """The preserved token service accepts only registered dataset identities after authentication."""
    token = "owned-test-session-" + "x" * 40
    app = create_app(tmp_path / "legacy", token, 8016)
    with TestClient(app, base_url="http://127.0.0.1:8016") as client:
        assert client.get("/api/datasets/" + "a" * 32 + "/review").status_code == 401
        client.headers["Authorization"] = "Bearer " + token
        record = client.post("/api/datasets/synthetic").json()
        report = client.get(f"/api/datasets/{record['id']}/review")
        assert report.status_code == 200
        assert report.json()["dataset_fingerprint"] == record["fingerprint"]
        assert client.get("/api/datasets/not-a-dataset/review").status_code == 404
        assert client.get("/api/datasets/" + "a" * 32 + "/review").status_code == 404


def test_private_report_obeys_login_lock_account_scope_and_encrypted_reopen(tmp_path):
    """A real private report survives encrypted reopen but never crosses account, login or lock boundaries."""
    app = create_private_app(tmp_path / "private", 8056)
    key = base64.b64encode(b"r" * 32).decode()
    salt = base64.b64encode(b"s" * 16).decode()
    with TestClient(
        app, base_url="http://127.0.0.1:8056", headers={"X-PIMS-Request": "v1"}
    ) as client:
        unknown = "/private/api/datasets/" + "a" * 32 + "/review"
        assert client.get(unknown).status_code == 401
        assert (
            client.post(
                "/private/register",
                json={"alias": "review_owner", "password": "synthetic-only-review-password"},
            ).status_code
            == 200
        )
        assert client.get(unknown).status_code == 423
        assert client.post("/private/unlock", json={"key": key, "salt": salt}).status_code == 200
        response = client.post("/private/api/datasets/synthetic", json={})
        assert response.status_code == 200, response.text
        record = response.json()
        url = f"/private/api/datasets/{record['id']}/review"
        report = client.get(url)
        assert report.status_code == 200
        assert all(
            value.strip() == "no-store" for value in report.headers["cache-control"].split(",")
        )
        original = report.json()
        imported = read_json(app.state.manager.active / "datasets" / record["id"] / "dataset.json")
        thumbnail_url = url + "/images/" + imported["records"][0]["hash"]
        thumbnail = client.get(thumbnail_url)
        assert thumbnail.status_code == 200 and thumbnail.headers["content-type"] == "image/png"
        with Image.open(io.BytesIO(thumbnail.content)) as image:
            assert max(image.size) <= 192 and not image.info
        assert client.post("/private/lock", json={}).status_code == 200
        assert client.get(url).status_code == 423
        assert client.get(thumbnail_url).status_code == 423
        assert client.post("/private/unlock", json={"key": key, "salt": salt}).status_code == 200
        assert client.get(url).json() == original
        assert client.post("/private/logout", json={}).status_code == 200
        assert (
            client.post(
                "/private/register",
                json={"alias": "other_reviewer", "password": "synthetic-only-review-password"},
            ).status_code
            == 200
        )
        assert client.post("/private/unlock", json={"key": key, "salt": salt}).status_code == 200
        assert client.get(url).status_code == 404
        assert client.get(thumbnail_url).status_code == 404
        assert client.get("/api/datasets/" + record["id"] + "/review").status_code in {404, 405}


def test_thumbnails_bind_imported_pixels_strip_metadata_and_reject_unknown_or_changed_data(
    tmp_path,
):
    """Only manifest identities produce bounded metadata-free previews; untrusted paths and changed files fail."""
    root = tmp_path / "dataset"
    manifest = synthetic_dataset(root, count=24)
    record = manifest["records"][0]
    thumbnail = dataset_thumbnail(root, manifest["fingerprint"], record["hash"])
    with Image.open(io.BytesIO(thumbnail)) as image:
        assert image.format == "PNG" and max(image.size) <= 192
        assert not image.info
    for unknown in ["../private", "0" * 64]:
        with pytest.raises(KeyError):
            dataset_thumbnail(root, manifest["fingerprint"], unknown)
    (root / record["file"]).write_bytes(b"modified")
    with pytest.raises(ValueError, match="changed"):
        dataset_thumbnail(root, manifest["fingerprint"], record["hash"])


def test_default_decoded_pixel_budget_stops_before_fifth_maximum_size_image(tmp_path):
    """The real 16-Mpixel aggregate budget limits actual imported 2048px rasters, independent of hash sampling count."""
    source = tmp_path / "source"
    source.mkdir()
    for index in range(5):
        file = source / f"large-{index}.png"
        with Image.new("RGB", (2048, 2048), (index * 30, 10, 20)) as image:
            image.save(file)
        file.with_suffix(".txt").write_text("owned large color field")
    root = tmp_path / "dataset"
    manifest = import_dataset([str(source)], root, "Owned pixel budget boundary")
    report = review_dataset(root, manifest["fingerprint"])
    assert report["inspection"]["verified_images"] == 4
    assert report["inspection"]["pixels"] == 16_777_216
    assert report["inspection"]["budget_stopped"]
    assert report["inspection"]["remaining_eligible_not_verified"] == 1


def test_product_versions_and_fresh_release_target_are_coherent():
    """The additive native refresh ships as 0.3.1, retaining historical notes and immutable draft delivery."""
    from studio import __version__

    root = Path(__file__).resolve().parents[1]
    assert __version__ == "0.3.1"
    assert tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"] == __version__
    assert json.loads((root / "package.json").read_text())["version"] == __version__
    assert (
        json.loads((root / "package-lock.json").read_text())["packages"][""]["version"]
        == __version__
    )
    release = (root / ".github/workflows/release-native.yml").read_text()
    assert "native-release-v0.3.1" in release
    assert "scripts/native_release_guard.py prepare" in release
    assert "--clobber" not in release and "--draft=false" not in release
    assert "inputs.commit" not in release
    assert (root / "docs/releases/v0.3.1.md").is_file()
    assert (root / "docs/releases/v0.3.0.md").is_file()
    assert (root / "docs/releases/v0.2.0.md").is_file()
