"""Jason Stys: actual package bytes, altered UI, bounded resources and runtime mismatch regressions."""
# Index: declarations module.manifest@L20, module.write_manifest@L76, module.test_real_built_resource_inventory_and_runtime_identity@L81, module.test_changed_package_is_refused_without_profile_creation@L107, module.test_descriptor_bounds_and_inventory_budget_are_enforced@L135, module.test_ambiguous_source_metadata_and_missing_entry_are_refused@L152, module.test_development_identity_does_not_claim_frozen_provenance@L163; variables root@L20, observed@L29, name@L30, raw@L31, library_name@L33, actual@L38, actual@L40, actual@L45, raw@L54, root@L76, value@L76, monkeypatch@L81, tmp_path@L81, value@L83, monkeypatch@L107, mutation@L107, tmp_path@L107, value@L109, monkeypatch@L135, tmp_path@L135, source@L137, tmp_path@L152, monkeypatch@L163, tmp_path@L163, interpreter@L169. Purposes/parameters: docs/code-map.json.

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import sys
import sysconfig
from pathlib import Path

import pytest

from studio import __version__ as VERSION
from studio.native_identity import bounded_bytes, ui_files, unique_pairs, verify_bundle, verify_gui


def manifest(root: Path) -> dict:
    """Create synthetic metadata around real UI fixture bytes and the actual interpreter library when supported."""
    (root / "dist/assets").mkdir(parents=True)
    (root / "dist/index.html").write_text("<!doctype html><html><body>Synthetic UI</body></html>")
    (root / "dist/assets/app.js").write_text("document.body.dataset.example = 'synthetic';")
    (root / "LICENSE").write_text("Synthetic authored license fixture\n")
    (root / "NATIVE_NOTICES.txt").write_text(
        "Synthetic notice fixture; no legal clearance asserted\n"
    )
    observed = ui_files(root)
    for name in ("LICENSE", "NATIVE_NOTICES.txt"):
        raw = (root / name).read_bytes()
        observed[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    library_name = {"win32": "python314.dll", "darwin": "Python", "linux": "libpython3.14.so.1.0"}[
        sys.platform
    ]
    if sys.version_info[:3] == (3, 14, 10):
        if sys.platform == "win32":
            actual = Path(sys.base_prefix) / library_name
        elif sys.platform == "darwin":
            actual = (
                Path(sysconfig.get_config_var("PYTHONFRAMEWORKPREFIX"))
                / "Python.framework/Versions/3.14/Python"
            )
        else:
            actual = Path(sysconfig.get_config_var("LIBDIR")) / library_name
        assert actual.is_file(), (
            "The actual pinned runtime library is required for this platform acceptance"
        )
        shutil.copy2(actual, root / library_name)
    else:
        # Source validation still supports3.12; it must refuse an attempted
        # frozen identity for that runtime, before this inert placeholder is read.
        (root / library_name).write_bytes(b"inert unsupported-runtime fixture")
    raw = (root / library_name).read_bytes()
    return {
        "schema": 1,
        "product": "personal-image-model-studio",
        "version": VERSION,
        "source": "a" * 40,
        "source_dirty": False,
        "python": platform.python_version(),
        "platform": sys.platform,
        "machine": platform.machine(),
        "runtime_library": {
            "file": library_name,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "sdk_sha256": hashlib.sha256(raw).hexdigest(),
        },
        "tcl_version": "9.0.4",
        "tk_version": "9.0.4",
        "resources": observed,
    }


def write_manifest(root, value):
    """Write exact finite JSON fixture bytes without any application account data."""
    (root / "NATIVE_SOURCE.json").write_text(json.dumps(value))


def test_real_built_resource_inventory_and_runtime_identity(tmp_path, monkeypatch):
    """The genuine pinned library passes; an older source-validation interpreter is explicitly refused."""
    value = manifest(tmp_path)
    write_manifest(tmp_path, value)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    if sys.version_info[:3] == (3, 14, 10):
        assert verify_bundle(tmp_path) == value
    else:
        with pytest.raises(ValueError, match="runtime identity"):
            verify_bundle(tmp_path)


@pytest.mark.parametrize(
    "mutation",
    [
        "ui_bytes",
        "unknown_ui",
        "notice_bytes",
        "library_bytes",
        "version",
        "source",
        "machine_type",
        "unknown_metadata",
        "library_path",
    ],
)
def test_changed_package_is_refused_without_profile_creation(tmp_path, monkeypatch, mutation):
    """Real resource/identity changes never reach account-profile initialization."""
    value = manifest(tmp_path)
    if mutation == "ui_bytes":
        (tmp_path / "dist/assets/app.js").write_text("changed executable UI bytes")
    elif mutation == "unknown_ui":
        (tmp_path / "dist/unexpected.js").write_text("unexpected UI module")
    elif mutation == "notice_bytes":
        (tmp_path / "NATIVE_NOTICES.txt").write_text("replaced notice")
    elif mutation == "library_bytes":
        (tmp_path / value["runtime_library"]["file"]).write_bytes(b"changed runtime")
    elif mutation == "library_path":
        value["runtime_library"]["file"] = "../outside.dll"
    elif mutation == "version":
        value["version"] = "999.0.0"
    elif mutation == "source":
        value["source"] = "unknown source"
    elif mutation == "machine_type":
        value["machine"] = None
    else:
        value["unexpected"] = True
    write_manifest(tmp_path, value)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    with pytest.raises(ValueError):
        verify_bundle(tmp_path)
    assert not (tmp_path / "private-accounts.db").exists()


def test_descriptor_bounds_and_inventory_budget_are_enforced(tmp_path, monkeypatch):
    """Actual oversized files and too many tree entries fail without unbounded reads or traversal."""
    source = tmp_path / "large.txt"
    source.write_bytes(b"abcd")
    with pytest.raises(ValueError, match="bound"):
        bounded_bytes(source, 3)
    assert bounded_bytes(source, 4) == b"abcd"
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist/index.html").write_text("fixture")
    (tmp_path / "dist/extra.js").write_text("fixture")
    monkeypatch.setattr("studio.native_identity.MAX_UI_FILES", 1)
    with pytest.raises(ValueError, match="inventory"):
        ui_files(tmp_path)
    with pytest.raises(ValueError, match="ordinary"):
        bounded_bytes(tmp_path / "dist", 16)


def test_ambiguous_source_metadata_and_missing_entry_are_refused(tmp_path):
    """Duplicate identities and a missing actual HTML entry cannot masquerade as valid package evidence."""
    with pytest.raises(ValueError, match="Duplicate"):
        json.loads('{"version":"1.0.0","version":"2.0.0"}', object_pairs_hook=unique_pairs)
    with pytest.raises(ValueError, match="unavailable"):
        ui_files(tmp_path)
    (tmp_path / "dist").mkdir()
    with pytest.raises(ValueError, match="entry point"):
        ui_files(tmp_path)


def test_development_identity_does_not_claim_frozen_provenance(tmp_path, monkeypatch):
    """Source checkout is explicitly development; a real Tcl interpreter mismatch fails closed."""
    import tkinter

    monkeypatch.delattr(sys, "frozen", raising=False)
    assert verify_bundle(tmp_path) == {"source": "development", "source_dirty": True}
    interpreter = tkinter.Tcl()
    verify_gui(interpreter, {"source": "development"})
    with pytest.raises(ValueError, match="GUI runtime identity"):
        verify_gui(
            interpreter,
            {"source": "a" * 40, "tcl_version": "impossible", "tk_version": "impossible"},
        )
