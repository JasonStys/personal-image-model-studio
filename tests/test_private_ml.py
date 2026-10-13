"""Jason Stys: genuine account-scoped CPU training, generation, deterministic replay and encrypted reload."""
# Index: declarations module.wait_for@L19, module.test_private_training_inference_and_encrypted_reopen@L34; variables pytestmark@L13, client@L19, identity@L19, deadline@L21, response@L23, j@L25, job@L25, tmp_path@L34, app@L36, headers@L37, key@L38, salt@L39, client@L40, response@L41, dataset@L47, job@L49, trained@L63, model@L65, outputs@L66, _@L67, generated@L68, image@L81, archive@L85, saved@L86. Purposes/parameters: docs/code-map.json.

import base64
import importlib.util
import time

import pytest
from fastapi.testclient import TestClient

from studio.private_api import create_private_app

pytestmark = [
    pytest.mark.ml,
    pytest.mark.skipif(importlib.util.find_spec("torch") is None, reason="ML extras required"),
]


def wait_for(client, identity):
    """Poll only disposable test-account jobs with a bounded deadline; never fabricate completion."""
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        response = client.get("/private/api/workspace")
        assert response.status_code == 200, response.text
        job = next(j for j in response.json()["job"] if j["id"] == identity)
        if job["status"] in {"failed", "cancelled", "interrupted"}:
            raise AssertionError(job)
        if job["status"] == "completed":
            return job
        time.sleep(0.2)
    raise AssertionError("Genuine ML worker exceeded its test deadline")


def test_private_training_inference_and_encrypted_reopen(tmp_path):
    """Real tensors/optimizer/worker and learned DDIM samples, not an inference placeholder or mocked job."""
    app = create_private_app(tmp_path / "private", 8056)
    headers = {"X-PIMS-Request": "v1"}
    key = base64.b64encode(b"k" * 32).decode()
    salt = base64.b64encode(b"s" * 16).decode()
    with TestClient(app, base_url="http://127.0.0.1:8056", headers=headers) as client:
        response = client.post(
            "/private/register",
            json={"alias": "ml_fixture", "password": "synthetic-only-login-password"},
        )
        assert response.status_code == 200
        assert client.post("/private/unlock", json={"key": key, "salt": salt}).status_code == 200
        dataset = client.post("/private/api/datasets/synthetic", json={})
        assert dataset.status_code == 200, dataset.text
        job = client.post(
            "/private/api/train",
            json={
                "name": "Actual private custom model",
                "dataset_ids": [dataset.json()["id"]],
                "steps": 20,
                "batch_size": 4,
                "resolution": 32,
                "max_seconds": 60,
                "device": "cpu",
                "seed": 1337,
            },
        )
        assert job.status_code == 200, job.text
        trained = wait_for(client, job.json()["id"])
        assert trained["result"]["model"]
        model = client.get("/private/api/workspace").json()["model"][0]
        outputs = []
        for _ in range(2):
            generated = client.post(
                "/private/api/generate",
                json={
                    "model_id": model["id"],
                    "prompt": {"description": "red circle on white background"},
                    "width": 32,
                    "height": 32,
                    "steps": 4,
                    "seed": 77,
                },
            )
            assert generated.status_code == 200, generated.text
            wait_for(client, generated.json()["id"])
            image = client.get("/private/api/images/" + generated.json()["id"] + "/file")
            assert image.status_code == 200 and image.content.startswith(b"\x89PNG")
            outputs.append(image.content)
        assert outputs[0] == outputs[1]
        archive = app.state.manager.archive(app.state.manager.owner)
        saved = archive.stat().st_mtime_ns
        client.get("/private/api/workspace")
        assert archive.stat().st_mtime_ns == saved, "Unchanged polling must not re-encrypt weights"
        assert client.post("/private/lock", json={}).status_code == 200
        assert not app.state.manager.active.exists()
        assert app.state.manager.key is None
        assert client.post("/private/unlock", json={"key": key, "salt": salt}).status_code == 200
        assert client.get("/private/api/workspace").json()["model"][0]["id"] == model["id"]
        assert (
            client.get("/private/api/images/" + generated.json()["id"] + "/file").content
            == outputs[1]
        )
