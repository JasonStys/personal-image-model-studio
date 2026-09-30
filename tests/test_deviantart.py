"""Offline official-API contract fixtures; these tests never log in, fetch real art or claim live access."""

# Index: declarations module.connector_fixture@L15, connector_fixture.handler@L21, module.test_pkce_one_use_expiry_and_no_secrets@L68, module.test_expired_oauth_state_does_not_exchange@L95, module.test_bounded_gallery_preserves_caption_and_origin@L106, module.test_import_fails_closed_and_leaves_no_dataset@L134, module.test_no_arbitrary_image_url@L157, module.test_description_is_inert_and_bounded@L163, module.test_rate_limit_error_does_not_echo_tokens@L169; variables kind@L15, requests@L17, stream@L18, request@L21, path@L24, item@L32, item@L43, clock@L61, connector@L62, result@L63, query@L64, tmp_path@L68, clock@L70, connector@L70, query@L70, requests@L70, verifier@L71, expected@L72, body@L82, clock@L97, connector@L97, query@L97, requests@L97, flagged@L106, kind@L106, tmp_path@L106, _@L108, connector@L108, query@L108, requests@L108, output@L110, manifest@L111, asset@L116, request@L116, path@L120, kind@L134, pattern@L134, tmp_path@L134, _@L136, _@L136, connector@L136, query@L136, output@L138, url@L157, connector@L171, request@L173, error@L175. Purposes/parameters: docs/code-map.json.
import base64
import hashlib
import io
import json
from urllib.parse import parse_qs
import httpx
import pytest
from PIL import Image
from studio.deviantart import DeviantArt, asset_url, description


def connector_fixture(kind="ordinary"):
    """Build explicit simulated OAuth/gallery responses and retain requests for token-leak assertions."""
    requests = []
    stream = io.BytesIO()
    Image.new("RGB", (32, 32), "green").save(stream, format="PNG")

    def handler(request):
        """Serve one owned-fixture entry; external networking is impossible with MockTransport."""
        requests.append(request)
        path = request.url.path
        if path == "/oauth2/token":
            return httpx.Response(
                200, json={"access_token": "fixture-not-a-real-token", "expires_in": 3600}
            )
        if path.endswith("/whoami"):
            return httpx.Response(200, json={"username": "FixtureOwner"})
        if path.endswith("/gallery/all"):
            item = {
                "deviationid": "fixture-001",
                "title": "Owned green circle",
                "author": {"username": "Other" if kind == "other-owner" else "FixtureOwner"},
                "content": {"src": "https://images.wixmp.com/owned.png"},
            }
            return httpx.Response(
                200,
                json={"results": [item], "has_more": kind == "bad-pagination", "next_offset": 0},
            )
        if path.endswith("/deviation/metadata"):
            item = {
                "deviationid": "fixture-001",
                "description": "<p>green circle</p><script>ignored</script>",
                "tags": [{"tag_name": "green"}],
            }
            if kind == "ai":
                item["is_ai_generated"] = True
            if kind == "noai":
                item["is_noai"] = True
            return httpx.Response(200, json={"metadata": [item]})
        if path == "/owned.png":
            return httpx.Response(
                302 if kind == "redirect" else 200,
                headers={"Content-Type": "image/png", "Location": "http://127.0.0.1/private"},
                content=stream.getvalue(),
            )
        raise AssertionError("Unexpected fixture request: " + path)

    clock = [100.0]
    connector = DeviantArt(8016, httpx.MockTransport(handler), clock=lambda: clock[0])
    result = connector.begin("12345")
    query = parse_qs(httpx.URL(result["url"]).query.decode())
    return connector, requests, query, clock


def test_pkce_one_use_expiry_and_no_secrets(tmp_path):
    """Validate state, verifier/challenge and token request placement; credentials never reach disk/status."""
    connector, requests, query, clock = connector_fixture()
    verifier = connector.pending["verifier"]
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )
    assert query["code_challenge"] == [expected]
    assert query["code_challenge_method"] == ["S256"]
    assert query["scope"] == ["basic browse user"]
    with pytest.raises(ValueError, match="state"):
        connector.finish("wrong", "fixture-code")
    assert not requests
    assert connector.finish(query["state"][0], "fixture-code")["connected"]
    body = parse_qs(requests[0].content.decode())
    assert body["code_verifier"] == [verifier]
    assert "client_secret" not in body
    assert "access_token" not in str(requests[1].url)
    assert "fixture-not-a-real-token" not in json.dumps(connector.status())
    with pytest.raises(ValueError):
        connector.finish(query["state"][0], "fixture-code")
    clock[0] += 3601
    assert not connector.status()["connected"]
    connector.close()
    assert not list(tmp_path.iterdir())


def test_expired_oauth_state_does_not_exchange():
    """Expired attempts cannot be reused even with the correct original state."""
    connector, requests, query, clock = connector_fixture()
    clock[0] += 601
    with pytest.raises(ValueError, match="expired"):
        connector.finish(query["state"][0], "code")
    assert not requests
    connector.close()


@pytest.mark.parametrize("kind,flagged", [("ordinary", 0), ("ai", 1)])
def test_bounded_gallery_preserves_caption_and_origin(tmp_path, kind, flagged):
    """Contract-test normalized raster/captions/AI metadata while enforcing no bearer token at CDN."""
    connector, requests, query, _ = connector_fixture(kind)
    connector.finish(query["state"][0], "code")
    output = tmp_path / "dataset"
    manifest = connector.gallery(output, "Contract fixture", 24)
    assert manifest["counts"] == {"total": 1, "flagged": flagged}
    assert "green circle" in manifest["records"][0]["caption"]
    assert "ignored" not in manifest["records"][0]["caption"]
    assert manifest["connector"]["visited"] == 1
    asset = next(request for request in requests if request.url.host == "images.wixmp.com")
    assert "authorization" not in asset.headers
    assert not any(
        "fixture-not-a-real-token" in path.read_text(errors="ignore")
        for path in output.rglob("*.json")
    )
    connector.close()


@pytest.mark.parametrize(
    "kind,pattern",
    [
        ("other-owner", "author"),
        ("redirect", "redirect"),
        ("bad-pagination", "pagination"),
        ("noai", "No supported"),
    ],
)
def test_import_fails_closed_and_leaves_no_dataset(tmp_path, kind, pattern):
    """Ownership, redirect, pagination and explicit opt-out failures never publish partial training datasets."""
    connector, _, query, _ = connector_fixture(kind)
    connector.finish(query["state"][0], "code")
    output = tmp_path / "dataset"
    with pytest.raises(ValueError, match=pattern):
        connector.gallery(output, "Blocked fixture", 24)
    assert not output.exists()
    assert not list(tmp_path.glob(".da-import-*"))
    connector.close()


@pytest.mark.parametrize(
    "url",
    [
        "http://images.wixmp.com/a",
        "https://wixmp.com.evil.example/a",
        "https://127.0.0.1/a",
        "https://user:password@wixmp.com/a",
        "https://wixmp.com:8016/a",
        "https://evil.example/a",
    ],
)
def test_no_arbitrary_image_url(url):
    """Provider metadata cannot turn imports into arbitrary-host/private-network downloads."""
    with pytest.raises(ValueError):
        asset_url(url)


def test_description_is_inert_and_bounded():
    """Descriptions lose markup and hidden scripts rather than becoming UI HTML."""
    assert description("<p>One &amp; two</p><script>bad</script>") == "One & two"
    assert len(description("x" * 40000)) == 1400


def test_rate_limit_error_does_not_echo_tokens():
    """Remote error bodies/URLs are redacted and no automatic retry defeats provider limits."""
    connector = DeviantArt(
        8016,
        httpx.MockTransport(lambda request: httpx.Response(429, json={"detail": "private-secret"})),
    )
    with pytest.raises(ValueError, match="HTTP 429") as error:
        connector.json_request("GET", "https://www.deviantart.com/api/v1/oauth2/placebo")
    assert "private-secret" not in str(error.value)
    connector.close()
