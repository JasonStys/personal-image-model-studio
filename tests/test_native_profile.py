"""Jason Stys: actual private-path alias controls preserve sentinels and existing ordinary recovery bytes.
# Index: declarations module.test_linked_fixed_private_member_is_refused_before_any_write@L18, module.test_ordinary_fixed_recovery_is_admitted_without_reading_or_replacing@L33, module.test_existing_nested_archive_or_recovery_hardlink_is_rejected@L46, module.test_application_tree_is_refused_before_directory_creation@L59, module.test_instance_lock_never_writes_through_a_link_and_second_owner_does_not_append@L69, module.test_real_directory_alias_is_refused_without_touching_target@L91; variables name@L18, tmp_path@L18, root@L20, sentinel@L22, before@L25, name@L33, tmp_path@L33, root@L35, state@L37, before@L39, name@L46, tmp_path@L46, root@L48, folder@L49, original@L51, tmp_path@L59, program@L61, destination@L63, tmp_path@L69, path@L71, owner@L72, before@L74, original@L81, linked@L83, mode@L91, tmp_path@L91, target@L93, sentinel@L95, root@L97, alias@L100, alias@L102, system@L104, chosen@L113. Purposes/parameters: docs/code-map.json.

Locations for declarations and state are generated in docs/code-map.json.
"""

import os
import subprocess
from pathlib import Path

import pytest

from studio.native_profile import DIRECTORIES, FILES, admit_root
from studio.private_workspace import InstanceLock


@pytest.mark.parametrize("name", FILES)
def test_linked_fixed_private_member_is_refused_before_any_write(tmp_path, name):
    """Every fixed lock/metadata/recovery member must refuse a real hard-link sentinel."""
    root = tmp_path / "private"
    root.mkdir()
    sentinel = tmp_path / "sentinel.txt"
    sentinel.write_bytes(b"untouched unrelated account-path sentinel\n")
    os.link(sentinel, root / name)
    before = sentinel.stat()
    with pytest.raises(ValueError, match="single-link"):
        admit_root(root)
    assert sentinel.read_bytes() == b"untouched unrelated account-path sentinel\n"
    assert sentinel.stat().st_mtime_ns == before.st_mtime_ns


@pytest.mark.parametrize("name", FILES)
def test_ordinary_fixed_recovery_is_admitted_without_reading_or_replacing(tmp_path, name):
    """Admission never interprets, truncates or removes ordinary recovery members."""
    root = tmp_path / "private"
    root.mkdir()
    state = root / name
    state.write_bytes(b"ordinary retained recovery evidence")
    before = state.stat()
    assert admit_root(root) == root
    assert state.read_bytes() == b"ordinary retained recovery evidence"
    assert state.stat().st_mtime_ns == before.st_mtime_ns


@pytest.mark.parametrize("name", DIRECTORIES)
def test_existing_nested_archive_or_recovery_hardlink_is_rejected(tmp_path, name):
    """Recovery and encrypted-tree writes cannot follow a pre-existing linked payload."""
    root = tmp_path / "private"
    folder = root / name / "nested"
    folder.mkdir(parents=True)
    original = tmp_path / "outside.txt"
    original.write_bytes(b"retained outside bytes")
    os.link(original, folder / "payload")
    with pytest.raises(ValueError, match="single-link"):
        admit_root(root)
    assert original.read_bytes() == b"retained outside bytes"


def test_application_tree_is_refused_before_directory_creation(tmp_path):
    """A user's proposed profile cannot become a child of installed program files."""
    program = tmp_path / "program"
    program.mkdir()
    destination = program / "private"
    with pytest.raises(ValueError, match="outside application"):
        admit_root(destination, [program])
    assert not destination.exists()


def test_instance_lock_never_writes_through_a_link_and_second_owner_does_not_append(tmp_path):
    """Use the actual OS lock, retain its single byte and reject a second owner before writing."""
    path = tmp_path / "instance.lock"
    owner = InstanceLock(path)
    try:
        before = path.stat()
        with pytest.raises(ValueError, match="Another instance"):
            InstanceLock(path)
        owner.stream.seek(0)
        assert owner.stream.read() == b"1" and path.stat().st_mtime_ns == before.st_mtime_ns
    finally:
        owner.close()
    original = tmp_path / "outside"
    original.write_bytes(b"never write a lock byte here")
    linked = tmp_path / "linked.lock"
    os.link(original, linked)
    with pytest.raises(ValueError, match="single-link"):
        InstanceLock(linked)
    assert original.read_bytes() == b"never write a lock byte here"


@pytest.mark.parametrize("mode", ["root", "ancestor", "active", "encrypted"])
def test_real_directory_alias_is_refused_without_touching_target(tmp_path, mode):
    """Create actual junctions on Windows or symlinks on POSIX, then inspect the unmodified target."""
    target = tmp_path / "outside"
    target.mkdir()
    sentinel = target / "sentinel.txt"
    sentinel.write_bytes(b"ordinary unrelated directory contents")
    root = tmp_path / "private"
    if mode in {"active", "encrypted"}:
        root.mkdir()
        alias = root / mode
    else:
        alias = root
    if os.name == "nt":
        system = Path(os.environ["SystemRoot"]) / "System32/cmd.exe"
        subprocess.run(
            [str(system), "/d", "/c", "mklink", "/J", str(alias), str(target)],
            check=True,
            capture_output=True,
            timeout=10,
        )
    else:
        alias.symlink_to(target, target_is_directory=True)
    chosen = root / "nested" if mode == "ancestor" else root
    with pytest.raises(ValueError, match="aliases"):
        admit_root(chosen)
    assert sentinel.read_bytes() == b"ordinary unrelated directory contents"
    assert not (target / "nested").exists()
