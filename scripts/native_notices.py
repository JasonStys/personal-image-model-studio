"""Jason Stys: collect real runtime license notices, including DLL-embedded Tcl/Tk9 libraries. Symbol locations: generated source index."""
# Index: declarations module.notice_paths@L22, module.read_tcl_notice@L36, module.gui_notice@L57, module.collect@L110; variables UPSTREAM_904@L10, info@L22, path@L26, part@L30, interpreter@L36, path@L36, channel@L41, code@L43, raw@L48, raw@L51, interpreter@L57, kind@L57, library@L57, root@L57, system@L57, version@L57, system@L59, path@L72, framework@L74, commit@L77, expected@L77, stream@L78, raw@L79, stream@L95, raw@L96, root@L110, window@L114, versions@L117, value@L121, blocks@L123, kind@L124, library@L124, version@L124, provenance@L128, raw@L128, project@L139, requested@L140, item@L141, pending@L141, selected@L142, name@L144, info@L148, raw@L149, requirement@L150, name@L153, info@L154, files@L155, path@L158, stream@L159, raw@L160, raw@L167, title@L167. Purposes/parameters: docs/code-map.json.

import hashlib
import platform
import sys
from importlib.metadata import distribution
from pathlib import Path

UPSTREAM_904 = {
    "Tcl": (
        "c655b4770b1d6d32a8cbffd6cef59db6029fe19e",
        "c0a69a2bfd757361ec7e6143973b103c90409316b49e9c88db26ad6388e79f16",
    ),
    "Tk": (
        "584f8fcf62c320d7c341e77171188cb4d79c3725",
        "2cde822b93ca16ae535c954b7dfe658b4ad10df2a193628d1b358f1765e8b198",
    ),
}


def notice_paths(info):
    """Keep actual component terms, including LICENSE.APACHE forms, without compiled author-list bytecode."""
    return [
        info.locate_file(path)
        for path in info.files or []
        if Path(path).suffix.lower() not in {".py", ".pyc", ".pyo"}
        and "__pycache__" not in Path(path).parts
        and (
            "licenses" in {part.lower() for part in Path(path).parts}
            or Path(path).name.upper().startswith(("LICENSE", "COPYING", "NOTICE"))
        )
    ]


def read_tcl_notice(interpreter, path: str) -> bytes:
    """Read actual filesystem/zipfs bytes through Tcl; only genuine ENOENT permits a reviewed alternative."""
    import tkinter

    try:
        channel = interpreter.call("open", path, "rb")
    except tkinter.TclError as error:
        code = interpreter.call("set", "errorCode")
        if tuple(interpreter.splitlist(code))[:2] == ("POSIX", "ENOENT"):
            raise FileNotFoundError(path) from error
        raise ValueError(f"GUI runtime notice open failed: {code!r}") from error
    try:
        raw = interpreter.call("read", channel, 65537)
    finally:
        interpreter.call("close", channel)
    raw = raw.encode("utf-8") if isinstance(raw, str) else raw
    if not isinstance(raw, bytes) or not 100 <= len(raw) <= 65536:
        raise ValueError("Actual GUI runtime license is missing or exceeds its byte bound")
    return raw


def gui_notice(interpreter, root: Path, kind: str, version: str, library: str, system=None):
    """Prefer actual runtime notices; explicit Ubuntu copyright and exact upstream Mac904 terms are reviewed alternatives."""
    system = sys.platform if system is None else system
    try:
        return "actual loaded runtime library notice", read_tcl_notice(
            interpreter, library + "/license.terms"
        )
    except FileNotFoundError:
        pass
    if (
        system == "linux"
        and version.startswith("8.6.")
        and library == f"/usr/share/tcltk/{kind.lower()}8.6"
    ):
        # Ubuntu's actual runtime package installs its full notice under /usr/share/doc, not the script library.
        path = f"/usr/share/doc/lib{kind.lower()}8.6/copyright"
        return "actual Ubuntu runtime-package copyright", read_tcl_notice(interpreter, path)
    framework = f"/Library/Frameworks/Python.framework/Versions/3.14/Frameworks/{kind}.framework/Versions/9.0/Resources/Scripts"
    if system == "darwin" and version == "9.0.4" and library == framework and kind in UPSTREAM_904:
        # Unix Tcl/Tk installation omits license.terms. Retain verbatim source terms for this exact loaded version.
        commit, expected = UPSTREAM_904[kind]
        with (root / f"licenses/{kind.upper()}-9.0.4.txt").open("rb") as stream:
            raw = stream.read(65537)
        if not 100 <= len(raw) <= 65536 or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("Exact upstream Tcl/Tk9.0.4 notice digest mismatch")
        return (
            f"verbatim upstream9.0.4 notice: https://github.com/tcltk/{kind.lower()}/blob/{commit}/license.terms",
            raw,
        )
    if (
        system == "darwin"
        and kind == "Tk"
        and version == "9.0.5"
        and library == framework
        and platform.python_version() == "3.14.10"
    ):
        # PSF's exact3.14.10 Mac recipe uses this prerelease Tk to fix the macOS dialog hang.
        # Archive SHA51ea4221... was independently verified; do not label this a stable9.0.5 release.
        with (root / "licenses/TK-9.0.5-pre-33904f039f48ed64.txt").open("rb") as stream:
            raw = stream.read(65537)
        if not 100 <= len(raw) <= 65536 or hashlib.sha256(raw).hexdigest() != UPSTREAM_904["Tk"][1]:
            raise ValueError("Exact PSF Mac3.14.10 prerelease Tk notice digest mismatch")
        return (
            "verbatim Tk9.0.5-pre-33904f039f48ed64 source notice from PSF Mac3.14.10 recipe: "
            "https://core.tcl-lang.org/tk/tarball/33904f039f48ed64/tk9.0.5.tar.gz "
            "archive SHA25651ea4221578b994ec7768df9165c6682eef487a148a15003a74135c33cab35b5",
            raw,
        )
    raise ValueError(
        f"No reviewed notice source for the actual loaded GUI runtime: {kind} {version} {library}"
    )


def collect(root: Path) -> tuple[dict, bytes]:
    """Retain every locked Python runtime notice and the actual loaded GUI runtime's bounded license bytes."""
    import tkinter

    window = tkinter.Tk()
    window.withdraw()
    try:
        versions = {
            "tcl_version": str(window.tk.call("info", "patchlevel")),
            "tk_version": str(window.tk.call("package", "require", "Tk")),
        }
        if not all(value.startswith(("8.6.", "9.0.")) for value in versions.values()):
            raise ValueError("Review a different Tcl/Tk family before freezing")
        blocks = []
        for kind, version, library in [
            ("Tcl", versions["tcl_version"], window.tk.call("info", "library")),
            ("Tk", versions["tk_version"], window.tk.eval("set tk_library")),
        ]:
            provenance, raw = gui_notice(window.tk, root, kind, version, str(library))
            blocks.append((kind + " " + version + " — " + provenance, raw))
    finally:
        window.destroy()
    blocks.append(("Authored project — MIT", (root / "LICENSE").read_bytes()))
    blocks.append(("Python3.14.10 runtime license", (root / "licenses/PYTHON.txt").read_bytes()))
    import tomllib

    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name

    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    requested = project["dependencies"] + project["optional-dependencies"]["cpu"]
    pending = [Requirement(item).name for item in requested] + ["pyinstaller"]
    selected = set()
    while pending:
        name = canonicalize_name(pending.pop())
        if name in selected:
            continue
        selected.add(name)
        info = distribution(name)
        for raw in info.requires or []:
            requirement = Requirement(raw)
            if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
                pending.append(requirement.name)
    for name in sorted(selected):
        info = distribution(name)
        files = notice_paths(info)
        if not files:
            raise ValueError("Runtime license notice missing: " + name)
        for path in files:
            with path.open("rb") as stream:
                raw = stream.read(2 * 1024 * 1024 + 1)
            if not 0 < len(raw) <= 2 * 1024 * 1024:
                raise ValueError("Runtime license exceeds its byte bound")
            if b"\0" in raw:
                raise ValueError("Runtime notice contains binary data")
            raw.decode("utf-8")
            blocks.append((name + " — " + path.name, raw))
    return versions, b"\n\n".join(title.encode("utf-8") + b"\n" + raw for title, raw in blocks)
