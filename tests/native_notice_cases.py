"""Jason Stys: actual Tcl reads, exact upstream terms and platform notice failure boundaries. Symbol locations: generated source index."""
# Index: declarations module.interpreter@L15, module.test_actual_tcl_notice_reader_preserves_bytes_and_missing_identity@L25, module.test_exact_mac_version_uses_verbatim_upstream_notice_and_binds_digest@L43, module.test_unreviewed_platform_version_or_library_cannot_substitute_notice@L79, module.test_ubuntu_uses_actual_runtime_package_copyright_not_guessed_script_file@L88, test_ubuntu_uses_actual_runtime_package_copyright_not_guessed_script_file.installed@L99, module.test_present_invalid_runtime_notice_never_falls_back_to_other_terms@L112, module.test_mac_pre905_terms_require_exact_psf_sdk_recipe@L120, module.test_mac_pre905_changed_notice_is_rejected@L138; variables ROOT@L11, root@L17, interpreter@L25, tmp_path@L25, path@L27, raw@L28, raw@L35, interpreter@L44, kind@L44, tmp_path@L44, library@L47, file@L48, target@L49, raw@L52, source@L52, interpreter@L80, library@L80, system@L80, version@L80, interpreter@L89, kind@L89, monkeypatch@L89, tmp_path@L89, fixture@L92, actual@L94, calls@L95, library@L96, package_path@L97, interpreter@L99, path@L99, raw@L107, source@L107, interpreter@L112, tmp_path@L112, accepted@L121, interpreter@L121, monkeypatch@L121, python_version@L121, tmp_path@L121, library@L125, name@L126, raw@L130, source@L130, interpreter@L138, monkeypatch@L138, tmp_path@L138, path@L142, library@L144. Purposes/parameters: docs/code-map.json.

import tkinter
from pathlib import Path

import pytest

from scripts import native_notices as notices

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def interpreter():
    """The fresh subprocess has stable OS descriptors for this genuine Tcl interpreter's entire lifetime."""
    root = tkinter.Tk()
    root.withdraw()
    try:
        yield root.tk
    finally:
        root.destroy()


def test_actual_tcl_notice_reader_preserves_bytes_and_missing_identity(tmp_path, interpreter):
    """The genuine Tcl interpreter reads bytes, reports missing files and closes failed bounded reads."""
    path = tmp_path / "notice"
    raw = b"Verbatim controlled fixture copyright\n" * 8
    path.write_bytes(raw)
    assert notices.read_tcl_notice(interpreter, str(path)) == raw
    with pytest.raises(FileNotFoundError):
        notices.read_tcl_notice(interpreter, str(tmp_path / "missing"))
    with pytest.raises((tkinter.TclError, ValueError)):
        notices.read_tcl_notice(interpreter, str(tmp_path))
    for raw in (b"short", b"x" * 65537):
        path.write_bytes(raw)
        with pytest.raises(ValueError, match="byte bound"):
            notices.read_tcl_notice(interpreter, str(path))
        assert not interpreter.splitlist(interpreter.call("chan", "names", "file*"))


@pytest.mark.parametrize("kind", ["Tcl", "Tk"])
def test_exact_mac_version_uses_verbatim_upstream_notice_and_binds_digest(
    tmp_path, kind, interpreter
):
    """A missing installed notice has a narrowly source-bound alternative, never synthesized family terms."""
    library = f"/Library/Frameworks/Python.framework/Versions/3.14/Frameworks/{kind}.framework/Versions/9.0/Resources/Scripts"
    file = Path("licenses") / f"{kind.upper()}-9.0.4.txt"
    target = tmp_path / file
    target.parent.mkdir()
    target.write_bytes((ROOT / file).read_bytes())
    source, raw = notices.gui_notice(interpreter, tmp_path, kind, "9.0.4", library, "darwin")
    assert source.startswith("verbatim upstream9.0.4 notice: https://github.com/tcltk/")
    assert notices.UPSTREAM_904[kind][0] in source and raw == target.read_bytes()
    target.write_bytes(
        raw.replace(b"Software", b"Changed!", 1) if b"Software" in raw else raw + b"tamper"
    )
    with pytest.raises(ValueError, match="digest mismatch"):
        notices.gui_notice(interpreter, tmp_path, kind, "9.0.4", library, "darwin")


@pytest.mark.parametrize(
    "version,library,system",
    [
        (
            "9.0.5",
            "/Library/Frameworks/Python.framework/Versions/3.14/Frameworks/Tcl.framework/Versions/9.0/Resources/Scripts",
            "darwin",
        ),
        ("9.0.4", "/different/Resources/Scripts", "darwin"),
        (
            "9.0.4",
            "/Library/Frameworks/Python.framework/Versions/3.14/Frameworks/Tcl.framework/Versions/9.0/Resources/Scripts",
            "linux",
        ),
        ("8.6.14", "/unreviewed/tcl8.6", "linux"),
    ],
)
def test_unreviewed_platform_version_or_library_cannot_substitute_notice(
    version, library, system, interpreter
):
    """Different runtime versions/distributions fail closed despite a valid reviewed source notice being present."""
    with pytest.raises(ValueError, match="No reviewed notice"):
        notices.gui_notice(interpreter, ROOT, "Tcl", version, library, system)


@pytest.mark.parametrize("kind", ["Tcl", "Tk"])
def test_ubuntu_uses_actual_runtime_package_copyright_not_guessed_script_file(
    tmp_path, monkeypatch, kind, interpreter
):
    """The reviewed Ubuntu package path is explicit; actual fixture bytes pass the same bounded Tcl reader."""
    fixture = tmp_path / "copyright"
    fixture.write_bytes(b"Full controlled distribution copyright notice\n" * 6)
    actual = notices.read_tcl_notice
    calls = []
    library = f"/usr/share/tcltk/{kind.lower()}8.6"
    package_path = f"/usr/share/doc/lib{kind.lower()}8.6/copyright"

    def installed(interpreter, path):
        """Return only the pinned synthetic distribution fixture for mandatory notice validation."""
        calls.append(path)
        if path == package_path:
            return actual(interpreter, str(fixture))
        raise FileNotFoundError(path)

    monkeypatch.setattr(notices, "read_tcl_notice", installed)
    source, raw = notices.gui_notice(interpreter, tmp_path, kind, "8.6.14", library, "linux")
    assert calls == [library + "/license.terms", package_path]
    assert source == "actual Ubuntu runtime-package copyright" and raw == fixture.read_bytes()


def test_present_invalid_runtime_notice_never_falls_back_to_other_terms(tmp_path, interpreter):
    """A too-short actual library notice is a real error, even on a platform with another possible notice."""
    (tmp_path / "license.terms").write_bytes(b"invalid")
    with pytest.raises(ValueError, match="byte bound"):
        notices.gui_notice(interpreter, ROOT, "Tcl", "9.0.4", str(tmp_path), "darwin")


@pytest.mark.parametrize("python_version,accepted", [("3.14.10", True), ("3.14.11", False)])
def test_mac_pre905_terms_require_exact_psf_sdk_recipe(
    tmp_path, monkeypatch, interpreter, python_version, accepted
):
    """An actual9.0.5 patch string alone cannot authorize these prerelease source terms on future Python SDKs."""
    monkeypatch.setattr(notices.platform, "python_version", lambda: python_version)
    library = "/Library/Frameworks/Python.framework/Versions/3.14/Frameworks/Tk.framework/Versions/9.0/Resources/Scripts"
    name = "TK-9.0.5-pre-33904f039f48ed64.txt"
    (tmp_path / "licenses").mkdir()
    (tmp_path / "licenses" / name).write_bytes((ROOT / "licenses" / name).read_bytes())
    if accepted:
        source, raw = notices.gui_notice(interpreter, tmp_path, "Tk", "9.0.5", library, "darwin")
        assert "Tk9.0.5-pre-33904f039f48ed64" in source and "SHA25651ea4221" in source
        assert raw == (ROOT / "licenses" / name).read_bytes()
    else:
        with pytest.raises(ValueError, match="No reviewed notice"):
            notices.gui_notice(interpreter, tmp_path, "Tk", "9.0.5", library, "darwin")


def test_mac_pre905_changed_notice_is_rejected(tmp_path, monkeypatch, interpreter):
    """The exact old Mac recipe cannot bless modified notice bytes even when its displayed patchlevel matches."""
    monkeypatch.setattr(notices.platform, "python_version", lambda: "3.14.10")
    (tmp_path / "licenses").mkdir()
    path = tmp_path / "licenses/TK-9.0.5-pre-33904f039f48ed64.txt"
    path.write_bytes((ROOT / "licenses" / path.name).read_bytes() + b"tamper")
    library = "/Library/Frameworks/Python.framework/Versions/3.14/Frameworks/Tk.framework/Versions/9.0/Resources/Scripts"
    with pytest.raises(ValueError, match="prerelease Tk notice digest"):
        notices.gui_notice(interpreter, tmp_path, "Tk", "9.0.5", library, "darwin")
