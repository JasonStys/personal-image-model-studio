"""Jason Stys: source-bound portable app packaging with actual runtime notices and fresh outputs.
# Index: declarations module.packaged_library@L34, module.runtime_library@L62, module.main@L77; variables ROOT@L31, binary@L34, name@L34, archive@L38, seen@L39, _@L40, _flag@L44, _offset@L44, compressed@L44, expanded@L44, kind@L44, data@L47, target@L51, name@L52, argv@L77, parser@L79, args@L86, git@L96, source@L99, dirty@L100, output@L103, resources@L108, notices@L124, versions@L124, library_name@L125, library_path@L125, library_bytes@L126, library_digest@L127, scratch@L130, notice_file@L133, data@L135, name@L135, metadata@L140, metadata_file@L158, command@L162, command@L184, source_file@L185, target@L185, command@L191, module@L192, command@L198, module@L199, command@L215, module@L216, command@L217, module@L218, command@L219, command@L220, binary@L222, attempt@L231, cooked@L238, cooked_digest@L239, stem@L261, files@L262, archive@L270, target@L271, file@L272, name@L272, archive@L275, target@L276, file@L277, name@L277, hashes@L279, file@L280, stream@L281. Purposes/parameters: docs/code-map.json.

No accounts, credentials, runtime data, release tokens or provider settings enter
the distribution. This script builds only; publication has separate exact-main
workflow/security/download gates. Symbol indexes are generated before release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import posixpath
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import tomllib
import uuid
import zipfile
from pathlib import Path

from studio import __version__ as VERSION
from studio.native_identity import WINDOWS_PYTHON_SHA256, bounded_bytes, ui_files
from scripts.native_notices import collect

ROOT = Path(__file__).resolve().parents[1]


def packaged_library(binary: Path, name: str) -> bytes:
    """Read actual bounded frozen library bytes, following only internal CArchive framework aliases."""
    from PyInstaller.archive.readers import CArchiveReader

    archive = CArchiveReader(str(binary))
    seen = set()
    for _ in range(8):
        if name in seen or name not in archive.toc:
            raise ValueError("Frozen Python library alias is missing or cyclic")
        seen.add(name)
        _offset, compressed, expanded, _flag, kind = archive.toc[name]
        if not 0 < expanded <= 64 * 1024 * 1024 or not 0 < compressed <= 64 * 1024 * 1024:
            raise ValueError("Frozen Python library exceeds its bound")
        data = archive.extract(name)
        if kind == "n":
            if len(data) > 4096 or not data.endswith(b"\0") or b"\0" in data[:-1]:
                raise ValueError("Invalid frozen framework alias")
            target = data[:-1].decode("utf-8")
            name = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
            if name.startswith(("/", "../")) or name == ".." or "\\" in name:
                raise ValueError("Frozen framework alias escapes the package")
        else:
            if kind != "b" or len(data) != expanded:
                raise ValueError("Frozen Python library payload differs")
            return data
    raise ValueError("Frozen framework alias chain exceeds its bound")


def runtime_library() -> tuple[str, Path]:
    """Locate the actual selected interpreter library without searching another installed Python."""
    if sys.platform == "win32":
        return "python314.dll", Path(sys.base_prefix) / "python314.dll"
    if sys.platform == "darwin":
        return "Python", Path(
            sysconfig.get_config_var("PYTHONFRAMEWORKPREFIX")
        ) / "Python.framework/Versions/3.14/Python"
    if sys.platform == "linux":
        return "libpython3.14.so.1.0", Path(
            sysconfig.get_config_var("LIBDIR")
        ) / "libpython3.14.so.1.0"
    raise ValueError("Review another native platform before packaging")


def main(argv=None) -> None:
    """Freeze the real private browser app and native owner window; never overwrite an earlier candidate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT / "release")
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Label a local development candidate; forbidden in CI",
    )
    args = parser.parse_args(argv)
    if sys.version_info[:3] != (3, 14, 10) or sys.version_info.releaselevel != "final":
        raise ValueError("Native packaging requires final patched CPython3.14.10")
    if args.allow_dirty and os.environ.get("CI", "").lower() in {"1", "true"}:
        raise ValueError("CI cannot label dirty source as a portable candidate")
    if (
        tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"] != VERSION
        or json.loads((ROOT / "package.json").read_text())["version"] != VERSION
    ):
        raise ValueError("Python/UI/native version coherence failed")
    git = shutil.which("git")
    if git is None:
        raise ValueError("The trusted build environment must provide Git")
    source = subprocess.check_output([git, "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()  # noqa: S603 -- resolved trusted build tool and literal Git arguments
    dirty = bool(subprocess.check_output([git, "status", "--porcelain"], cwd=ROOT).strip())  # noqa: S603 -- resolved trusted build tool, no shell/input code
    if dirty and not args.allow_dirty:
        raise ValueError("Native distribution requires clean reviewed source")
    output = args.output_root.resolve()
    if not output.is_relative_to(ROOT.resolve()) or output.exists():
        raise ValueError(
            "Choose a fresh build directory within this repository; existing outputs are preserved"
        )
    resources = ui_files(ROOT)
    subprocess.run(  # noqa: S603 -- fixed owned interpreter and literal test module
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_native_notices.py",
            "--capture=sys",
            "-q",
            "-o",
            "cache_dir=" + str(ROOT / ".runtime/native-notice-cache" / uuid.uuid4().hex),
        ],
        cwd=ROOT,
        check=True,
        timeout=45,
    )
    versions, notices = collect(ROOT)
    library_name, library_path = runtime_library()
    library_bytes = bounded_bytes(library_path.resolve(), 64 * 1024 * 1024)
    library_digest = hashlib.sha256(library_bytes).hexdigest()
    if sys.platform == "win32" and library_digest != WINDOWS_PYTHON_SHA256:
        raise ValueError("The Windows Python runtime differs from the independently reviewed SDK")
    scratch = ROOT / ".runtime/native-package-stage" / uuid.uuid4().hex
    scratch.mkdir(parents=True)
    output.mkdir(parents=True)
    notice_file = scratch / "NATIVE_NOTICES.txt"
    notice_file.write_bytes(notices)
    for name, data in (
        ("LICENSE", bounded_bytes(ROOT / "LICENSE", 1024 * 1024)),
        (notice_file.name, notices),
    ):
        resources[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    metadata = {
        "schema": 1,
        "product": "personal-image-model-studio",
        "version": VERSION,
        "source": source,
        "source_dirty": dirty,
        "python": platform.python_version(),
        "platform": sys.platform,
        "machine": platform.machine(),
        **versions,
        "runtime_library": {
            "file": library_name,
            "bytes": len(library_bytes),
            "sha256": library_digest,
            "sdk_sha256": library_digest,
        },
        "resources": resources,
    }
    metadata_file = scratch / "NATIVE_SOURCE.json"
    metadata_file.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(metadata_file, output / metadata_file.name)
    shutil.copy2(notice_file, output / notice_file.name)
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--noupx",
        "--onefile",
        "--name",
        "PersonalImageModelStudio",
        "--distpath",
        str(output / "bin"),
        "--workpath",
        str(scratch / "build"),
        "--specpath",
        str(scratch),
        "--paths",
        str(ROOT),
    ]
    if sys.platform == "win32":
        # Console-mode pipes remain usable for scoped acceptance; PyInstaller
        # hides only its own normal console, never a user's inherited terminal.
        command += ["--hide-console", "hide-early"]
    for source_file, target in (
        (ROOT / "dist", "dist"),
        (ROOT / "LICENSE", "."),
        (notice_file, "."),
        (metadata_file, "."),
    ):
        command += ["--add-data", str(source_file) + os.pathsep + target]
    for module in (
        "uvicorn.logging",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.lifespan.on",
    ):
        command += ["--hidden-import", module]
    for module in (
        "pytest",
        "pip",
        "setuptools",
        "ruff",
        "transformers",
        "torchvision",
        "peft",
        "accelerate",
        "tensorflow",
        "webview",
        "hypothesis",
        "matplotlib",
        "scipy",
        "IPython",
    ):
        command += ["--exclude-module", module]
    for module in ("torch", "diffusers", "safetensors"):
        command += ["--collect-all", module]
    for module in ("torch", "diffusers", "safetensors", "numpy", "huggingface-hub"):
        command += ["--recursive-copy-metadata", module]
    command += ["--runtime-hook", str(ROOT / "studio/native_privacy.py")]
    command.append(str(ROOT / "scripts/native_entry.py"))
    binary = (
        output
        / "bin"
        / (
            "PersonalImageModelStudio.exe"
            if sys.platform == "win32"
            else "PersonalImageModelStudio"
        )
    )
    for attempt in range(2):
        subprocess.run(  # noqa: S603 -- fixed trusted freezer argv, no shell or uploaded source
            command,
            cwd=ROOT,
            check=True,
            env={**os.environ, "PYINSTALLER_CONFIG_DIR": str(scratch / "cache")},
        )
        cooked = packaged_library(binary, library_name)
        cooked_digest = hashlib.sha256(cooked).hexdigest()
        if sys.platform == "win32" and cooked_digest != WINDOWS_PYTHON_SHA256:
            raise ValueError("Windows freezing changed the independently pinned Python DLL")
        if metadata["runtime_library"]["sha256"] == cooked_digest and metadata["runtime_library"][
            "bytes"
        ] == len(cooked):
            from PyInstaller.archive.readers import CArchiveReader

            if (
                CArchiveReader(str(binary)).extract("NATIVE_SOURCE.json")
                != metadata_file.read_bytes()
            ):
                raise ValueError("Actual embedded source metadata differs from the archive sidecar")
            break
        if attempt:
            raise ValueError("Processed Python runtime changed across source-binding passes")
        # macOS load-path repair and ad-hoc signing legitimately change SDK
        # library bytes. Bind the measured cooked payload on a second pass,
        # retaining the original SDK digest separately; never waive the check.
        metadata["runtime_library"].update(bytes=len(cooked), sha256=cooked_digest)
        metadata_file.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        shutil.copy2(metadata_file, output / metadata_file.name)
    stem = f"PersonalImageModelStudio-{VERSION}-{platform.system().lower()}-{platform.machine().lower()}"
    files = [
        (binary, binary.name),
        (ROOT / "LICENSE", "LICENSE"),
        (ROOT / "docs/private-installation.md", "INSTALL.md"),
        (metadata_file, metadata_file.name),
        (notice_file, notice_file.name),
    ]
    if sys.platform == "win32":
        archive = output / (stem + ".zip")
        with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as target:
            for file, name in files:
                target.write(file, name)
    else:
        archive = output / (stem + ".tar.gz")
        with tarfile.open(archive, "x:gz") as target:
            for file, name in files:
                target.add(file, arcname=name, recursive=False)
    hashes = []
    for file in (archive, binary):
        with file.open("rb") as stream:
            hashes.append(hashlib.file_digest(stream, "sha256").hexdigest() + "  " + file.name)
    (output / (stem + ".sha256")).write_text("\n".join(hashes) + "\n", encoding="ascii")
    print(
        f"Built unsigned portable candidate {archive.name}; source_dirty={dirty}. No publication or installation performed."
    )


if __name__ == "__main__":
    main()
