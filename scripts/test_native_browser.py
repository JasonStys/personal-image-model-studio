"""Jason Stys: replay the original private-account and real-ML browser journeys against an actual compiled app.
# Index: declarations module.digest@L28, module.run@L34, module.main@L200; variables ROOT@L25, path@L28, stream@L30, executable@L34, output@L34, executable@L36, output@L39, copied@L45, inputs@L47, name@L48, original@L49, text@L50, text@L53, text@L54, temporary@L57, profile@L58, nonce@L59, reservation@L60, port@L62, origin@L63, log@L64, process@L65, normal@L73, client@L75, deadline@L76, response@L81, identity@L83, config@L93, node@L122, browser_log@L125, observed_tests@L140, stats@L143, normal@L154, stopped@L155, parser@L202, args@L205. Purposes/parameters: docs/code-map.json.

Only output destinations and service startup are rebound. Original assertions,
timeouts, file inputs, browser controls, encryption and real worker paths remain.
All accounts are synthetic and stored in a new temporary profile.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    """Hash actual opened app/source bytes for reproducible consumer provenance."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(executable: Path, output: Path) -> None:
    """Own one real compiled app, six unchanged Chromium journeys and normal nonce-authorized native Quit."""
    executable = executable.resolve(strict=True)
    if not executable.is_file() or output.exists():
        raise ValueError("Select the compiled application and a fresh evidence directory")
    output = output.resolve()
    if not output.is_relative_to(ROOT / ".runtime"):
        raise ValueError(
            "Keep synthetic browser evidence in this repository's private runtime directory"
        )
    output.mkdir(parents=True)
    copied = output / "original-tests"
    copied.mkdir()
    inputs = {}
    for name in ("private.spec.ts", "private-ml.spec.ts"):
        original = ROOT / "tests" / name
        text = original.read_text(encoding="utf-8")
        # File inputs, all test assertions and deadlines stay byte-for-byte intact.
        # Rebind only screenshots so previous validation evidence is not overwritten.
        text = text.replace('"artifacts/', json.dumps(output.as_posix() + "/")[0:-1])
        text = text.replace("`artifacts/", "`" + output.as_posix() + "/")
        (copied / name).write_text(text, encoding="utf-8")
        inputs[name] = {"source_sha256": digest(original), "consumer_sha256": digest(copied / name)}
    with tempfile.TemporaryDirectory(prefix="pims-native-browser-") as temporary:
        profile = Path(temporary).resolve() / "synthetic-accounts"
        nonce = secrets.token_hex(32)
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        origin = f"http://127.0.0.1:{port}"
        with (output / "native-owner.log").open("xb") as log:
            process = subprocess.Popen(
                [str(executable), "--no-browser", "--port", str(port), "--data", str(profile)],
                cwd=ROOT,
                env={**os.environ, "PIMS_ACCEPTANCE_NONCE": nonce, "PIMS_NO_BROWSER": "1"},
                stdin=subprocess.PIPE,
                stdout=log,
                stderr=log,
            )
            normal = False
            try:
                with httpx.Client(base_url=origin, timeout=3, trust_env=False) as client:
                    deadline = time.monotonic() + 120
                    while True:
                        if process.poll() is not None:
                            raise RuntimeError("The actual compiled owner exited before readiness")
                        try:
                            response = client.get("/health")
                            response.raise_for_status()
                            identity = response.json()
                            break
                        except httpx.HTTPError:
                            if time.monotonic() >= deadline:
                                raise RuntimeError(
                                    "The actual compiled app did not become ready"
                                ) from None
                            time.sleep(0.1)
                    assert identity["version"] == "0.3.1"
                    assert identity["native"]["product"] == "personal-image-model-studio"
                config = output / "playwright.config.mjs"
                config.write_text(
                    'import { defineConfig, devices } from "@playwright/test";\n'
                    "export default defineConfig("
                    + json.dumps(
                        {
                            "testDir": str(copied),
                            "workers": 1,
                            "retries": 0,
                            "fullyParallel": False,
                            "timeout": 90000,
                            "expect": {"timeout": 30000},
                            "reporter": [
                                ["list"],
                                ["json", {"outputFile": str(output / "browser-results.json")}],
                            ],
                            "outputDir": str(output / "test-results"),
                            "use": {
                                "baseURL": origin,
                                "viewport": {"width": 1280, "height": 900},
                                "trace": "retain-on-failure",
                                "screenshot": "only-on-failure",
                            },
                            "projects": [{"name": "chromium", "use": {"browserName": "chromium"}}],
                        }
                    )
                    + ");\n",
                    encoding="utf-8",
                )
                node = shutil.which("node")
                if node is None:
                    raise ValueError("Use the trusted test environment's Node runtime")
                with (output / "original-browser-journeys.log").open("xb") as browser_log:
                    subprocess.run(
                        [
                            node,
                            str(ROOT / "node_modules/@playwright/test/cli.js"),
                            "test",
                            "--config",
                            str(config),
                        ],
                        cwd=ROOT,
                        stdout=browser_log,
                        stderr=subprocess.STDOUT,
                        check=True,
                        timeout=600,
                    )
                observed_tests = json.loads(
                    (output / "browser-results.json").read_text(encoding="utf-8")
                )
                stats = observed_tests["stats"]
                if not (
                    stats["expected"] == 6
                    and stats["unexpected"] == stats["skipped"] == stats["flaky"] == 0
                ):
                    raise ValueError(
                        "All six original private/ML journeys must run without skips or retries"
                    )
                process.stdin.write(("quit " + nonce + "\n").encode("ascii"))
                process.stdin.flush()
                assert process.wait(timeout=30) == 0
                normal = True
                with socket.socket() as stopped:
                    stopped.settimeout(0.5)
                    assert stopped.connect_ex(("127.0.0.1", port)) != 0
                (output / "acceptance.json").write_text(
                    json.dumps(
                        {
                            "passed": True,
                            "executable_sha256": digest(executable),
                            "identity": identity,
                            "originalTests": inputs,
                            "originalPrivateAndMlBrowserJourneys": 6,
                            "normalOwnedExit": True,
                            "exitCode": 0,
                            "listenerClosed": True,
                            "ordinaryUserProfilesOpened": False,
                            "qualityLimit": "Small synthetic model training proves execution and persistence, not production image quality.",
                        },
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
            finally:
                if process.poll() is None:
                    # Failure cleanup never writes a passing receipt.
                    process.stdin.write(("quit " + nonce + "\n").encode("ascii"))
                    process.stdin.flush()
                    try:
                        process.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        process.wait(timeout=15)
                if process.stdin:
                    process.stdin.close()
                if not normal:
                    print(
                        "Compiled-browser validation failed; original evidence is retained.",
                        flush=True,
                    )


if not __debug__:
    raise RuntimeError("Native validation refuses optimized Python")


def main() -> None:
    """Require an explicit actual executable and a fresh private proof output."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.executable, args.output)


if __name__ == "__main__":
    main()
