"""Jason Stys: streaming authenticated archives for locked, local image workspaces.
# Index: declarations module.safe_name@L29, module.members@L56, module.signature@L77, module.EncryptedWriter@L85, EncryptedWriter.__init__@L88, EncryptedWriter.writable@L92, EncryptedWriter.write@L96, EncryptedWriter.tell@L102, module.encrypt_workspace@L107, module.decrypt_workspace@L157; variables MAGIC@L22, AAD@L23, MAX_BYTES@L24, MAX_FILES@L25, CHUNK@L26, name@L29, path@L31, devices@L32, i@L37, i@L38, c@L45, c@L46, p@L49, root@L56, found@L58, names@L58, total@L58, path@L59, name@L64, total@L69, root@L77, p@L81, encryptor@L88, self@L88, stream@L88, self@L92, data@L96, self@L96, self@L102, destination@L107, key@L107, root@L107, paths@L109, p@L112, descriptor@L115, temporary@L115, scratch@L116, nonce@L118, encryptor@L119, stream@L121, writer@L123, archive@L126, path@L130, source@L131, source@L133, original@L135, copied@L136, content@L140, entry@L143, key@L157, root@L157, source@L157, descriptor@L161, temporary@L161, plain@L163, stream@L163, nonce@L166, tag@L168, remaining@L170, decryptor@L171, chunk@L174, remaining@L177, archive@L180, entries@L181, names@L182, total@L182, entry@L185, name@L186, total@L195, metadata@L198, original@L201, entry@L212, target@L215, content@L217, output@L217. Purposes/parameters: docs/code-map.json.

Keys exist only in the trusted local service while unlocked. The ML workspace is
plaintext during computation; these archives do not protect a compromised OS.
"""

import io
import json
import os
import secrets
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path, PurePosixPath

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = b"PIMSV001"
AAD = b"Jason Stys: Personal Image Model Studio local vault v1"
MAX_BYTES = 8 * 1024**3
MAX_FILES = 20000
CHUNK = 1024**2


def safe_name(name: str) -> str:
    """Permit portable relative paths only; reject links, dot components and Windows devices."""
    path = PurePosixPath(name)
    devices = {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{i}" for i in range(10)),
        *(f"lpt{i}" for i in range(10)),
    }
    if (
        not name
        or len(name) > 240
        or "\\" in name
        or path.is_absolute()
        or any(c in name for c in ":\x00<>|?*")
        or any(ord(c) < 32 for c in name)
        or any(
            p in {"", ".", ".."} or p.endswith((".", " ")) or p.split(".")[0].lower() in devices
            for p in name.split("/")
        )
    ):
        raise ValueError("Invalid portable archive path")
    return path.as_posix()


def members(root: Path) -> list[Path]:
    """Bound file count/bytes and reject filesystem links before snapshotting this exact workspace."""
    found, total, names = [], 0, {"workspace-meta.json"}
    for path in root.rglob("*"):
        if path.is_symlink() or path.is_junction():
            raise ValueError("Workspace links are not supported")
        if not path.is_file() or path.name.endswith(("-wal", "-shm")):
            continue
        name = safe_name(path.relative_to(root).as_posix()).casefold()
        if name in names:
            raise ValueError("Workspace names collide with archive metadata or portable paths")
        names.add(name)
        found.append(path)
        total += path.stat().st_size
        if len(found) > MAX_FILES or total > MAX_BYTES:
            raise ValueError(
                "Workspace exceeds 8 GiB or 20,000 files; export and remove unused data"
            )
    return sorted(found)


def signature(root: Path) -> tuple:
    """O(F) metadata fingerprint; no whole-model hashing or encryption during unchanged UI polling."""
    return tuple(
        (p.relative_to(root).as_posix(), p.stat().st_size, p.stat().st_mtime_ns)
        for p in members(root)
    )


class EncryptedWriter(io.RawIOBase):
    """Non-seekable ZIP output: encrypt each bounded write directly into a private temporary archive."""

    def __init__(self, stream, encryptor):
        """Pair one private file descriptor with a fresh authenticated-encryption context."""
        self.stream, self.encryptor, self.position = stream, encryptor, 0

    def writable(self):
        """Advertise ZIP's streaming data-descriptor path, never pretending to support seek."""
        return True

    def write(self, data):
        """Encrypt bytes without keeping the archive in memory."""
        self.stream.write(self.encryptor.update(data))
        self.position += len(data)
        return len(data)

    def tell(self):
        """Report plaintext ZIP offsets required by its central directory."""
        return self.position


def encrypt_workspace(root: Path, destination: Path, key: bytes):
    """Snapshot idle SQLite databases and atomically publish an AES-256-GCM archive; preserve old on failure."""
    paths = members(root)
    if (
        shutil.disk_usage(destination.parent).free
        < sum(p.stat().st_size for p in paths) + 64 * CHUNK
    ):
        raise ValueError("Not enough disk space to safely save the encrypted workspace")
    descriptor, temporary = tempfile.mkstemp(prefix=".vault-", dir=destination.parent)
    scratch = Path(tempfile.mkdtemp(prefix=".sqlite-snapshot-", dir=destination.parent))
    try:
        nonce = secrets.token_bytes(12)
        encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
        encryptor.authenticate_additional_data(AAD)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(MAGIC + nonce)
            writer = EncryptedWriter(stream, encryptor)
            with zipfile.ZipFile(
                writer, "w", compression=zipfile.ZIP_STORED, allowZip64=True
            ) as archive:
                archive.writestr(
                    "workspace-meta.json", json.dumps({"version": 1, "root": str(root)})
                )
                for path in paths:
                    source = path
                    if path.name in {"studio.sqlite", "quarantine.sqlite"}:
                        source = scratch / path.name
                        with (
                            closing(sqlite3.connect(path)) as original,
                            closing(sqlite3.connect(source)) as copied,
                        ):
                            original.backup(copied)
                    with (
                        source.open("rb") as content,
                        archive.open(
                            path.relative_to(root).as_posix(), "w", force_zip64=True
                        ) as entry,
                    ):
                        shutil.copyfileobj(content, entry, CHUNK)
            stream.write(encryptor.finalize())
            stream.write(encryptor.tag)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
        # Only the newly created scratch directory is removed; never a user-selected path.
        shutil.rmtree(scratch)


def decrypt_workspace(source: Path, root: Path, key: bytes) -> str:
    """Authenticate the entire archive before opening ZIP or exposing extracted files to the ML engine."""
    if source.stat().st_size < 36 or source.stat().st_size > MAX_BYTES + 32 * CHUNK:
        raise ValueError("Invalid encrypted workspace size")
    descriptor, temporary = tempfile.mkstemp(prefix=".verified-", dir=root.parent)
    try:
        with source.open("rb") as stream, os.fdopen(descriptor, "wb") as plain:
            if stream.read(8) != MAGIC:
                raise ValueError("Unsupported encrypted workspace version")
            nonce = stream.read(12)
            stream.seek(-16, os.SEEK_END)
            tag = stream.read(16)
            stream.seek(20)
            remaining = source.stat().st_size - 36
            decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
            decryptor.authenticate_additional_data(AAD)
            while remaining:
                chunk = stream.read(min(CHUNK, remaining))
                if not chunk:
                    raise ValueError("Truncated encrypted workspace")
                remaining -= len(chunk)
                plain.write(decryptor.update(chunk))
            plain.write(decryptor.finalize())
        with zipfile.ZipFile(temporary) as archive:
            entries = archive.infolist()
            names, total = set(), 0
            if len(entries) > MAX_FILES + 1:
                raise ValueError("Too many archive files")
            for entry in entries:
                name = safe_name(entry.filename)
                # Case-insensitive uniqueness keeps restore portable to Windows/macOS.
                if (
                    name.casefold() in names
                    or entry.is_dir()
                    or stat.S_ISLNK(entry.external_attr >> 16)
                ):
                    raise ValueError("Archive duplicates, directories or links are unsupported")
                names.add(name.casefold())
                total += entry.file_size
                if total > MAX_BYTES or entry.compress_type != zipfile.ZIP_STORED:
                    raise ValueError("Unsupported archive compression or size")
            metadata = archive.getinfo("workspace-meta.json")
            if metadata.file_size > 4096:
                raise ValueError("Invalid archive metadata")
            original = json.loads(archive.read(metadata))
            if (
                set(original) != {"version", "root"}
                or original["version"] != 1
                or not isinstance(original["root"], str)
            ):
                raise ValueError("Invalid workspace version")
            if root.exists():
                raise ValueError("Refusing to overwrite an existing recovery workspace")
            root.mkdir(mode=0o700)
            try:
                for entry in entries:
                    if entry.filename == "workspace-meta.json":
                        continue
                    target = root / entry.filename
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(entry) as content, target.open("xb") as output:
                        shutil.copyfileobj(content, output, CHUNK)
            except Exception:
                shutil.rmtree(root)  # This function created and validated this exact new target.
                raise
            return original["root"]
    finally:
        Path(temporary).unlink(missing_ok=True)
