"""Jason Stys: genuine compiled CPU app tests; only disposable aliases, owned pixels and synthetic keys."""
# Index: declarations module.wait_job@L19, module.stop@L34, module.main@L55; variables client@L19, identity@L19, deadline@L21, response@L23, j@L25, job@L25, process@L34, children@L38, child@L39, _@L45, pending@L45, child@L46, parser@L57, args@L60, executable@L61, temporary@L62, root@L63, selected@L64, port@L66, flags@L67, log_path@L68, nonce@L69, log@L70, process@L71, client@L92, deadline@L93, health@L101, credentials@L119, key@L124, dataset@L129, training@L131, model@L147, generated@L148, image@L161, result@L174, worker_log@L196. Purposes/parameters: docs/code-map.json.

import argparse
import base64
import json
import os
import secrets
import socket
import subprocess
import tempfile
import time
from pathlib import Path

import httpx
import psutil


def wait_job(client, identity):
    """Require actual optimizer/sampler completion; a queued response is not a successful ML test."""
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        response = client.get("/private/api/workspace")
        response.raise_for_status()
        job = next(j for j in response.json()["job"] if j["id"] == identity)
        if job["status"] in {"failed", "cancelled", "interrupted"}:
            raise AssertionError("Compiled ML worker failed: " + str(job.get("error")))
        if job["status"] == "completed":
            return job
        time.sleep(0.3)
    raise AssertionError("Compiled CPU worker exceeded its smoke deadline")


def stop(process):
    """Stop only this test's exact subprocess tree after locking; never a user's running app."""
    if process.poll() is not None:
        return
    children = psutil.Process(process.pid).children(recursive=True)
    for child in reversed(children):
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass
    process.terminate()
    _, pending = psutil.wait_procs(children, timeout=10)
    for child in pending:
        child.kill()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def main():
    """Launch the exact binary, train fresh native tensors, sample pixels and verify encrypted persistence."""
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--report", type=Path, default=Path("artifacts/native-smoke.json"))
    args = parser.parse_args()
    executable = args.executable.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="pims-packaged-smoke-") as temporary:
        root = Path(temporary)
        with socket.socket() as selected:
            selected.bind(("127.0.0.1", 0))
            port = selected.getsockname()[1]
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        log_path = root / "launcher.log"
        nonce = secrets.token_hex(16)  # Correlate readiness, not an authentication credential.
        with log_path.open("wb") as log:
            process = subprocess.Popen(
                [
                    str(executable),
                    "--no-browser",
                    "--port",
                    str(port),
                    "--data",
                    str(root / "data"),
                ],
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                env={**os.environ, "PIMS_NO_BROWSER": "1", "PIMS_VALIDATION_NONCE": nonce},
                creationflags=flags,
            )
            try:
                with httpx.Client(
                    base_url=f"http://127.0.0.1:{port}",
                    headers={"X-PIMS-Request": "v1"},
                    timeout=30,
                    trust_env=False,
                ) as client:
                    deadline = time.monotonic() + 120
                    while time.monotonic() < deadline:
                        if process.poll() is not None:
                            raise AssertionError(
                                "Packaged app exited: "
                                + log_path.read_text(errors="replace")[-2000:]
                            )
                        try:
                            health = client.get("/health")
                            if (
                                health.status_code == 200
                                and health.json().get("validation_nonce") == nonce
                            ):
                                break
                        except httpx.RequestError:
                            pass
                        time.sleep(0.25)
                    else:
                        raise AssertionError("Packaged app readiness deadline exceeded")
                    assert (
                        health.json()["mode"] == "private-local-accounts"
                        and health.json()["author"] == "Jason Stys"
                    )
                    assert client.get("/").status_code == 200
                    assert client.get("/private/api/workspace").status_code == 401
                    assert client.get("/api/workspace").status_code in {404, 405}
                    credentials = {
                        "alias": "packaged_" + secrets.token_hex(6),
                        "password": "synthetic-only-packaged-password",
                    }
                    assert client.post("/private/register", json=credentials).status_code == 200
                    key = {
                        "key": base64.b64encode(b"k" * 32).decode(),
                        "salt": base64.b64encode(b"s" * 16).decode(),
                    }
                    assert client.post("/private/unlock", json=key).status_code == 200
                    dataset = client.post("/private/api/datasets/synthetic", json={})
                    assert dataset.status_code == 200
                    training = client.post(
                        "/private/api/train",
                        json={
                            "name": "Packaged genuine native model",
                            "dataset_ids": [dataset.json()["id"]],
                            "steps": 2,
                            "batch_size": 2,
                            "resolution": 32,
                            "max_seconds": 60,
                            "device": "cpu",
                            "seed": 1337,
                        },
                    )
                    assert training.status_code == 200, training.text
                    print("Packaged app ready; checking genuine CPU optimization…", flush=True)
                    wait_job(client, training.json()["id"])
                    model = client.get("/private/api/workspace").json()["model"][0]
                    generated = client.post(
                        "/private/api/generate",
                        json={
                            "model_id": model["id"],
                            "prompt": {"description": "red circle on white background"},
                            "width": 32,
                            "height": 32,
                            "steps": 2,
                            "seed": 77,
                        },
                    )
                    assert generated.status_code == 200, generated.text
                    wait_job(client, generated.json()["id"])
                    image = client.get("/private/api/images/" + generated.json()["id"] + "/file")
                    assert image.status_code == 200 and image.content.startswith(b"\x89PNG")
                    assert client.post("/private/lock", json={}).status_code == 200
                    assert not (root / "data" / "active").exists()
                    assert client.post("/private/unlock", json=key).status_code == 200
                    assert (
                        client.get(
                            "/private/api/images/" + generated.json()["id"] + "/file"
                        ).content
                        == image.content
                    )
                    assert client.post("/private/logout", json={}).status_code == 200
                    assert client.get("/private/account").status_code == 401
                result = {
                    "passed": True,
                    "version": "0.2.0",
                    "checks": [
                        "exact packaged launcher",
                        "author/private mode/UI",
                        "unauthenticated denial",
                        "no legacy plaintext API",
                        "registration and key unlock",
                        "owned dataset",
                        "genuine CPU optimization",
                        "learned PNG generation",
                        "encrypted lock/plaintext removal",
                        "encrypted reopen/pixel persistence",
                        "logout revocation",
                    ],
                    "quality_limit": "Two optimizer steps prove execution, not visual quality. No pretrained weights or user data were used.",
                }
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
                print("Packaged native CPU smoke: all 11 checks passed", flush=True)
            except Exception:
                for worker_log in (root / "data" / "active" / "jobs").glob("*/worker.log"):
                    print(
                        "Synthetic worker diagnostic:",
                        worker_log.read_text(errors="replace")[-2500:],
                    )
                raise
            finally:
                stop(process)


if __name__ == "__main__":
    main()
