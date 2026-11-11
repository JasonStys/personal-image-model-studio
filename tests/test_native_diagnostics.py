"""Jason Stys: real bounded diagnostic files cannot execute terminal controls or replace failed acceptance."""
# Index: declarations module.test_actual_large_log_tail_is_bounded_escaped_and_file_unchanged@L11, module.test_missing_or_special_diagnostic_never_masks_the_original_failure@L24, module.test_real_alias_diagnostic_is_not_read@L31; variables capsys@L11, tmp_path@L11, path@L13, original@L14, raw@L17, value@L18, capsys@L24, tmp_path@L24, path@L26, capsys@L31, tmp_path@L31, original@L33, alias@L35, raw@L38. Purposes/parameters: docs/code-map.json.

import json
import os
from pathlib import Path

from scripts.native_diagnostics import MAX_TAIL, emit_tail


def test_actual_large_log_tail_is_bounded_escaped_and_file_unchanged(tmp_path: Path, capsys):
    """Retain the meaningful last bytes while earlier contents/control sequences remain unprinted as controls."""
    path = tmp_path / "failed-child.log"
    original = b"PRIVATE-PREFIX" + b"x" * (MAX_TAIL * 3) + b"\x1b[31m\nactual-tail"
    path.write_bytes(original)
    emit_tail(path)
    raw = capsys.readouterr().err
    value = json.loads(raw)
    assert value["tail"].endswith("actual-tail") and "PRIVATE-PREFIX" not in raw
    assert len(value["tail"].encode()) <= MAX_TAIL and "\x1b" not in raw
    assert path.read_bytes() == original


def test_missing_or_special_diagnostic_never_masks_the_original_failure(tmp_path, capsys):
    """An unavailable diagnostic cannot create success or raise over the real child error."""
    for path in (tmp_path / "missing.log", tmp_path):
        emit_tail(path)
        assert "diagnostic_unavailable" in json.loads(capsys.readouterr().err)


def test_real_alias_diagnostic_is_not_read(tmp_path, capsys):
    """Refuse actual hard-linked logs so diagnostics cannot borrow unrelated file content."""
    original = tmp_path / "retained.txt"
    original.write_bytes(b"unrelated-retained-sentinel")
    alias = tmp_path / "alias.log"
    os.link(original, alias)
    emit_tail(alias)
    raw = capsys.readouterr().err
    assert "unrelated-retained-sentinel" not in raw
    assert "diagnostic_unavailable" in json.loads(raw)
    assert original.read_bytes() == b"unrelated-retained-sentinel"
