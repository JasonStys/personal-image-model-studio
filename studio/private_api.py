"""Jason Stys: authenticated loopback accounts, private uploads and isolated real ML dispatch.
# Index: declarations module.LocalBoundary@L35, LocalBoundary.__init__@L38, LocalBoundary.__call__@L44, LocalBoundary.__call__.guarded_send@L51, LocalBoundary.__call__.deny@L67, LocalBoundary.__call__.replay@L122, module.Closed@L133, module.Credentials@L139, module.Recovery@L146, module.Unlock@L152, module.Delete@L159, module.Activity@L166, module.UploadStart@L172, module.UploadChunk@L180, module.WorkspaceProxy@L187, WorkspaceProxy.__init__@L190, WorkspaceProxy.__call__@L194, WorkspaceProxy.__call__.replay@L264, module.create_private_app@L288, create_private_app.lifespan@L305, create_private_app.lifespan.idle_lock@L311, create_private_app.invalid@L348, create_private_app.bad_value@L353, create_private_app.bad_file@L358, create_private_app.identify@L367, create_private_app.signed@L371, create_private_app.auth_limit@L384, create_private_app.health@L392, create_private_app.register@L420, create_private_app.login@L432, create_private_app.reset@L441, create_private_app.account@L464, create_private_app.unlock@L475, create_private_app.activity@L487, create_private_app.save@L494, create_private_app.lock@L503, create_private_app.logout@L509, create_private_app.delete@L520, create_private_app.backup@L537, create_private_app.begin_file@L551, create_private_app.file_chunk@L596, create_private_app.callback@L628; variables COOKIE@L31, CSP@L32, app@L38, manager@L38, self@L38, receive@L44, scope@L44, self@L44, send@L44, raw@L48, headers@L49, k@L49, v@L49, message@L51, detail@L67, status@L67, _@L74, k@L74, callback@L77, accounts@L82, mutation@L87, cookies@L95, name@L100, token@L101, account@L102, public@L105, chunks@L108, total@L108, message@L110, body@L113, total@L114, consumed@L120, consumed@L126, model_config@L136, alias@L142, password@L143, recovery@L149, key@L155, salt@L156, password@L162, confirm@L163, idle_seconds@L169, path@L175, size@L176, batch@L177, offset@L183, content@L184, manager@L190, self@L190, receive@L194, scope@L194, self@L194, send@L194, account@L198, manager@L201, path@L207, parts@L219, message@L221, content@L225, data@L227, chosen@L228, item@L237, consumed@L261, original_receive@L262, consumed@L268, receive@L272, forwarded@L273, k@L278, v@L278, root@L289, port@L290, static@L291, interpreter@L292, embedded@L293, native_identity@L295, static@L300, manager@L301, app@L305, task@L326, app@L337, error@L348, request@L348, error@L353, request@L353, error@L358, request@L358, request@L367, body@L371, owner@L371, response@L373, alias@L384, result@L394, key@L404, data@L420, owner@L424, recovery@L424, data@L432, owner@L435, data@L441, db@L446, row@L447, fresh@L456, request@L464, data@L475, request@L475, owner@L477, result@L481, data@L487, request@L487, request@L494, result@L498, request@L503, request@L509, response@L515, data@L520, request@L520, owner@L522, db@L525, row@L526, response@L532, request@L537, owner@L539, path@L543, data@L551, request@L551, path@L555, maximum@L572, used@L572, batch@L575, destination@L576, identity@L580, temporary@L581, data@L596, identity@L596, request@L596, record@L600, content@L604, stream@L614, complete@L617, request@L628, params@L635, k@L636. Purposes/parameters: docs/code-map.json.

Not a public-hosting API. No credentials appear in URLs, responses, logs or Git.
"""

import base64
import binascii
import json
import os
import secrets
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from studio.accounts import password_matches, digest
from studio import __version__
from studio.private_workspace import Workspaces
from studio.vault import MAX_BYTES, safe_name

COOKIE = "pims_account"
CSP = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; worker-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-src 'none'; frame-ancestors 'none'"


class LocalBoundary:
    """Validate origin/body/CSRF before parsing and identify the account only from its HttpOnly cookie."""

    def __init__(self, app, manager: Workspaces):
        """Bind one exact literal-loopback origin and its runtime-only account repository."""
        self.app, self.manager = app, manager
        self.host = f"127.0.0.1:{manager.port}"
        manager.cookie_name = COOKIE + "_" + str(manager.port)

    async def __call__(self, scope, receive, send):
        """Reject spoofed hosting, cross-site requests, unauthenticated APIs and unbounded bodies."""
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        raw = scope["headers"]
        headers = {k.decode().lower(): v.decode() for k, v in raw}

        async def guarded_send(message):
            """Every response, including denials and file downloads, stays non-cacheable and unframed."""
            if message["type"] == "http.response.start":
                message["headers"] += [
                    (b"cache-control", b"no-store"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"content-security-policy", CSP.encode()),
                    (
                        b"permissions-policy",
                        b"camera=(), microphone=(), geolocation=(), payment=(), browsing-topics=()",
                    ),
                ]
            await send(message)

        async def deny(detail, status):
            """Emit only generic boundary errors, never bodies, credentials or machine paths."""
            await JSONResponse({"detail": detail}, status)(scope, receive, guarded_send)

        if (
            headers.get("host") != self.host
            or scope.get("scheme") != "http"
            or sum(k.lower() == b"host" for k, _ in raw) != 1
        ):
            return await deny("Use this app's exact loopback address", 403)
        callback = scope["path"] == "/oauth/deviantart/callback" and scope["method"] == "GET"
        if headers.get("origin", "http://" + self.host) != "http://" + self.host or (
            headers.get("sec-fetch-site") == "cross-site" and not callback
        ):
            return await deny("Untrusted local origin", 403)
        accounts = self.manager.accounts
        if not await run_in_threadpool(
            accounts.throttle, "request:" + str(scope.get("client", ("local",))[0]), 1000
        ):
            return await deny("Too many requests; wait before trying again", 429)
        mutation = scope["method"] not in {"GET", "HEAD", "OPTIONS"}
        if mutation and (
            headers.get("x-pims-request") != "v1"
            or headers.get("content-type", "").split(";")[0] != "application/json"
        ):
            return await deny("This action requires the app's same-origin JSON request", 403)
        from http.cookies import SimpleCookie, CookieError

        cookies = SimpleCookie()
        try:
            cookies.load(headers.get("cookie", ""))
        except CookieError:
            return await deny("Invalid session", 401)
        name = self.manager.cookie_name
        token = cookies[name].value if name in cookies else ""
        account = await run_in_threadpool(accounts.owner, token) if token else None
        scope.setdefault("state", {})["account"] = account
        scope["state"]["session_token"] = token
        public = {"/private/register", "/private/login", "/private/reset"}
        if scope["path"].startswith("/private/") and scope["path"] not in public and not account:
            return await deny("Sign in to your local account", 401)
        chunks, total = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            total += len(body)
            if total > 8 * 1024**2:
                return await deny("Request exceeds 8 MiB", 413)
            chunks.append(body)
            if not message.get("more_body", False):
                break
        consumed = False

        async def replay():
            """Replay only this bounded request and preserve disconnect handling for file responses."""
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, replay, guarded_send)


class Closed(BaseModel):
    """Reject unknown fields rather than treating them as privileges or executable configuration."""

    model_config = ConfigDict(extra="forbid")


class Credentials(Closed):
    """Non-identifying lower-case alias and a long login password; no email or demographics required."""

    alias: str = Field(pattern=r"^[a-z0-9_][a-z0-9_-]{2,39}$")
    password: str = Field(min_length=15, max_length=128)


class Recovery(Credentials):
    """One-use login recovery does not recover a forgotten encryption phrase."""

    recovery: str = Field(min_length=32, max_length=128)


class Unlock(Closed):
    """Browser-derived 256-bit key for this trusted local service; never saved in the account database."""

    key: str = Field(min_length=44, max_length=44)
    salt: str | None = Field(default=None, min_length=24, max_length=24)


class Delete(Closed):
    """Current password and explicit confirmation protect against accidental live-data deletion."""

    password: str = Field(min_length=15, max_length=128)
    confirm: Literal[True]


class Activity(Closed):
    """Human-triggered heartbeat; polling alone does not keep a decrypted workspace alive."""

    idle_seconds: Literal[600, 1800, 7200] = 600


class UploadStart(Closed):
    """Portable browser-selected relative name, bounded size and optional existing upload batch."""

    path: str = Field(min_length=1, max_length=240)
    size: int = Field(ge=1, le=6 * 1024**3)
    batch: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")


class UploadChunk(Closed):
    """One ordered 4-MiB maximum chunk; replay/out-of-order chunks cannot overwrite earlier bytes."""

    offset: int = Field(ge=0, le=MAX_BYTES)
    content: str = Field(max_length=5_600_000)


class WorkspaceProxy:
    """Adapt account-cookie requests to the old trusted ML API without exposing its internal bearer token."""

    def __init__(self, manager):
        """Retain only the account coordinator, never a caller-selected workspace path."""
        self.manager = manager

    async def __call__(self, scope, receive, send):
        """Serialize API mutations with snapshot/lock operations and restrict machine-path/runtime capabilities."""
        if scope["type"] != "http":
            return
        account = scope.get("state", {}).get("account")
        if not account:
            return await JSONResponse({"detail": "Sign in first"}, 401)(scope, receive, send)
        manager = self.manager
        async with manager.requests:
            if manager.owner != account["id"]:
                return await JSONResponse({"detail": "Unlock your account's workspace first"}, 423)(
                    scope, receive, send
                )
            path = scope["path"].split("/private/api", 1)[-1]
            if path == "/runtime" and scope["method"] != "GET":
                return await JSONResponse(
                    {
                        "detail": "Account mode does not accept executable paths. Configure a trusted runtime in the launcher, not a browser."
                    },
                    403,
                )(scope, receive, send)
            if (
                path in {"/models", "/datasets", "/train", "/generate"}
                and scope["method"] == "POST"
            ):
                parts = []
                while True:
                    message = await receive()
                    parts.append(message.get("body", b""))
                    if not message.get("more_body", False):
                        break
                content = b"".join(parts)
                try:
                    data = json.loads(content)
                    chosen = (
                        data.get("paths", [])
                        if path == "/datasets"
                        else [data.get("path")]
                        if path == "/models"
                        else []
                    )
                    if not isinstance(chosen, list):
                        raise ValueError()
                    for item in chosen:
                        if not isinstance(item, str) or not Path(item).resolve().is_relative_to(
                            manager.active / "imports"
                        ):
                            raise ValueError()
                    if manager.embedded and (
                        path == "/train"
                        and data.get("mode") == "lora"
                        or path == "/models"
                        and data.get("kind") != "native"
                    ):
                        return await JSONResponse(
                            {
                                "detail": "The bundled CPU engine supports native models. Classic SD/LoRA requires an explicitly configured full ML runtime."
                            },
                            400,
                        )(scope, receive, send)
                except (ValueError, TypeError, AttributeError):
                    return await JSONResponse(
                        {
                            "detail": "Select files through the account upload controls; arbitrary machine paths are forbidden"
                        },
                        400,
                    )(scope, receive, send)
                consumed = False
                original_receive = receive

                async def replay():
                    """Restore inspected JSON to the inner closed-schema handlers."""
                    nonlocal consumed
                    if not consumed:
                        consumed = True
                        return {"type": "http.request", "body": content, "more_body": False}
                    return await original_receive()

                receive = replay
            forwarded = dict(scope)
            forwarded["path"] = "/api" + path
            forwarded["raw_path"] = forwarded["path"].encode()
            forwarded["root_path"] = ""
            forwarded["headers"] = [
                (k, v) for k, v in scope["headers"] if k.lower() != b"authorization"
            ] + [(b"authorization", ("Bearer " + manager.internal_token).encode())]
            await manager.app(forwarded, receive, send)
            # A completed response remains valid if a subsequent snapshot fails; retain recovery files.
            try:
                await run_in_threadpool(manager.save)
            except Exception:
                manager.save_failed = True


def create_private_app(
    root: Path,
    port: int,
    static: Path | None = None,
    interpreter=None,
    embedded=False,
    *,
    native_identity=None,
):
    """Create a distinct, loopback-only account service; old plaintext runtime directories remain untouched."""
    if not 1024 <= port <= 65535:
        raise ValueError("Choose an available loopback port in 1024..65535")
    static = static or Path(__file__).resolve().parents[1] / "dist"
    manager = Workspaces(root, port, static, interpreter, embedded)
    manager.last_activity, manager.idle_seconds, manager.save_failed = time.monotonic(), 600, False

    @asynccontextmanager
    async def lifespan(app):
        """Expire unlocked keys independently of UI polling and preserve interrupted data if saving fails."""
        import asyncio

        app.state.lifecycle_started = True

        async def idle_lock():
            """Check human-idle deadlines without renewing them on ordinary workspace polling."""
            while True:
                await asyncio.sleep(5)
                async with manager.requests:
                    if (
                        manager.owner
                        and time.monotonic() - manager.last_activity > manager.idle_seconds
                    ):
                        try:
                            await run_in_threadpool(manager.lock, manager.owner)
                        except Exception:
                            manager.save_failed = True
                            manager.last_activity = time.monotonic()

        task = asyncio.create_task(idle_lock())
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            await run_in_threadpool(manager.close)

    app = FastAPI(
        title="Personal Image Model Studio — Jason Stys",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.manager = manager
    app.add_middleware(LocalBoundary, manager=manager)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, error):
        """Never reflect supplied passwords, base64 image data or keys into validation errors."""
        return JSONResponse({"detail": "Invalid input; check the field limits in Help"}, 422)

    @app.exception_handler(ValueError)
    async def bad_value(request, error):
        """Known bounded safe application messages only; no tracebacks or raw request data."""
        return JSONResponse({"detail": str(error)[:400]}, 400)

    @app.exception_handler(OSError)
    async def bad_file(request, error):
        """Filesystem failures reveal no private machine path."""
        return JSONResponse(
            {
                "detail": "Local file/storage operation failed; preserve your data and check available disk space"
            },
            400,
        )

    def identify(request):
        """Owner comes from the validated server session, never a client-selected ID."""
        return request.state.account["id"]

    def signed(owner, body):
        """Random HttpOnly/SameSite cookie, no JS storage/token links; HTTP is allowed only on loopback."""
        response = JSONResponse(body)
        response.set_cookie(
            manager.cookie_name,
            manager.accounts.session(owner),
            max_age=8 * 3600,
            httponly=True,
            samesite="strict",
            path="/private",
        )
        return response

    async def auth_limit(alias):
        """Persistent global/alias throttles bound expensive login/recovery hashing."""
        if not await run_in_threadpool(
            manager.accounts.throttle, "auth-global", 40
        ) or not await run_in_threadpool(manager.accounts.throttle, "auth:" + alias, 10):
            raise HTTPException(429, "Too many login attempts; wait five minutes")

    @app.get("/health")
    def health():
        """Metadata-only readiness; no account identities, filesystem paths or secret parameters."""
        result = {
            "ready": True,
            "mode": "private-local-accounts",
            "version": __version__,
            "author": "Jason Stys",
            "validation_nonce": os.environ.get("PIMS_VALIDATION_NONCE"),
        }
        if native_identity is not None:
            result["native"] = {
                key: native_identity[key]
                for key in (
                    "product",
                    "version",
                    "source",
                    "source_dirty",
                    "python",
                    "tcl_version",
                    "tk_version",
                )
            }
            result["native"]["runtime_library_sha256"] = native_identity["runtime_library"][
                "sha256"
            ]
        return result

    @app.post("/private/register")
    async def register(data: Credentials):
        """Register an empty account; duplicate aliases disclose no existing account contents."""
        await auth_limit(data.alias)
        try:
            owner, recovery = await run_in_threadpool(
                manager.accounts.register, data.alias, data.password
            )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Unable to register this alias; choose another") from None
        return signed(owner, {"alias": data.alias, "recovery": recovery})

    @app.post("/private/login")
    async def login(data: Credentials):
        """Authenticate a real account with a fixed-cost missing-user hash and rotate its session."""
        await auth_limit(data.alias)
        owner = await run_in_threadpool(manager.accounts.login, data.alias, data.password)
        if not owner:
            raise HTTPException(401, "Unable to sign in with those credentials")
        return signed(owner, {"alias": data.alias})

    @app.post("/private/reset")
    async def reset(data: Recovery):
        """Rotate login/recovery credentials and revoke all its sessions; preserve the independent vault key."""
        await auth_limit(data.alias)
        # Locate only the recovery-code-confirmed account; do not trust a caller-provided owner.
        async with manager.requests:
            with manager.accounts.connection() as db:
                row = db.execute(
                    "SELECT id,recovery FROM accounts WHERE username=?", (data.alias,)
                ).fetchone()
            if not row or not secrets.compare_digest(row["recovery"], digest(data.recovery)):
                raise HTTPException(401, "Recovery credentials are invalid")
            # Seal before rotating credentials: a failed disk write must not
            # consume a recovery code or lose the once-shown replacement.
            if manager.owner == row["id"]:
                await run_in_threadpool(manager.lock, row["id"])
            fresh = await run_in_threadpool(
                manager.accounts.reset, data.alias, data.recovery, data.password
            )
            if not fresh:
                raise HTTPException(401, "Recovery credentials are invalid")
        return JSONResponse({"recovery": fresh})

    @app.get("/private/account")
    def account(request: Request):
        """Return just the caller's account status and documented runtime/privacy capabilities."""
        return {
            "alias": request.state.account["username"],
            **manager.status(identify(request)),
            "save_failed": manager.save_failed,
            "idle_seconds": manager.idle_seconds,
            "embedded_cpu": manager.embedded,
        }

    @app.post("/private/unlock")
    async def unlock(request: Request, data: Unlock):
        """Unlock exactly the authenticated owner with a key derived in its browser."""
        owner = identify(request)
        if not await run_in_threadpool(manager.accounts.throttle, "unlock:" + owner, 10):
            raise HTTPException(429, "Too many unlock attempts; wait five minutes")
        async with manager.requests:
            result = await run_in_threadpool(manager.unlock, owner, data.key, data.salt)
            manager.last_activity, manager.save_failed = time.monotonic(), False
            manager.idle_seconds = 600
            return result

    @app.post("/private/activity")
    def activity(request: Request, data: Activity):
        """Human UI activity alone renews the key timeout; longer job sessions need explicit selection."""
        manager.require(identify(request))
        manager.last_activity, manager.idle_seconds = time.monotonic(), data.idle_seconds
        return {"active": True}

    @app.post("/private/save")
    async def save(request: Request):
        """Explicit idle snapshot; failed saves retain both key and plaintext recovery data."""
        async with manager.requests:
            manager.require(identify(request))
            result = await run_in_threadpool(manager.save, True)
            manager.save_failed = False
            return result

    @app.post("/private/lock")
    async def lock(request: Request):
        """Cancel this account's jobs, seal its workspace, close OAuth and remove its plaintext staging directory."""
        async with manager.requests:
            return await run_in_threadpool(manager.lock, identify(request))

    @app.post("/private/logout")
    async def logout(request: Request):
        """Lock the caller's active workspace and revoke only its presented session."""
        async with manager.requests:
            if manager.owner == identify(request):
                await run_in_threadpool(manager.lock, identify(request))
            manager.accounts.revoke(request.state.session_token)
        response = JSONResponse({"signed_out": True})
        response.delete_cookie(manager.cookie_name, path="/private")
        return response

    @app.post("/private/delete")
    async def delete(request: Request, data: Delete):
        """Require a current password; cascade only this account and remove only its checked local data paths."""
        owner = identify(request)
        await auth_limit(request.state.account["username"])
        async with manager.requests:
            with manager.accounts.connection() as db:
                row = db.execute("SELECT password FROM accounts WHERE id=?", (owner,)).fetchone()
            if not row or not await run_in_threadpool(password_matches, data.password, row[0]):
                raise HTTPException(401, "Current password is incorrect")
            await run_in_threadpool(manager.delete_data, owner)
            if not await run_in_threadpool(manager.accounts.delete, owner, data.password):
                raise HTTPException(409, "Account changed; sign in again")
        response = JSONResponse({"deleted": True})
        response.delete_cookie(manager.cookie_name, path="/private")
        return response

    @app.get("/private/backup")
    async def backup(request: Request):
        """Export only the caller's encrypted archive; account-key metadata is backed up separately for now."""
        owner = identify(request)
        async with manager.requests:
            if manager.owner == owner:
                await run_in_threadpool(manager.save, True)
            path = manager.archive(owner)
            if not path.exists():
                raise HTTPException(404, "Create and save a workspace first")
            return FileResponse(
                path, media_type="application/octet-stream", filename="private-workspace.pimsvault"
            )

    @app.post("/private/files")
    async def begin_file(request: Request, data: UploadStart):
        """Reserve one browser-selected upload inside this account, not an arbitrary machine location."""
        async with manager.requests:
            manager.require(identify(request))
            path = safe_name(data.path)
            if Path(path).suffix.lower() not in {
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
                ".bmp",
                ".json",
                ".jsonl",
                ".csv",
                ".txt",
                ".safetensors",
                ".zip",
            }:
                raise ValueError(
                    "Only raster, caption/config, safe-tensor and ZIP data files are accepted; executable models are rejected"
                )
            used, maximum = manager.usage()
            if used + data.size > maximum or len(manager.uploads) >= 8:
                raise ValueError("Workspace/upload capacity exceeded")
            batch = data.batch or uuid.uuid4().hex
            destination = manager.active / "imports" / batch / path
            if destination.exists():
                raise ValueError("This upload path already exists; start a new batch")
            destination.parent.mkdir(parents=True, exist_ok=True)
            identity = uuid.uuid4().hex
            temporary = destination.with_name(destination.name + "." + identity + ".part")
            temporary.touch(exist_ok=False)
            manager.uploads[identity] = {
                "size": data.size,
                "written": 0,
                "destination": destination,
                "temporary": temporary,
            }
            return {
                "id": identity,
                "batch": batch,
                "directory": str(manager.active / "imports" / batch),
            }

    @app.put("/private/files/{identity}")
    async def file_chunk(request: Request, identity: str, data: UploadChunk):
        """Append exactly the next bounded chunk and atomically publish only at the declared size."""
        async with manager.requests:
            manager.require(identify(request))
            record = manager.uploads.get(identity)
            if not record:
                raise HTTPException(404, "Upload is not active")
            try:
                content = base64.b64decode(data.content, validate=True)
            except (ValueError, binascii.Error):
                raise ValueError("Invalid upload bytes") from None
            if (
                not content
                or len(content) > 4 * 1024**2
                or data.offset != record["written"]
                or record["written"] + len(content) > record["size"]
            ):
                raise ValueError("Upload chunk is out of order or exceeds its declared size")
            with record["temporary"].open("ab") as stream:
                stream.write(content)
            record["written"] += len(content)
            complete = record["written"] == record["size"]
            if complete:
                record["temporary"].replace(record["destination"])
                del manager.uploads[identity]
            return {
                "complete": complete,
                "path": str(record["destination"]) if complete else None,
                "written": record["written"],
            }

    @app.get("/oauth/deviantart/callback")
    async def callback(request: Request):
        """Only an already-unlocked account's own one-use OAuth state can complete this explicit connector flow."""
        async with manager.requests:
            if manager.app is None:
                raise HTTPException(
                    400, "Unlock the originating account and start authorization again"
                )
            params = request.query_params
            if params.get("error") or any(len(params.getlist(k)) != 1 for k in params):
                raise ValueError("Authorization was declined or callback is invalid")
            await run_in_threadpool(
                manager.app.state.connector.finish, params.get("state", ""), params.get("code", "")
            )
            from fastapi.responses import HTMLResponse

            return HTMLResponse(
                "<!doctype html><html lang='en'><title>Account connected</title><h1>DeviantArt connected</h1><p>Return to your local studio. No images were imported automatically.</p></html>"
            )

    app.mount("/private/api", WorkspaceProxy(manager))
    if static.exists():
        app.mount("/", StaticFiles(directory=static, html=True))
    return app
