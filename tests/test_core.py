"""Offline contract, ingestion, privacy, provenance and persistence regression checks."""

# Index: declarations module.client@L27, module.picture@L36, module.test_reject_ignored_or_missing_images@L52, module.test_weight_grammar_rejects_ambiguity@L59, module.test_structured_positive_negative_regions@L65, module.test_plain_unicode_weights_are_finite@L84, module.test_phrase_policy_sees_weighted_and_normalized_text@L89, module.test_training_modes_and_limits@L95, module.test_zip_rejects_unsafe_members_before_extraction@L108, module.test_quarantine_dedup_and_atomic_failure@L125, module.test_json_and_confinement@L148, module.test_image_metadata_is_removed@L161, module.test_http_auth_origin_body_and_safe_errors@L174, module.test_http_synthetic_glossary_upload_feedback@L194, module.test_store_feedback_export_and_latest_consent@L238, module.test_pretrained_inspection_blocks_executable_components@L265; variables TOKEN@L23, tmp_path@L27, app@L29, value@L32, color@L36, path@L36, image@L38, extra@L52, mode@L52, value@L59, prompt@L67, result@L73, value@L84, _@L86, weight@L86, member@L108, tmp_path@L108, source@L110, archive@L111, entry@L113, destination@L118, tmp_path@L125, source@L127, manifest@L133, split@L137, record@L138, tmp_path@L148, path@L150, value@L151, tmp_path@L161, image@L163, exif@L164, path@L166, output@L169, client@L174, response@L182, response@L184, client@L194, response@L196, identity@L198, stream@L217, uploaded@L219, tmp_path@L238, store@L240, path@L241, archive@L254, tmp_path@L265. Purposes/parameters: docs/code-map.json.
import base64
import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, strategies as st
from PIL import Image
from studio.api import create_app
from studio.contracts import Generation, Prompt, Subject, Training
from studio.datasets import import_dataset, eligible, extract_zip
from studio.feedback import export_feedback
from studio.files import atomic_json, read_json, confined, normalized_image
from studio.formats import inspect_diffusers
from studio.prompts import weighted, compile_prompt, enforce_policy
from studio.store import Store

TOKEN = "test-session-" + "x" * 40


@pytest.fixture
def client(tmp_path):
    """Use a private temporary workspace and exercise real HTTP boundary/lifespan behavior."""
    app = create_app(tmp_path, TOKEN)
    with TestClient(
        app, base_url="http://127.0.0.1:8016", headers={"Authorization": "Bearer " + TOKEN}
    ) as value:
        yield value


def picture(path: Path, color="red"):
    """Create an owned fixture raster, not a substituted model generation result."""
    image = Image.new("RGB", (32, 32), color)
    image.save(path)
    image.close()


@pytest.mark.parametrize(
    "mode,extra",
    [
        ("text", {"image_id": "source"}),
        ("inpaint", {"image_id": "source"}),
        ("edit", {}),
        ("expand", {"image_id": "source", "mask_id": "mask"}),
    ],
)
def test_reject_ignored_or_missing_images(mode, extra):
    """Edit modes never silently ignore a source/mask or fabricate a required input."""
    with pytest.raises(ValueError):
        Generation(model_id="m", prompt={"tags": "blue"}, mode=mode, **extra)


@pytest.mark.parametrize("value", ["(red:0)", "(red:3)", "((red:1.2):1.3)", "(red)", "red)"])
def test_weight_grammar_rejects_ambiguity(value):
    """Unsupported weight/nesting syntax must fail explicitly."""
    with pytest.raises(ValueError):
        weighted(value)


def test_structured_positive_negative_regions():
    """Independent fields remain separate and numeric weights survive compilation."""
    prompt = Prompt(
        style="watercolor",
        tags="(blue:1.4)",
        negative_style="oil",
        subjects=[Subject(description="circle", region=(0, 0, 0.5, 1), negative="square")],
    )
    result = compile_prompt(prompt.model_dump())
    assert "(blue:1.4)" in result["positive"]
    assert "oil" in result["negative"]
    assert result["regions"][0]["box"] == (0, 0, 0.5, 1)
    with pytest.raises(ValueError):
        Subject(region=(1, 0, 0, 1))
    with pytest.raises(ValueError):
        Prompt(negative_tags="blue")


@given(st.text(alphabet=st.characters(whitelist_categories=("Ll", "Lu")), min_size=1, max_size=40))
def test_plain_unicode_weights_are_finite(value):
    """Property-test plain Unicode spans without granting unsupported parenthesis syntax."""
    assert all(weight == 1 for _, weight in weighted(value))


def test_phrase_policy_sees_weighted_and_normalized_text():
    """Transparent word policy cannot be bypassed merely by adding numeric weight syntax."""
    with pytest.raises(ValueError):
        enforce_policy(compile_prompt({"description": "(BLOCKED:1.3)"}), ["blocked"])


def test_training_modes_and_limits():
    """Native and LoRA configurations have different explicit prerequisites."""
    with pytest.raises(ValueError):
        Training(name="test", dataset_ids=["a"], mode="lora")
    with pytest.raises(ValueError):
        Training(name="test", dataset_ids=["a"], learning_rate=float("nan"))
    with pytest.raises(ValueError):
        Generation(model_id="m", prompt={"tags": "red"}, width=33)


@pytest.mark.parametrize(
    "member", ["../escape.png", "/escape.png", "folder\\escape.png", "C:escape.png", "execute.py"]
)
def test_zip_rejects_unsafe_members_before_extraction(tmp_path, member):
    """Traversal and executable files never reach an extraction destination."""
    source = tmp_path / "source.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("okay.png", b"first")
        entry = zipfile.ZipInfo(member)
        entry.filename = (
            member  # Preserve hostile separators that Windows' ZIP writer normalizes otherwise.
        )
        archive.writestr(entry, b"bad")
    destination = tmp_path / "out"
    destination.mkdir()
    with pytest.raises(ValueError):
        extract_zip(source, destination)
    assert not list(destination.iterdir())


def test_quarantine_dedup_and_atomic_failure(tmp_path):
    """Deduplication cannot erase AI-origin labels; conflicting provenance aborts publication."""
    source = tmp_path / "source"
    source.mkdir()
    picture(source / "a.png")
    picture(source / "b.png", "blue")
    atomic_json(source / "a.json", {"caption": "red circle", "origin": "human"})
    atomic_json(source / "b.json", {"caption": "blue circle", "origin": "ai_generated"})
    manifest = import_dataset([str(source)], tmp_path / "output", "fixture")
    assert manifest["counts"] == {"total": 2, "flagged": 1}
    assert all(
        not record["origin"].startswith("ai_")
        for split in ("train", "validation")
        for record in eligible(manifest, split)
    )
    picture(source / "c.png")
    atomic_json(source / "c.json", {"caption": "red circle", "origin": "ai_generated"})
    with pytest.raises(ValueError, match="conflicting"):
        import_dataset([str(source)], tmp_path / "conflict", "conflict")
    assert not (tmp_path / "conflict").exists()
    assert not list(tmp_path.glob(".import-*"))


def test_json_and_confinement(tmp_path):
    """Strict JSON rejects ambiguous keys, NaN, nonobjects and oversized metadata."""
    path = tmp_path / "input.json"
    for value in ('{"a":1,"a":2}', '{"a":NaN}', "[]"):
        path.write_text(value)
        with pytest.raises(ValueError):
            read_json(path)
    with pytest.raises(ValueError):
        read_json(path, 1)
    with pytest.raises(ValueError):
        confined(tmp_path, "../escape")


def test_image_metadata_is_removed(tmp_path):
    """Private EXIF data must not survive normalization, even when Pillow propagates image info."""
    image = Image.new("RGB", (8, 8))
    exif = Image.Exif()
    exif[315] = "Private artist label"
    path = tmp_path / "image.png"
    image.save(path, exif=exif)
    image.close()
    with normalized_image(path) as output:
        assert not output.info
        assert not output.getexif()


def test_http_auth_origin_body_and_safe_errors(client):
    """Authentication precedes parsing; hostile origins/hosts and bad payloads fail closed."""
    assert client.get("/api/workspace", headers={"Authorization": "bad"}).status_code == 401
    assert (
        client.get("/api/workspace", headers={"Origin": "https://evil.example"}).status_code == 403
    )
    assert client.get("/api/workspace", headers={"Host": "evil.example"}).status_code == 403
    assert client.post("/api/policy", content=b"x" * (8 * 1024 * 1024 + 1)).status_code == 413
    response = client.post("/api/images", json={"name": "secret-name", "content": "not-base64"})
    assert response.status_code == 400
    response = client.post(
        "/api/images",
        json={"name": "secret-name", "content": base64.b64encode(b"not-an-image").decode()},
    )
    assert response.status_code == 400
    assert "secret-name" not in response.text
    assert client.get("/health").headers["cache-control"] == "no-store"
    assert client.get("/api/images/unknown/file").status_code == 404


def test_http_synthetic_glossary_upload_feedback(client):
    """Real synthetic import, validated glossary and consented feedback round-trip through HTTP/SQLite."""
    response = client.post("/api/datasets/synthetic")
    assert response.status_code == 200
    identity = response.json()["id"]
    assert response.json()["counts"]["total"] > 300
    assert (
        client.put(
            f"/api/datasets/{identity}/glossary",
            json={
                "entries": {
                    "light": {"definition": "illumination", "source": "reviewed", "reviewed": True}
                }
            },
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"/api/datasets/{identity}/glossary", json={"entries": {"light": {"definition": 4}}}
        ).status_code
        == 400
    )
    stream = io.BytesIO()
    Image.new("RGB", (32, 32), "red").save(stream, format="PNG")
    uploaded = client.post(
        "/api/images",
        json={"name": "owned source", "content": base64.b64encode(stream.getvalue()).decode()},
    ).json()
    assert client.get(f"/api/images/{uploaded['id']}/file").status_code == 200
    assert (
        client.post(f"/api/images/{uploaded['id']}/feedback", json={"score": 5}).status_code == 200
    )
    assert client.get(f"/api/images/{uploaded['id']}/feedback").json()[0]["score"] == 5
    assert client.get("/api/feedback/export").status_code == 400
    assert (
        client.post(
            "/api/connectors/deviantart/import",
            json={"name": "test", "rights_confirmed": False, "provider_terms_reviewed": True},
        ).status_code
        == 422
    )


def test_store_feedback_export_and_latest_consent(tmp_path):
    """Consent revocation wins over older opt-in; exported pixels stay labelled AI-origin."""
    store = Store(tmp_path)
    path = tmp_path / "owned.png"
    picture(path)
    store.put(
        "image",
        "generated",
        {
            "id": "generated",
            "name": "sample",
            "path": str(path),
            "request": {"prompt": {"description": "red circle"}},
        },
    )
    store.add_feedback("generated", {"score": 3, "allow_training": True})
    with zipfile.ZipFile(io.BytesIO(export_feedback(store))) as archive:
        assert json.loads(archive.read("generated.json"))["origin"] == "ai_generated"
    store.add_feedback("generated", {"score": 4, "allow_training": False})
    with pytest.raises(ValueError, match="consent"):
        export_feedback(store)
    store.put("dataset", "x' OR 1=1--", {"test": True})
    assert store.get("dataset", "x' OR 1=1--") == {"test": True}
    with pytest.raises(KeyError):
        store.get("dataset", "x")


def test_pretrained_inspection_blocks_executable_components(tmp_path):
    """Even a local safe-tensor model cannot request arbitrary Python component classes."""
    atomic_json(tmp_path / "model_index.json", {"_class_name": "CustomPipeline"})
    with pytest.raises(ValueError):
        inspect_diffusers(tmp_path)
