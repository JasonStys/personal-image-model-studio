"""Jason Stys: extract and validate the real compiled CPU application before any draft upload.
# Index: declarations module.validate@L39, module.main@L162; variables allow_dirty@L39, folder@L39, machine@L42, system@L42, archive_name@L43, sidecar_name@L43, binary_name@L44, archive@L45, sidecar@L45, checksums@L46, proof@L50, extracted@L51, executable@L53, raw_metadata@L55, metadata@L56, source@L57, member@L70, data@L71, smoke@L77, arguments@L78, name@L78, timeout@L78, log_path@L102, log@L104, cpu@L116, browser@L117, observed@L122, result@L135, output@L152, parser@L164, args@L167. Purposes/parameters: docs/code-map.json.

Runs the original native optimizer/sampler and six original browser journeys.
No source server, outside model, provider credentials or user profile is used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import uuid

from PyInstaller.archive.readers import CArchiveReader

if __package__:
    from .native_diagnostics import emit_tail
    from .native_distribution import (
        ROOT,
        digest,
        extract_archive,
        names_for,
        read_manifest,
        require,
    )
else:
    from native_diagnostics import emit_tail
    from native_distribution import ROOT, digest, extract_archive, names_for, read_manifest, require
from studio import __version__
from studio.native_identity import bounded_bytes, unique_pairs


def validate(folder: Path, *, allow_dirty: bool = False) -> dict:
    """Bind archive, extracted binary, embedded metadata and observed service identity to actual source."""
    require(not allow_dirty or not os.environ.get("CI"), "CI cannot accept a dirty local candidate")
    system, machine = platform.system().lower(), platform.machine().lower()
    archive_name, sidecar_name = names_for(system, machine, __version__)
    binary_name = "PersonalImageModelStudio" + (".exe" if system == "windows" else "")
    archive, sidecar = folder / archive_name, folder / sidecar_name
    checksums = read_manifest(sidecar, archive_name, binary_name)
    require(
        digest(archive) == checksums[archive_name], "Archive checksum does not match actual bytes"
    )
    proof = ROOT / ".runtime/native-archive-acceptance" / uuid.uuid4().hex
    extracted = proof / "app"
    extracted.mkdir(parents=True)
    executable = extract_archive(archive, extracted, binary_name, native_metadata=True)
    require(digest(executable) == checksums[binary_name], "Extracted executable checksum differs")
    raw_metadata = bounded_bytes(extracted / "NATIVE_SOURCE.json", 256 * 1024)
    metadata = json.loads(raw_metadata, object_pairs_hook=unique_pairs)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(
        metadata["product"] == "personal-image-model-studio"
        and metadata["version"] == __version__
        and metadata["source"] == source
        and type(metadata["source_dirty"]) is bool
        and (allow_dirty or metadata["source_dirty"] is False),
        "Archive must identify this actual clean source, product and version",
    )
    require(
        CArchiveReader(str(executable)).extract("NATIVE_SOURCE.json") == raw_metadata,
        "Actual executable metadata differs from the archive sidecar",
    )
    for member in ("LICENSE", "NATIVE_NOTICES.txt"):
        data = bounded_bytes(extracted / member, 4 * 1024**2)
        require(
            len(data) == metadata["resources"][member]["bytes"]
            and hashlib.sha256(data).hexdigest() == metadata["resources"][member]["sha256"],
            "Archive license/notice differs from the embedded runtime manifest",
        )
    smoke = proof / "compiled-cpu-smoke.json"
    for name, arguments, timeout in (
        (
            "cpu",
            [
                sys.executable,
                str(ROOT / "scripts/smoke_native.py"),
                str(executable),
                "--report",
                str(smoke),
            ],
            400,
        ),
        (
            "browser",
            [
                sys.executable,
                str(ROOT / "scripts/test_native_browser.py"),
                str(executable),
                "--output",
                str(proof / "browser"),
            ],
            700,
        ),
    ):
        log_path = proof / (name + ".log")
        try:
            with log_path.open("xb") as log:
                subprocess.run(
                    arguments,
                    cwd=ROOT,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=timeout,
                    check=True,
                )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            emit_tail(log_path)
            raise
    cpu = json.loads(smoke.read_text())
    browser = json.loads((proof / "browser/acceptance.json").read_text())
    require(
        cpu["passed"] and cpu["normal_owned_exit"] and cpu["normal_exit_code"] == 0,
        "Compiled CPU acceptance must exit normally",
    )
    observed = browser["identity"]["native"]
    require(
        browser["passed"]
        and browser["normalOwnedExit"]
        and browser["exitCode"] == 0
        and browser["listenerClosed"]
        and browser["executable_sha256"] == checksums[binary_name]
        and observed["source"] == metadata["source"]
        and observed["source_dirty"] is metadata["source_dirty"]
        and observed["version"] == metadata["version"]
        and observed["runtime_library_sha256"] == metadata["runtime_library"]["sha256"],
        "Actual extracted native browser identity or ownership differs",
    )
    result = {
        "mode": "built",
        "version": __version__,
        "built_source": source,
        "source_dirty": metadata["source_dirty"],
        "archive_sha256": checksums[archive_name],
        "binary_sha256": checksums[binary_name],
        "proof": str(proof.relative_to(ROOT)),
        "native_ui": {
            "compiled_native": True,
            "normal_owned_exit": True,
            "normal_exit_code": 0,
            "embedded_identity_matches_archive": True,
            "original_private_and_ml_browser_journeys": 6,
            "original_compiled_cpu_checks": len(cpu["checks"]),
        },
    }
    output = ROOT / "artifacts" / f"native-acceptance-{system}.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if not __debug__:
    raise RuntimeError("Native validation refuses optimized Python")


def main() -> None:
    """Require the complete explicit build directory; local dirty evidence cannot authorize release."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--built-directory", type=Path, required=True)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            validate(args.built_directory.resolve(strict=True), allow_dirty=args.allow_dirty)
        )
    )


if __name__ == "__main__":
    main()
