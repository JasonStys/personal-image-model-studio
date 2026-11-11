"""Jason Stys: actual ZIP/tar extraction boundaries and strict two-entry checksum contracts."""
# Index: declarations module.test_real_zip_member_constraints_preserve_outside_sentinel@L26, module.test_real_tar_requires_regular_executable_and_no_links@L69, module.test_checksum_sidecar_rejects_ambiguous_or_partial_names@L100; variables MEMBERS@L14, monkeypatch@L26, mutation@L26, tmp_path@L26, outside@L28, archive@L30, package@L31, data@L32, index@L32, name@L32, member@L35, destination@L52, executable@L55, p@L59, kind@L69, tmp_path@L69, archive@L71, package@L72, data@L73, name@L73, name@L74, member@L75, destination@L85, extra@L100, tmp_path@L100, sidecar@L102, rows@L103. Purposes/parameters: docs/code-map.json.

import io
from pathlib import Path
import stat
import tarfile
import zipfile

import pytest

from scripts.native_distribution import extract_archive, read_manifest

MEMBERS = {
    "PersonalImageModelStudio.exe": b"inert-not-executed",
    "LICENSE": b"authored",
    "INSTALL.md": b"installation",
    "NATIVE_SOURCE.json": b"{}",
    "NATIVE_NOTICES.txt": b"actual notices fixture",
}


@pytest.mark.parametrize(
    "mutation", ["valid", "traversal", "duplicate", "link", "missing", "special-mode", "oversize"]
)
def test_real_zip_member_constraints_preserve_outside_sentinel(tmp_path, monkeypatch, mutation):
    """Construct real malformed archives, never execute fixtures, and verify no outside file is changed."""
    outside = tmp_path / "outside"
    outside.write_bytes(b"retain")
    archive = tmp_path / "package.zip"
    with zipfile.ZipFile(archive, "x") as package:
        for index, (name, data) in enumerate(MEMBERS.items()):
            if mutation == "missing" and index == 4:
                continue
            member = zipfile.ZipInfo(
                "../outside" if mutation == "traversal" and index == 0 else name
            )
            member.external_attr = (
                (stat.S_IFLNK | 0o777) << 16
                if mutation == "link" and index == 0
                else (
                    stat.S_IFREG | (0o4755 if mutation == "special-mode" and index == 0 else 0o644)
                )
                << 16
            )
            package.writestr(member, data)
        if mutation == "duplicate":
            with pytest.warns(UserWarning, match="Duplicate name"):
                package.writestr("LICENSE", b"ambiguous")
    if mutation == "oversize":
        monkeypatch.setattr("scripts.native_distribution.MAX_DOWNLOAD", 5)
    destination = tmp_path / "extract"
    destination.mkdir()
    if mutation == "valid":
        executable = extract_archive(
            archive, destination, "PersonalImageModelStudio.exe", native_metadata=True
        )
        assert executable.read_bytes() == MEMBERS[executable.name]
        assert {p.name: p.read_bytes() for p in destination.iterdir()} == MEMBERS
    else:
        with pytest.raises(ValueError):
            extract_archive(
                archive, destination, "PersonalImageModelStudio.exe", native_metadata=True
            )
    assert outside.read_bytes() == b"retain"


@pytest.mark.parametrize("kind", ["regular", "symlink", "hardlink", "non-executable"])
def test_real_tar_requires_regular_executable_and_no_links(tmp_path, kind):
    """A POSIX package must retain its executable bit; validation never repairs a broken release."""
    archive = tmp_path / "package.tar.gz"
    with tarfile.open(archive, "x:gz") as package:
        for name, data in MEMBERS.items():
            name = name.removesuffix(".exe")
            member = tarfile.TarInfo(name)
            member.size = len(data)
            member.mode = 0o755 if name == "PersonalImageModelStudio" else 0o644
            if name == "PersonalImageModelStudio":
                if kind in {"symlink", "hardlink"}:
                    member.type = tarfile.SYMTYPE if kind == "symlink" else tarfile.LNKTYPE
                    member.linkname = "../outside"
                elif kind == "non-executable":
                    member.mode = 0o644
            package.addfile(member, io.BytesIO(data))
    destination = tmp_path / "extract"
    destination.mkdir()
    if kind == "regular":
        assert (
            extract_archive(
                archive, destination, "PersonalImageModelStudio", native_metadata=True
            ).read_bytes()
            == MEMBERS["PersonalImageModelStudio.exe"]
        )
    else:
        with pytest.raises(ValueError):
            extract_archive(archive, destination, "PersonalImageModelStudio", native_metadata=True)


@pytest.mark.parametrize("extra", ["", "duplicate", "path", "missing"])
def test_checksum_sidecar_rejects_ambiguous_or_partial_names(tmp_path: Path, extra):
    """Checksums cover exactly the archive and executable; foreign names cannot authorize code execution."""
    sidecar = tmp_path / "package.sha256"
    rows = ["a" * 64 + "  package.zip", "b" * 64 + "  PersonalImageModelStudio.exe"]
    if extra == "duplicate":
        rows.append(rows[0])
    elif extra == "path":
        rows[1] = "b" * 64 + "  ../outside.exe"
    elif extra == "missing":
        rows.pop()
    sidecar.write_text("\n".join(rows) + "\n", encoding="ascii")
    if not extra:
        assert read_manifest(sidecar, "package.zip", "PersonalImageModelStudio.exe") == {
            "package.zip": "a" * 64,
            "PersonalImageModelStudio.exe": "b" * 64,
        }
    else:
        with pytest.raises(ValueError):
            read_manifest(sidecar, "package.zip", "PersonalImageModelStudio.exe")
