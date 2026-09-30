"""Read-only own-gallery OAuth connector: PKCE, memory-only credentials and bounded imports."""

# Index: declarations module.PlainText@L29, PlainText.__init__@L32, PlainText.handle_starttag@L37, PlainText.handle_endtag@L44, PlainText.handle_data@L49, module.description@L55, module.asset_url@L62, module.DeviantArt@L79, DeviantArt.__init__@L82, DeviantArt.begin@L99, DeviantArt.json_request@L127, DeviantArt.finish@L149, DeviantArt.status@L194, DeviantArt.disconnect@L204, DeviantArt.gallery@L209, DeviantArt.close@L358; variables API@L20, OAUTH@L21, HEADERS@L22, self@L32, attributes@L37, self@L37, tag@L37, self@L44, tag@L44, data@L49, self@L49, value@L55, parser@L57, value@L62, parsed@L64, domains@L65, host@L66, domain@L73, clock@L82, port@L82, self@L82, transport@L82, client_id@L99, self@L99, state@L104, verifier@L104, challenge@L105, params@L116, kwargs@L127, method@L127, self@L127, url@L127, response@L130, body@L135, chunk@L136, value@L140, code@L149, self@L149, state@L149, pending@L152, result@L162, access@L173, duration@L174, who@L182, username@L188, self@L194, connected@L197, self@L204, limit@L209, name@L209, output@L209, self@L209, token@L216, username@L216, auth@L217, offset@L219, seen@L219, skipped@L219, visited@L219, deadline@L220, temporary@L221, source@L222, page@L228, items@L240, item@L243, visited@L246, identity@L247, content@L257, skipped@L259, metadata@L261, entries@L267, details@L270, skipped@L278, url@L280, path@L281, response@L285, size@L297, destination@L298, chunk@L299, size@L300, tags@L310, tag@L312, ai@L315, value@L317, origin@L319, caption@L320, next_offset@L343, offset@L346, manifest@L347, self@L358. Purposes/parameters: docs/code-map.json.
import base64
import hashlib
import json
import re
import secrets
import tempfile
import threading
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import httpx
from studio.datasets import import_dataset
from studio.files import atomic_json, normalized_image

API = "https://www.deviantart.com/api/v1/oauth2"
OAUTH = "https://www.deviantart.com/oauth2"
HEADERS = {
    "User-Agent": "PersonalImageModelStudio/0.1",
    "Accept-Encoding": "gzip",
    "dA-minor-version": "20240701",
}


class PlainText(HTMLParser):
    """Convert bounded provider descriptions to inert text, never rendering remote markup."""

    def __init__(self):
        """Track text and nested non-content sections."""
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attributes):
        """Ignore scripts/styles and separate block text."""
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag in {"p", "br", "div", "li"}:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        """Exit non-content sections without interpreting executable attributes."""
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        """Collect only visible description text."""
        if not self.hidden:
            self.parts.append(data)


def description(value: str) -> str:
    """Return at most 1400 inert description characters for a training caption."""
    parser = PlainText()
    parser.feed(str(value)[:32000])
    return " ".join("".join(parser.parts).split())[:1400]


def asset_url(value: str) -> str:
    """Allow HTTPS provider raster CDN URLs only; reject credentials, redirects and arbitrary hosts."""
    parsed = urlsplit(value)
    domains = ("deviantart.com", "deviantart.net", "wixmp.com")
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or parsed.port not in (None, 443)
        or parsed.username
        or parsed.password
        or parsed.fragment
        or not any(host == domain or host.endswith("." + domain) for domain in domains)
    ):
        raise ValueError("Image URL is not an approved HTTPS provider host")
    return value


class DeviantArt:
    """One private app-session authorization; no passwords, client secrets or saved OAuth tokens."""

    def __init__(self, port: int, transport=None, clock=time.monotonic):
        """Use fixed TLS endpoints and injectable contract-test transport, not arbitrary API base URLs."""
        self.callback = f"http://127.0.0.1:{port}/oauth/deviantart/callback"
        self.clock = clock
        self.client = httpx.Client(
            headers=HEADERS,
            timeout=15,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )
        self.lock = threading.RLock()
        self.pending = None
        self.access = None
        self.expires = 0
        self.username = None

    def begin(self, client_id: str) -> dict:
        """Start a ten-minute, one-use S256 flow for a registered PUBLIC client; no secret is accepted."""
        if not re.fullmatch(r"[0-9]{1,12}", client_id):
            raise ValueError("Enter the numeric public client ID, not a secret")
        with self.lock:
            verifier, state = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
            challenge = (
                base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
                .decode()
                .rstrip("=")
            )
            self.pending = {
                "client_id": client_id,
                "verifier": verifier,
                "state": state,
                "started": self.clock(),
            }
            params = {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": self.callback,
                "scope": "basic browse user",
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
            return {"url": OAUTH + "/authorize?" + urlencode(params), "callback": self.callback}

    def json_request(self, method: str, url: str, **kwargs) -> dict:
        """Bound decoded API bodies and redact remote errors/URLs/tokens from exceptions."""
        try:
            with self.client.stream(method, url, **kwargs) as response:
                if response.status_code != 200:
                    raise ValueError(
                        f"DeviantArt request failed (HTTP {response.status_code}); retry authorization or check provider limits"
                    )
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 1024 * 1024:
                        raise ValueError("DeviantArt metadata exceeds 1 MiB")
            value = json.loads(body)
            if not isinstance(value, dict):
                raise ValueError("Invalid DeviantArt response shape")
            return value
        except (httpx.HTTPError, json.JSONDecodeError):
            raise ValueError(
                "DeviantArt request unavailable or invalid; no credentials were logged"
            ) from None

    def finish(self, state: str, code: str) -> dict:
        """Consume exact state before exchange and bind future imports to the authenticated username."""
        with self.lock:
            pending = self.pending
            if (
                not pending
                or not secrets.compare_digest(state, pending["state"])
                or self.clock() - pending["started"] > 600
            ):
                raise ValueError("Authorization state invalid or expired; start a new connection")
            self.pending = None
            if not code or len(code) > 2048:
                raise ValueError("Missing authorization code")
            result = self.json_request(
                "POST",
                OAUTH + "/token",
                data={
                    "client_id": pending["client_id"],
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.callback,
                    "code_verifier": pending["verifier"],
                },
            )
            access = result.get("access_token")
            duration = result.get("expires_in")
            if (
                not isinstance(access, str)
                or not 1 <= len(access) <= 4096
                or type(duration) is not int
                or not 1 <= duration <= 3600
            ):
                raise ValueError("Invalid OAuth token response")
            who = self.json_request(
                "GET",
                API + "/user/whoami",
                params={"with_session": "true"},
                headers={"Authorization": "Bearer " + access},
            )
            username = who.get("username")
            if not isinstance(username, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", username):
                raise ValueError("Provider did not identify the authenticated account")
            self.access, self.expires, self.username = access, self.clock() + duration, username
            return self.status()

    def status(self) -> dict:
        """Expose account connection state, never token values; expiry requires browser reauthorization."""
        with self.lock:
            connected = bool(self.access and self.clock() < self.expires)
            return {
                "connected": connected,
                "username": self.username if connected else None,
                "callback": self.callback,
            }

    def disconnect(self) -> None:
        """Forget local memory credentials; users can revoke the app in provider account settings."""
        with self.lock:
            self.access, self.username, self.pending, self.expires = None, None, None, 0

    def gallery(self, output: Path, name: str, limit: int = 24) -> dict:
        """Import at most 96 own-gallery raster entries; no favourites, bypasses, uploads or auto-training."""
        if not 1 <= limit <= 96:
            raise ValueError("Gallery sample limit must be 1..96")
        with self.lock:
            if not self.status()["connected"]:
                raise ValueError("Connect your DeviantArt account before importing")
            token, username = self.access, self.username
        auth = {"Authorization": "Bearer " + token}
        output.parent.mkdir(parents=True, exist_ok=True)
        seen, offset, skipped, visited = set(), 0, 0, 0
        deadline = self.clock() + 300
        with tempfile.TemporaryDirectory(prefix=".da-import-", dir=output.parent) as temporary:
            source = Path(temporary)
            while visited < limit:
                if self.clock() > deadline:
                    raise ValueError(
                        "Gallery import exceeded its five-minute budget; reduce sample size"
                    )
                page = self.json_request(
                    "GET",
                    API + "/gallery/all",
                    params={
                        "username": username,
                        "offset": offset,
                        "limit": min(24, limit - visited),
                        "with_session": "true",
                        "mature_content": "false",
                    },
                    headers=auth,
                )
                items = page.get("results")
                if not isinstance(items, list) or len(items) > 24:
                    raise ValueError("Invalid bounded gallery page")
                for item in items:
                    if visited >= limit:
                        break
                    visited += 1
                    identity = item.get("deviationid", "")
                    if (
                        not isinstance(identity, str)
                        or not re.fullmatch(r"[A-Za-z0-9-]{1,64}", identity)
                        or identity in seen
                    ):
                        raise ValueError("Gallery contains an invalid or repeated entry")
                    seen.add(identity)
                    if item.get("author", {}).get("username", "").casefold() != username.casefold():
                        raise ValueError("Gallery author differs from your authenticated account")
                    content = item.get("content", {})
                    if item.get("is_mature") or not content.get("src"):
                        skipped += 1
                        continue
                    metadata = self.json_request(
                        "GET",
                        API + "/deviation/metadata",
                        params={"deviationids[]": identity, "with_session": "true"},
                        headers=auth,
                    )
                    entries = metadata.get("metadata", [])
                    if len(entries) != 1 or entries[0].get("deviationid") != identity:
                        raise ValueError("Missing/mismatched gallery caption metadata")
                    details = entries[0]
                    # Respect explicit provider NoAI/opt-out flags. An account link is not a training license.
                    if (
                        details.get("is_ai_training_allowed") is False
                        or details.get("allows_ai_training") is False
                        or details.get("is_noai")
                        or item.get("is_noai")
                    ):
                        skipped += 1
                        continue
                    url = asset_url(content["src"])
                    path = source / f"{identity}.png"
                    try:
                        with self.client.stream(
                            "GET", url, headers={"Accept": "image/png,image/jpeg,image/webp"}
                        ) as response:
                            if response.status_code != 200 or response.headers.get(
                                "content-type", ""
                            ).split(";")[0] not in {
                                "image/png",
                                "image/jpeg",
                                "image/webp",
                                "image/bmp",
                            }:
                                raise ValueError(
                                    "Unsupported raster response or redirect; no bypass attempted"
                                )
                            size = 0
                            with path.open("wb") as destination:
                                for chunk in response.iter_bytes():
                                    size += len(chunk)
                                    if size > 20 * 1024 * 1024 or self.clock() > deadline:
                                        raise ValueError("Gallery raster exceeds size/time budget")
                                    destination.write(chunk)
                        with normalized_image(path):
                            pass
                    except httpx.HTTPError:
                        raise ValueError(
                            "Gallery image download unavailable; private URL was not logged"
                        ) from None
                    tags = [
                        str(tag.get("tag_name", ""))[:100]
                        for tag in details.get("tags", [])[:64]
                        if isinstance(tag, dict)
                    ]
                    ai = any(
                        value.get("is_ai_generated") or value.get("is_ai_assisted")
                        for value in (item, details)
                    )
                    origin = "ai_assisted" if ai else "unknown"
                    caption = ", ".join(
                        filter(
                            None,
                            [
                                str(item.get("title", ""))[:200],
                                description(details.get("description", "")),
                                " ".join(tags),
                            ],
                        )
                    )[:2000]
                    atomic_json(
                        path.with_suffix(".json"),
                        {
                            "caption": caption,
                            "tags": tags,
                            "origin": origin,
                            "name": str(item.get("title", ""))[:200],
                            "artist": username,
                            "license": "Account owner confirmed training rights and provider terms; account ownership alone is not a license",
                        },
                    )
                if not page.get("has_more") or not items or visited >= limit:
                    break
                next_offset = page.get("next_offset")
                if type(next_offset) is not int or not offset < next_offset <= 50000:
                    raise ValueError("Gallery pagination did not advance")
                offset = next_offset
            manifest = import_dataset([str(source)], output, name)
            manifest["connector"] = {
                "provider": "DeviantArt",
                "visited": visited,
                "skipped": skipped,
                "max_items": limit,
                "scope": "own gallery raster sample",
            }
            atomic_json(output / "dataset.json", manifest)
            return manifest

    def close(self) -> None:
        """Forget credentials and release only this connector's HTTP client."""
        self.disconnect()
        self.client.close()
