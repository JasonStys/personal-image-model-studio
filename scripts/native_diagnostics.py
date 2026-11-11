"""Jason Stys: bounded escaped diagnostics from owned synthetic acceptance logs; never a validation waiver."""
# Index: declarations module.emit_tail@L13; variables MAX_TAIL@L10, path@L13, before@L16, descriptor@L19, stream@L26, opened@L27, raw@L35, record@L36, record@L38. Purposes/parameters: docs/code-map.json.

import json
import os
from pathlib import Path
import stat
import sys

MAX_TAIL = 16384


def emit_tail(path: Path) -> None:
    """Expose an actual failed child's bounded tail without terminal controls or replacing its original failure."""
    try:
        before = path.lstat()
        if path.is_symlink() or path.is_junction() or not stat.S_ISREG(before.st_mode):
            raise ValueError("ordinary owned log required")
        descriptor = os.open(
            path,
            os.O_RDONLY
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NONBLOCK", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
            ):
                raise ValueError("log identity changed")
            stream.seek(max(0, opened.st_size - MAX_TAIL))
            raw = stream.read(MAX_TAIL)
        record = {"owned_failed_log": path.name, "tail": raw.decode("utf-8", errors="replace")}
    except (OSError, ValueError) as error:
        record = {"owned_failed_log": path.name, "diagnostic_unavailable": type(error).__name__}
    print(json.dumps(record, ensure_ascii=True), file=sys.stderr, flush=True)
