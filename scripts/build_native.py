"""Jason Stys: verified-source one-file CPU app packages, checksums and third-party notices for each build OS."""
# Index: declarations module.notices@L17, module.main@L47; variables VERSION@L14, path@L17, packages@L19, distribution@L20, parts@L22, name@L29, distribution@L30, file@L34, text@L35, root@L49, output@L52, command@L55, name@L92, command@L105, executable@L108, system@L113, machine@L116, architecture@L117, prefix@L120, notice@L121, files@L123, archive@L130, package@L131, name@L132, path@L132, archive@L135, package@L136, name@L137, path@L137, rows@L139, file@L140, content@L141. Purposes/parameters: docs/code-map.json.

import hashlib
import importlib.metadata
import os
import platform
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

VERSION = "0.2.0"


def notices(path: Path):
    """Preserve installed dependency version/license attribution in a generated distribution artifact."""
    packages = sorted(
        {distribution.metadata["Name"] for distribution in importlib.metadata.distributions()}
    )
    parts = [
        "Personal Image Model Studio — Jason Stys\nInstalled build/runtime dependency notices; some build-only packages are not included in the native CPU executable.\n",
        f"Python {sys.version}\n{sys.copyright}\n",
        (Path(__file__).resolve().parents[1] / "docs" / "licenses" / "python-3.12.txt").read_text(
            encoding="utf-8"
        ),
    ]
    for name in packages:
        distribution = importlib.metadata.distribution(name)
        parts.append(
            f"\n=== {name} {distribution.version} ===\nLicense: {distribution.metadata.get('License-Expression') or distribution.metadata.get('License', 'See upstream license')}\n"
        )
        for file in distribution.files or []:
            text = str(file)
            if (
                ".dist-info/" in text
                and "license" in text.lower()
                and distribution.locate_file(file).is_file()
            ):
                parts.append(
                    distribution.locate_file(file).read_text(encoding="utf-8", errors="replace")
                )
    path.write_text("\n".join(parts), encoding="utf-8")


def main():
    """Build native CPU features only; never silently ship GPU drivers, pretrained weights or private runtime data."""
    root = Path(__file__).resolve().parents[1]
    if not (root / "dist" / "index.html").is_file():
        raise SystemExit("Build the TypeScript UI first")
    output = root / "artifacts" / "native"
    output.mkdir(parents=True, exist_ok=True)
    os.environ["PYINSTALLER_CONFIG_DIR"] = str(root / "build" / "native-cache")
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--console",
        "--noupx",
        "--name",
        "PersonalImageModelStudio",
        "--distpath",
        str(output),
        "--workpath",
        str(root / "build" / "native"),
        "--specpath",
        str(root / "build"),
        "--add-data",
        f"{root / 'dist'}:dist",
        "--collect-all",
        "diffusers",
        "--collect-all",
        "safetensors",
        "--collect-all",
        "torch",
        "--copy-metadata",
        "numpy",
        "--copy-metadata",
        "torch",
        "--copy-metadata",
        "diffusers",
        "--copy-metadata",
        "huggingface-hub",
        "--recursive-copy-metadata",
        "diffusers",
        "--recursive-copy-metadata",
        "torch",
    ]
    for name in (
        "transformers",
        "torchvision",
        "peft",
        "accelerate",
        "tensorflow",
        "webview",
        "pytest",
        "hypothesis",
        "matplotlib",
        "scipy",
        "IPython",
    ):
        command += ["--exclude-module", name]
    command.append(str(root / "scripts" / "native_entry.py"))
    subprocess.run(command, cwd=root, check=True)
    executable = output / (
        "PersonalImageModelStudio.exe" if sys.platform == "win32" else "PersonalImageModelStudio"
    )
    if not executable.is_file():
        raise SystemExit("Native application was not created")
    system = (
        "windows" if sys.platform == "win32" else "darwin" if sys.platform == "darwin" else "linux"
    )
    machine = platform.machine().lower()
    architecture = (
        "amd64" if system == "windows" else "arm64" if machine in {"arm64", "aarch64"} else "x86_64"
    )
    prefix = f"PersonalImageModelStudio-{VERSION}-{system}-{architecture}"
    notice = output / "THIRD_PARTY.txt"
    notices(notice)
    files = {
        executable.name: executable,
        "LICENSE": root / "LICENSE",
        "INSTALL.md": root / "docs" / "private-installation.md",
        "THIRD_PARTY.txt": notice,
    }
    if system == "windows":
        archive = output / (prefix + ".zip")
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
            for name, path in files.items():
                package.write(path, name)
    else:
        archive = output / (prefix + ".tar.gz")
        with tarfile.open(archive, "w:gz") as package:
            for name, path in files.items():
                package.add(path, arcname=name, recursive=False)
    rows = []
    for file in (archive, executable):
        with file.open("rb") as content:
            rows.append(hashlib.file_digest(content, "sha256").hexdigest() + "  " + file.name)
    (output / (prefix + ".sha256")).write_text("\n".join(rows) + "\n", encoding="ascii")
    print(
        "Unsigned native CPU package:", archive.name, "bytes:", archive.stat().st_size, flush=True
    )


if __name__ == "__main__":
    main()
