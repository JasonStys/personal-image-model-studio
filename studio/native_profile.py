"""Jason Stys: inspect private account paths before writes without resetting recovery data.
# Index: declarations module.is_alias@L25, module.regular@L32, module.directory_chain@L43, module.ordinary_tree@L54, module.admit_root@L79; variables FILES@L13, DIRECTORIES@L21, MAX_ENTRIES@L22, info@L25, path@L32, info@L35, path@L43, current@L45, info@L47, path@L54, entries@L58, pending@L58, current@L60, children@L61, child@L62, entries@L63, info@L68, path@L79, program_roots@L79, path@L81, programs@L84, programs@L86, program@L87, name@L90, name@L92. Purposes/parameters: docs/code-map.json.

Declaration and variable locations are generated in docs/code-map.json.
These static admission checks do not isolate malicious code running as the same OS user.
"""

import os
import stat
import sys
from pathlib import Path

FILES = (
    "instance.lock",
    "accounts.sqlite",
    "accounts.sqlite-journal",
    "accounts.sqlite-wal",
    "accounts.sqlite-shm",
    "active-owner.json",
)
DIRECTORIES = ("active", "encrypted")
MAX_ENTRIES = 60000


def is_alias(info) -> bool:
    """Treat every Windows reparse attribute and symbolic link as an unsupported alias."""
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def regular(path: Path):
    """Inspect an existing member without following it; ordinary recovery files remain intact."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if is_alias(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("Private account state must be ordinary unlinked single-link files")
    return info


def directory_chain(path: Path) -> None:
    """Check lexical ancestors before mkdir, resolution or permission changes can follow an alias."""
    for current in reversed((path, *path.parents)):
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if is_alias(info) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("Private account directories cannot use aliases or special files")


def ordinary_tree(path: Path) -> None:
    """Inspect existing recovery/archive entries with a bounded iterative metadata walk, without reading contents."""
    if not path.exists():
        return
    pending, entries = [path], 0
    while pending:
        current = pending.pop()
        with os.scandir(current) as children:
            for child in children:
                entries += 1
                if entries > MAX_ENTRIES:
                    raise ValueError("Private account recovery tree exceeds its inspection limit")
                # Windows DirEntry.stat may report cached zero link counts;
                # ask the OS for actual lstat metadata before deciding ownership.
                info = Path(child.path).lstat()
                if is_alias(info):
                    raise ValueError("Private recovery and archive entries cannot be aliases")
                if stat.S_ISDIR(info.st_mode):
                    pending.append(Path(child.path))
                elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise ValueError(
                        "Private recovery and archive files must be ordinary single-link files"
                    )


def admit_root(path: Path, program_roots=()) -> Path:
    """Admit one dedicated external local profile before its existing manager creates or opens any state."""
    path = Path(os.path.abspath(path))
    if path == Path(path.anchor) or str(path).startswith("\\\\"):
        raise ValueError("Choose a dedicated local account data directory")
    programs = [Path(__file__).resolve().parents[1], *program_roots]
    if getattr(sys, "frozen", False):
        programs += [Path(sys.executable).parent, Path(sys._MEIPASS)]
    if any(path.is_relative_to(Path(os.path.abspath(program))) for program in programs):
        raise ValueError("Private account data must stay outside application files")
    directory_chain(path)
    for name in FILES:
        regular(path / name)
    for name in DIRECTORIES:
        directory_chain(path / name)
        ordinary_tree(path / name)
    return path
