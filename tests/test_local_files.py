"""Jason Stys: actual descriptor, bounds, alias and FIFO evidence for local artifact admission."""
# Index: declarations module.test_one_descriptor_reads_original_bytes_after_path_replacement@L16, test_one_descriptor_reads_original_bytes_after_path_replacement.replace_after_descriptor_validation@L24, module.test_growth_is_capped_from_actual_descriptor_bytes_for_json_and_digest@L41, test_growth_is_capped_from_actual_descriptor_bytes_for_json_and_digest.grow_after_stat@L47, module.test_real_hardlink_and_directory_refused_without_mutating_outside_bytes@L62, module.test_regular_to_fifo_swap_is_bounded_by_nonblocking_descriptor_admission@L83, module.test_valid_digest_json_and_invalid_byte_limits@L111, module.test_seekable_zip_view_caps_grown_end_and_parser_read_requests@L122, module.test_stream_construction_failure_cannot_close_a_reused_owned_descriptor@L141, test_stream_construction_failure_cannot_close_a_reused_owned_descriptor.fail_after_creation@L149; variables monkeypatch@L16, tmp_path@L16, replacement@L18, source@L18, fdopen@L21, blocked@L22, descriptor@L24, mode@L24, options@L24, stream@L26, monkeypatch@L41, tmp_path@L41, source@L43, fdopen@L45, descriptor@L47, mode@L47, options@L47, stream@L49, writer@L50, tmp_path@L62, alias@L64, source@L64, read@L67, tmp_path@L83, source@L85, program@L87, result@L101, tmp_path@L111, source@L113, limit@L117, tmp_path@L122, source@L124, stream@L126, writer@L132, monkeypatch@L141, tmp_path@L141, source@L143, unrelated@L143, fdopen@L146, created@L147, descriptor@L149, mode@L149, options@L149, stream@L151, other@L153, original@L161, other@L161, ownership@L161, _original@L166, _ownership@L166, other@L166. Purposes/parameters: docs/code-map.json.

from __future__ import annotations

import hashlib
import os
import subprocess
import sys

import pytest

from studio import files


def test_one_descriptor_reads_original_bytes_after_path_replacement(tmp_path, monkeypatch):
    """Replacement after descriptor validation cannot redirect the read to the new path content."""
    source, replacement = tmp_path / "source", tmp_path / "replacement"
    source.write_bytes(b"admitted original")
    replacement.write_bytes(b"different replacement")
    fdopen = os.fdopen
    blocked = []

    def replace_after_descriptor_validation(descriptor, mode, **options):
        """Interleave actual replacement immediately before yielding the already-open descriptor."""
        stream = fdopen(descriptor, mode, **options)
        try:
            os.replace(replacement, source)
        except PermissionError:
            if os.name != "nt":
                stream.close()
                raise
            blocked.append(True)
        return stream

    monkeypatch.setattr(files.os, "fdopen", replace_after_descriptor_validation)
    assert files.regular_bytes(source, 64) == b"admitted original"
    assert source.read_bytes() == (b"admitted original" if blocked else b"different replacement")


def test_growth_is_capped_from_actual_descriptor_bytes_for_json_and_digest(tmp_path, monkeypatch):
    """Growth after fstat is refused by actual read accounting, not trusted metadata size."""
    source = tmp_path / "source"
    source.write_bytes(b"12")
    fdopen = os.fdopen

    def grow_after_stat(descriptor, mode, **options):
        """Append real bytes after size admission while preserving the same underlying file."""
        stream = fdopen(descriptor, mode, **options)
        with source.open("ab") as writer:
            writer.write(b"3456789")
        return stream

    monkeypatch.setattr(files.os, "fdopen", grow_after_stat)
    with pytest.raises(ValueError, match="limit"):
        files.regular_bytes(source, 4)
    source.write_bytes(b"12")
    with pytest.raises(ValueError, match="limit"):
        files.digest(source, 4)


def test_real_hardlink_and_directory_refused_without_mutating_outside_bytes(tmp_path):
    """Real NTFS/POSIX links and wrong entry types fail before JSON/image/digest or atomic publication."""
    source, alias = tmp_path / "original", tmp_path / "alias"
    source.write_bytes(b"retained")
    os.link(source, alias)
    for read in (
        lambda: files.regular_bytes(alias, 100),
        lambda: files.digest(alias),
        lambda: files.atomic_json(alias, {"new": True}),
    ):
        with pytest.raises(ValueError):
            read()
    with pytest.raises((ValueError, IsADirectoryError, PermissionError)):
        files.regular_bytes(tmp_path, 100)
    assert source.read_bytes() == alias.read_bytes() == b"retained"


@pytest.mark.skipif(
    os.name == "nt",
    reason="Actual no-writer FIFO open requires POSIX; real Windows hardlink/descriptor cases are separate",
)
def test_regular_to_fifo_swap_is_bounded_by_nonblocking_descriptor_admission(tmp_path):
    """A real FIFO inserted at open cannot wait for a writer or pass as a regular JSON source."""
    source = tmp_path / "source"
    source.write_bytes(b"{}")
    program = """
import os,sys
from pathlib import Path
from studio import files
path=Path(sys.argv[1]);original=files.os.open

def swap(value,flags):
 path.unlink();os.mkfifo(path)
 return original(value,flags)
files.os.open=swap
try:files.regular_bytes(path,100)
except ValueError:print('nonregular-refused')
else:raise SystemExit(2)
"""
    result = subprocess.run(
        [sys.executable, "-c", program, str(source)],
        capture_output=True,
        text=True,
        timeout=2,
        check=False,
    )
    assert result.returncode == 0 and result.stdout.strip() == "nonregular-refused"


def test_valid_digest_json_and_invalid_byte_limits(tmp_path):
    """Valid small files remain usable while booleans/unbounded limits and invalid JSON fail closed."""
    source = tmp_path / "source"
    source.write_bytes(b'{"value":2}')
    assert files.digest(source) == hashlib.sha256(source.read_bytes()).hexdigest()
    assert files.read_json(source) == {"value": 2}
    for limit in (True, 0, -1, 20 * 1024**3 + 1):
        with pytest.raises(ValueError):
            files.regular_bytes(source, limit)


def test_seekable_zip_view_caps_grown_end_and_parser_read_requests(tmp_path):
    """The actual descriptor view refuses out-of-cap ZIP-style seeks/reads rather than trusting initial size."""
    source = tmp_path / "source"
    source.write_bytes(b"1234")
    with files.regular_stream(source, 4) as stream:
        assert stream.seek(0, os.SEEK_END) == 4
        assert stream.seek(0) == 0 and stream.read(1000000) == b"1234"
        assert stream.seek(0) == 0 and stream.read() == b"1234"
        with pytest.raises(ValueError, match="limit"):
            stream.seek(5)
        with source.open("ab") as writer:
            writer.write(b"5")
        with pytest.raises(ValueError, match="limit"):
            stream.seek(0, os.SEEK_END)
        stream.seek(0)
        with pytest.raises(ValueError, match="limit"):
            stream.read()


def test_stream_construction_failure_cannot_close_a_reused_owned_descriptor(tmp_path, monkeypatch):
    """A wrapping failure after stream creation cannot transfer ownership then close somebody else's descriptor."""
    source, unrelated = tmp_path / "source", tmp_path / "unrelated"
    source.write_bytes(b"{}")
    unrelated.write_bytes(b"retained unrelated bytes")
    fdopen = os.fdopen
    created = []

    def fail_after_creation(descriptor, mode, **options):
        """Inject a real stream creation/close and open a second real owned file before failing."""
        stream = fdopen(descriptor, mode, **options)
        stream.close()
        other = os.open(unrelated, os.O_RDONLY | getattr(os, "O_BINARY", 0))
        created.append((descriptor, other, options.get("closefd")))
        raise OSError("Injected stream construction failure")

    monkeypatch.setattr(files.os, "fdopen", fail_after_creation)
    try:
        with pytest.raises(OSError, match="Injected"):
            files.regular_bytes(source, 100)
        original, other, ownership = created[0]
        assert ownership is False and original != other
        assert os.fstat(other).st_size == len(b"retained unrelated bytes")
        assert os.read(other, 100) == b"retained unrelated bytes"
    finally:
        for _original, other, _ownership in created:
            try:
                os.close(other)
            except OSError:
                pass
    assert source.read_bytes() == b"{}" and unrelated.read_bytes() == b"retained unrelated bytes"
