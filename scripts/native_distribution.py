"""Jason Stys: bounded native archive validation and literal trusted release helpers.
# Index: declarations module.require@L23, module.command@L29, module.names_for@L49, module.digest@L60, module.read_manifest@L66, module.extract_archive@L83, extract_archive.write@L99; variables REPO@L17, ROOT@L18, MAX_DOWNLOAD@L19, MAX_EXPANDED@L20, condition@L23, message@L23, arguments@L29, timeout@L29, completed@L31, detail@L42, machine@L49, system@L49, version@L49, stem@L56, path@L60, stream@L62, archive_name@L66, binary_name@L66, path@L66, result@L69, line@L70, match@L71, archive@L83, binary_name@L83, destination@L83, native_metadata@L83, expected@L89, total@L96, seen@L97, mode@L99, name@L99, size@L99, stream@L99, target@L110, copied@L115, output@L116, chunk@L117, copied@L118, total@L124, bundle@L128, member@L130, mode@L131, stream@L136, bundle@L139, member@L140, stream@L143. Purposes/parameters: docs/code-map.json.

Authored shared packaging patterns retain their complete name, type, byte and
checksum controls. These helpers never access account or provider information.
"""

import hashlib
import re
import stat
import sys
import subprocess
import tarfile
import zipfile
from pathlib import Path

REPO = "JasonStys/personal-image-model-studio"
ROOT = Path(__file__).resolve().parents[1]
MAX_DOWNLOAD = 768 * 1024 * 1024
MAX_EXPANDED = 1024 * 1024 * 1024


def require(condition, message):
    """Fail closed even when a caller enables Python optimization."""
    if not condition:
        raise ValueError(message)


def command(arguments, *, timeout=120):
    """Run literal trusted argument arrays; no shell or credential output."""
    completed = subprocess.run(  # noqa: S603 -- fixed QA commands and a digest-verified owned native binary; no shell.
        arguments,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )  # noqa: S603 -- literal trusted build/QA commands; no shell.
    if completed.returncode:
        detail = completed.stderr[-2500:] if arguments[0] == "node" else ""
        raise RuntimeError(
            f"Acceptance command failed: {Path(arguments[0]).name} (exit {completed.returncode}) {detail}"
        )
    return completed.stdout


def names_for(system, machine, version):
    """Use only the three architectures actually published; never guess an ABI."""
    require(
        (system, machine) in {("windows", "amd64"), ("linux", "x86_64"), ("darwin", "arm64")},
        "No reviewed portable archive exists for this OS/architecture",
    )
    require(bool(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version)), "Invalid product version")
    stem = f"PersonalImageModelStudio-{version}-{system}-{machine}"
    return stem + (".zip" if system == "windows" else ".tar.gz"), stem + ".sha256"


def digest(path):
    """Stream file hashes without loading an executable into controller memory."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_manifest(path, archive_name, binary_name):
    """Only two literal basename entries are expected; reject duplicates and traversal."""
    require(path.stat().st_size <= 4096, "Checksum sidecar exceeds its budget")
    result = {}
    for line in path.read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        require(
            match is not None and match[2] not in result, "Malformed or ambiguous checksum sidecar"
        )
        result[match[2]] = match[1]
    require(
        set(result) == {archive_name, binary_name},
        "Checksum sidecar does not cover exact package/binary",
    )
    return result


def extract_archive(archive, destination, binary_name, *, native_metadata=False):
    """Extract only exact historical/current regular members into a newly owned empty directory.

    The CPU application is one-file PyInstaller, so no archive links are necessary. POSIX binary
    executable bits must already exist; tests never repair missing archive modes.
    """
    expected = {binary_name, "LICENSE", "INSTALL.md"}
    if native_metadata:
        expected.update({"NATIVE_SOURCE.json", "NATIVE_NOTICES.txt"})
    require(
        destination.is_dir() and not any(destination.iterdir()),
        "Extraction directory must be empty",
    )
    total = 0
    seen = set()

    def write(name, size, mode, stream):
        """Stream an exact allowed regular member exclusively, enforcing declared and total expanded budgets."""
        nonlocal total
        require(name in expected and name not in seen, "Unexpected/duplicate portable member")
        require(
            0 <= size <= MAX_DOWNLOAD and total + size <= MAX_EXPANDED,
            "Expanded package exceeds byte budget",
        )
        require(not mode & 0o7000, "Special executable permission bits are forbidden")
        if not archive.name.endswith(".zip") and name == binary_name:
            require(bool(mode & 0o100), "POSIX executable mode was lost in the archive")
        target = destination / name
        require(
            target.parent.resolve() == destination.resolve(),
            "Portable member escapes extraction root",
        )
        copied = 0
        with target.open("xb") as output:
            while chunk := stream.read(min(1024 * 1024, size - copied + 1)):
                copied += len(chunk)
                require(copied <= size, "Archive member exceeds declared length")
                output.write(chunk)
        require(copied == size, "Truncated portable member")
        if sys.platform != "win32":
            target.chmod(mode & 0o777)
        total += copied
        seen.add(name)

    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as bundle:
            require(len(bundle.infolist()) == len(expected), "Unexpected ZIP member count")
            for member in bundle.infolist():
                mode = member.external_attr >> 16
                require(
                    not member.is_dir() and stat.S_IFMT(mode) in {0, stat.S_IFREG},
                    "ZIP links or special files are forbidden",
                )
                with bundle.open(member) as stream:
                    write(member.filename, member.file_size, mode, stream)
    else:
        with tarfile.open(archive, "r:gz") as bundle:
            for member in bundle:
                require(len(seen) < len(expected), "Unexpected tar member count")
                require(member.isfile(), "Tar links or special files are forbidden")
                stream = bundle.extractfile(member)
                require(stream is not None, "Missing tar member bytes")
                with stream:
                    write(member.name, member.size, member.mode, stream)
    require(seen == expected, "Incomplete portable archive")
    return destination / binary_name
