"""Offline public-data parsing/raster/cleanup tests; CI never downloads a category or account art."""
# Index: declarations module.drawing@L12, module.test_raster_discards_identity_and_preserves_geometry@L22, module.test_invalid_coordinates_fail_closed@L48, module.test_ndjson_limits@L59, module.test_stream_aggregate_budgets@L66, module.test_download_is_fixed_bounded_and_atomic@L74, test_download_is_fixed_bounded_and_atomic.handler@L78, module.test_insufficient_or_unavailable_sample_leaves_no_output@L106; variables category@L12, index@L12, item@L24, first@L25, second@L27, patch@L48, body@L59, budget@L66, body@L68, deadline@L69, tmp_path@L74, requests@L76, request@L78, category@L81, offset@L82, body@L83, index@L85, output@L91, summary@L92, request@L95, request@L96, sidecar@L97, status@L106, tmp_path@L106, output@L108, request@L111. Purposes/parameters: docs/code-map.json.

import json
import time

import httpx
import pytest
from scripts.prepare_quickdraw import prepare, raster, records, MAX_BYTES


def drawing(category="sun", index=0):
    """Small generated XY fixture, not a redistributed participant drawing."""
    return {
        "word": category,
        "recognized": True,
        "countrycode": "discarded",
        "drawing": [[[0, index * 4, 255], [0, 128, 255]]],
    }


def test_raster_discards_identity_and_preserves_geometry():
    """Pixels depend on strokes, not participant attributes; unrecognized drawings are not retained."""
    item = drawing()
    with raster(item, "sun") as first:
        item["countrycode"] = "another-value"
        with raster(item, "sun") as second:
            assert first.size == (32, 32)
            assert first.tobytes() == second.tobytes()
            assert first.getextrema() != ((255, 255),) * 3
    item["recognized"] = False
    assert raster(item, "sun") is None


@pytest.mark.parametrize(
    "patch",
    [
        {"word": "other"},
        {"recognized": "yes"},
        {"drawing": None},
        {"drawing": [[[0], [0, 2]]]},
        {"drawing": [[[0, float("nan")], [0, 255]]]},
        {"drawing": [[[0, 256], [0, 255]]]},
        {"drawing": [[[False, 255], [0, 255]]]},
        {"drawing": [[[0, 1], [0, 1]]]},
    ],
)
def test_invalid_coordinates_fail_closed(patch):
    """Malformed/nonfinite/unbounded or degenerate source coordinates cannot reach image allocation."""
    with pytest.raises(ValueError):
        raster({**drawing(), **patch}, "sun")


@pytest.mark.parametrize(
    "body",
    [b"x" * 65537 + b"\n", b"\xff\n", b"{bad}\n"],
    ids=["oversized-line", "invalid-utf8", "invalid-json"],
)
def test_ndjson_limits(body):
    """Reject oversized/undecodable source lines with bounded errors."""
    with pytest.raises(ValueError):
        list(records(httpx.Response(200, content=body), time.monotonic() + 5))


@pytest.mark.parametrize("budget", ["bytes", "time"])
def test_stream_aggregate_budgets(budget):
    """Even individually valid source lines cannot exceed total bytes or the monotonic deadline."""
    body = (b'{"bounded":"' + b"x" * 20000 + b'"}\n') * 106
    deadline = time.monotonic() + 5 if budget == "bytes" else time.monotonic() - 1
    with pytest.raises(ValueError, match="byte/time budget"):
        list(records(httpx.Response(200, content=body), deadline))


def test_download_is_fixed_bounded_and_atomic(tmp_path):
    """Use generated fixtures to verify range bounds, deduplication, attribution and atomic publication."""
    requests = []

    def handler(request):
        """Serve deterministic category fixtures; no network or real artwork is involved."""
        requests.append(request)
        category = request.url.path.rsplit("/", 1)[1].split(".")[0]
        offset = {"sun": 0, "flower": 20, "fish": 40}[category]
        body = (
            b"\n".join(
                json.dumps(drawing(category, offset + index)).encode() for index in range(20)
            )
            + b"\n"
        )
        return httpx.Response(206, content=body)

    output = tmp_path / "sample"
    summary = prepare(output, 16, httpx.MockTransport(handler))
    assert summary["total"] == 48
    assert len(list(output.glob("*.png"))) == 48
    assert all(request.headers["range"] == f"bytes=0-{MAX_BYTES - 1}" for request in requests)
    assert all(request.url.host == "storage.googleapis.com" for request in requests)
    sidecar = json.loads(next(output.glob("sun-*.json")).read_text())
    assert "CC BY 4.0" in sidecar["license"]
    assert "countrycode" not in sidecar
    assert "modifications" in sidecar
    with pytest.raises(ValueError, match="new sample directory"):
        prepare(output, 16, httpx.MockTransport(handler))


@pytest.mark.parametrize("status", [200, 302, 429])
def test_insufficient_or_unavailable_sample_leaves_no_output(tmp_path, status):
    """Empty input/redirect/provider limits cannot leave a partial sample or trigger a bypass."""
    output = tmp_path / "sample"
    with pytest.raises(ValueError):
        prepare(
            output, 16, httpx.MockTransport(lambda request: httpx.Response(status, content=b""))
        )
    assert not list(tmp_path.iterdir())
