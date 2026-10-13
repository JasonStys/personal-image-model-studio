"""Jason Stys: owner-restricted application data directory permissions, never system-wide policy changes."""
# Index: declarations module.protect_directory@L11; variables root@L11, root@L13, system@L24, flags@L25, identity@L26, rows@L33. Purposes/parameters: docs/code-map.json.

import csv
import io
import os
import subprocess
from pathlib import Path


def protect_directory(root: Path):
    """Restrict this checked application data root to its OS user, SYSTEM and administrators on Windows."""
    root = root.resolve(strict=True)
    if (
        root == Path(root.anchor)
        or root == Path.home().resolve()
        or root.is_symlink()
        or root.is_junction()
    ):
        raise ValueError("Refusing to change permissions on a broad or linked directory")
    if os.name != "nt":
        root.chmod(0o700)
        return
    system = Path(os.environ.get("SYSTEMROOT", r"C:\Windows")) / "System32"
    flags = subprocess.CREATE_NO_WINDOW
    identity = subprocess.run(
        [str(system / "whoami.exe"), "/user", "/fo", "csv", "/nh"],
        capture_output=True,
        text=True,
        check=True,
        creationflags=flags,
    )
    rows = list(csv.reader(io.StringIO(identity.stdout)))
    if len(rows) != 1 or len(rows[0]) != 2 or not rows[0][1].startswith("S-1-"):
        raise ValueError("Cannot verify this OS user's security identity")
    # Numeric SID grants avoid translated group names. No recursion: descendants
    # created by the application inherit this protected root's owner-only ACL.
    subprocess.run(
        [
            str(system / "icacls.exe"),
            str(root),
            "/inheritancelevel:r",
            "/grant:r",
            "*" + rows[0][1] + ":(OI)(CI)F",
            "*S-1-5-18:(OI)(CI)F",
            "*S-1-5-32-544:(OI)(CI)F",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
        creationflags=flags,
    )
