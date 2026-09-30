"""Loopback-only authenticated API for datasets, models, job control, image history and feedback."""

# Index: declarations module.Boundary@L28, Boundary.__init__@L31, Boundary.__call__@L37, Boundary.__call__.replay@L72, Boundary.__call__.private_send@L80, module.Upload@L98, module.Policy@L106, module.AccountConnect@L113, module.GalleryImport@L120, module.RuntimeChoice@L130, module.create_app@L138, create_app.lifespan@L158, create_app.invalid@L176, create_app.bad_value@L184, create_app.missing@L189, create_app.file_error@L194, create_app.account_status@L199, create_app.account_connect@L204, create_app.account_disconnect@L209, create_app.account_callback@L215, create_app.account_import@L226, create_app.feedback_export@L244, create_app.health@L253, create_app.runtime_status@L258, create_app.runtime_choice@L263, create_app.workspace@L280, create_app.dataset@L285, create_app.synthetic@L302, create_app.glossary@L318, create_app.glossary_save@L323, create_app.model@L349, create_app.upload@L381, create_app.image_file@L409, create_app.training@L418, create_app.generation@L438, create_app.cancellation@L457, create_app.report@L462, create_app.feedback_save@L470, create_app.feedback_read@L476, create_app.policy_save@L481; variables app@L31, port@L31, self@L31, token@L31, receive@L37, scope@L37, self@L37, send@L37, headers@L41, k@L41, v@L41, size@L55, chunks@L56, message@L58, chunk@L61, size@L62, consumed@L70, consumed@L76, message@L80, model_config@L101, name@L102, content@L103, model_config@L109, denied_terms@L110, model_config@L116, client_id@L117, model_config@L123, name@L124, max_items@L125, rights_confirmed@L126, provider_terms_reviewed@L127, model_config@L133, python@L134, trusted@L135, root@L139, token@L140, port@L141, static@L142, interpreter@L143, connector_transport@L144, worker_source@L145, store@L148, interpreter@L151, jobs@L154, connector@L155, app@L158, app@L164, error@L176, request@L176, e@L179, error@L184, request@L184, error@L189, request@L189, error@L194, request@L194, data@L204, request@L215, params@L217, key@L218, data@L226, identity@L228, path@L229, result@L230, record@L231, data@L263, path@L265, job@L273, kind@L282, data@L285, identity@L287, path@L288, result@L289, record@L290, identity@L304, path@L305, result@L306, record@L307, identity@L318, body@L323, identity@L323, entries@L325, term@L328, value@L328, path@L344, data@L349, path@L351, details@L355, summary@L356, summary@L364, identity@L368, result@L369, data@L381, content@L384, identity@L387, directory@L388, temporary@L390, path@L391, image@L394, record@L398, identity@L409, settings@L418, references@L420, identity@L422, resumed@L426, base@L431, settings@L438, compiled@L440, policy@L441, selected@L443, references@L444, identity@L457, identity@L462, job@L464, feedback@L470, identity@L470, identity@L476, policy@L481, term@L483, static@L488. Purposes/parameters: docs/code-map.json.
import base64
import binascii
import secrets
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from studio.contracts import DatasetImport, Generation, Training, Feedback, ModelImport
from studio.datasets import import_dataset, synthetic_dataset
from studio.files import normalized_image, read_json, atomic_json
from studio.jobs import Jobs, TERMINAL
from studio.prompts import compile_prompt, enforce_policy
from studio.store import Store
from studio.deviantart import DeviantArt
from studio.feedback import export_feedback
from studio.formats import inspect_diffusers


class Boundary:
    """Authenticate before body parsing and restrict Host/Origin and total request bytes."""

    def __init__(self, app, token: str, port: int):
        """Bind a strong private process token and exact localhost origin."""
        if len(token) < 32:
            raise ValueError("Session token must contain at least 32 characters")
        self.app, self.token, self.host = app, token, f"127.0.0.1:{port}"

    async def __call__(self, scope, receive, send):
        """Validate headers and incrementally cap bodies before FastAPI receives input."""
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
        if (
            headers.get("host") != self.host
            or headers.get("origin", f"http://{self.host}") != f"http://{self.host}"
        ):
            return await JSONResponse({"detail": "Untrusted local origin"}, 403)(
                scope, receive, send
            )
        if scope["path"].startswith("/api/") and not secrets.compare_digest(
            headers.get("authorization", ""), "Bearer " + self.token
        ):
            return await JSONResponse({"detail": "Authorize this local session"}, 401)(
                scope, receive, send
            )
        size = 0
        chunks = []
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > 8 * 1024 * 1024:
                return await JSONResponse({"detail": "Request exceeds 8 MiB"}, 413)(
                    scope, receive, send
                )
            chunks.append(chunk)
            if not message.get("more_body"):
                break
        consumed = False

        async def replay():
            """Replay one bounded body; preserve the real receiver for later disconnect checks."""
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        async def private_send(message):
            """Apply private cache and browser isolation headers to every normal response."""
            if message["type"] == "http.response.start":
                message["headers"] += [
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-frame-options", b"DENY"),
                    (
                        b"content-security-policy",
                        b"default-src 'self'; img-src 'self' blob:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'",
                    ),
                ]
            await send(message)

        await self.app(scope, replay, private_send)


class Upload(BaseModel):
    """Single base64 raster upload; filenames are labels, never filesystem paths."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    content: str = Field(max_length=7_000_000)


class Policy(BaseModel):
    """Local transparent phrase blocks, not a semantic/visual safety classifier."""

    model_config = ConfigDict(extra="forbid")
    denied_terms: list[str] = Field(default_factory=list, max_length=100)


class AccountConnect(BaseModel):
    """Public application identifier only; this application never accepts a website password/secret."""

    model_config = ConfigDict(extra="forbid")
    client_id: str = Field(pattern=r"^[0-9]{1,12}$")


class GalleryImport(BaseModel):
    """An own-gallery sample needs separate training-rights and provider-terms confirmation."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)
    max_items: int = Field(default=24, ge=1, le=96)
    rights_confirmed: Literal[True]
    provider_terms_reviewed: Literal[True]


class RuntimeChoice(BaseModel):
    """Explicit operator-selected trusted Python executable, never shell text or interpreter arguments."""

    model_config = ConfigDict(extra="forbid")
    python: str = Field(min_length=1, max_length=1024)
    trusted: Literal[True]


def create_app(
    root: Path,
    token: str,
    port: int = 8016,
    static: Path | None = None,
    interpreter: str | None = None,
    connector_transport=None,
    worker_source: Path | None = None,
):
    """Construct a single-user private workspace without changing other apps or requesting cloud credentials."""
    store = Store(root)
    if interpreter is None:
        try:
            interpreter = store.get("runtime", "worker")["python"]
        except KeyError:
            pass
    jobs = Jobs(store, interpreter, worker_source)
    connector = DeviantArt(port, connector_transport)

    @asynccontextmanager
    async def lifespan(app):
        """Cancel only this workspace's workers at shutdown; preserve all completed artifacts."""
        yield
        jobs.close()
        connector.close()

    app = FastAPI(
        title="Personal Image Model Studio",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.store, app.state.jobs = store, jobs
    app.state.connector = connector
    app.add_middleware(Boundary, token=token, port=port)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, error):
        """Return concise validation messages without echoing base64 images or private prompts."""
        return JSONResponse(
            {"detail": "Invalid input: " + "; ".join(str(e["msg"])[:150] for e in error.errors())},
            422,
        )

    @app.exception_handler(ValueError)
    async def bad_value(request, error):
        """Surface bounded known application errors; no stack traces in browser responses."""
        return JSONResponse({"detail": str(error)[:500]}, 400)

    @app.exception_handler(KeyError)
    async def missing(request, error):
        """Unknown object identities yield a generic 404."""
        return JSONResponse({"detail": "Record not found"}, 404)

    @app.exception_handler(OSError)
    async def file_error(request, error):
        """Invalid/inaccessible files must not expose machine paths or traceback text to the browser."""
        return JSONResponse({"detail": "Selected file is invalid or unavailable"}, 400)

    @app.get("/api/connectors/deviantart")
    def account_status():
        """Return public connection state without credentials."""
        return connector.status()

    @app.post("/api/connectors/deviantart/connect")
    def account_connect(data: AccountConnect):
        """Provide an official browser authorization link for a registered public application."""
        return connector.begin(data.client_id)

    @app.post("/api/connectors/deviantart/disconnect")
    def account_disconnect():
        """Forget this process's credentials; provider-side revocation is a separate user action."""
        connector.disconnect()
        return connector.status()

    @app.get("/oauth/deviantart/callback")
    def account_callback(request: Request):
        """Authenticate the provider callback by one-use state rather than the app's private bearer token."""
        params = request.query_params
        if any(len(params.getlist(key)) != 1 for key in params) or params.get("error"):
            raise ValueError("Authorization failed or callback has duplicate fields; start again")
        connector.finish(params.get("state", ""), params.get("code", ""))
        return HTMLResponse(
            "<!doctype html><html lang='en'><title>Account connected</title><body><h1>DeviantArt connected</h1><p>Close this tab and return to Image Model Studio. No gallery was downloaded or trained automatically.</p></body></html>"
        )

    @app.post("/api/connectors/deviantart/import")
    def account_import(data: GalleryImport):
        """Normalize an explicit bounded own-gallery sample, retain labels and separate AI-origin records."""
        identity = uuid.uuid4().hex
        path = store.root / "datasets" / identity
        result = connector.gallery(path, data.name, data.max_items)
        record = {
            "id": identity,
            "name": data.name,
            "path": str(path),
            "counts": result["counts"],
            "fingerprint": result["fingerprint"],
            "connector": result["connector"],
        }
        store.put("dataset", identity, record)
        store.quarantine(identity, result["records"])
        return record

    @app.get("/api/feedback/export")
    def feedback_export():
        """Download explicitly consenting feedback data; generated images stay labelled AI-origin."""
        return Response(
            export_feedback(store),
            media_type="application/zip",
            headers={"content-disposition": 'attachment; filename="feedback-data.zip"'},
        )

    @app.get("/health")
    def health():
        """Return process readiness without exposing workspace data or token."""
        return {"ready": True}

    @app.get("/api/runtime")
    def runtime_status():
        """Show which private local interpreter will run trusted ML modules."""
        return {"python": jobs.interpreter, "configured": bool(jobs.interpreter)}

    @app.put("/api/runtime")
    def runtime_choice(data: RuntimeChoice):
        """Change future worker executable only while idle, with explicit local trust acknowledgement."""
        path = Path(data.python).resolve(strict=True)
        if not path.is_file() or not re.fullmatch(
            r"python(?:3(?:\.[0-9]+)?)?(?:\.exe)?", path.name, re.IGNORECASE
        ):
            raise ValueError(
                "Choose an installed trusted Python executable, not a command or script"
            )
        with jobs.lock:
            if any(job["status"] not in TERMINAL for job in store.list("job")):
                raise ValueError("Finish/cancel queued jobs before changing the ML runtime")
            jobs.interpreter = str(path)
            store.put("runtime", "worker", {"python": str(path)})
        return {"configured": True}

    @app.get("/api/workspace")
    def workspace():
        """Return bounded model/dataset/image/job metadata to the authenticated local tab."""
        return {kind: store.list(kind) for kind in ("model", "dataset", "image", "job")}

    @app.post("/api/datasets")
    def dataset(data: DatasetImport):
        """Import explicit rights-approved directories/ZIPs and retain AI quarantine metadata separately."""
        identity = uuid.uuid4().hex
        path = store.root / "datasets" / identity
        result = import_dataset(data.paths, path, data.name)
        record = {
            "id": identity,
            "name": data.name,
            "path": str(path),
            "counts": result["counts"],
            "fingerprint": result["fingerprint"],
        }
        store.put("dataset", identity, record)
        store.quarantine(identity, result["records"])
        return record

    @app.post("/api/datasets/synthetic")
    def synthetic():
        """Create and register owned procedural data for a genuine offline training test."""
        identity = uuid.uuid4().hex
        path = store.root / "datasets" / identity
        result = synthetic_dataset(path)
        record = {
            "id": identity,
            "name": result["name"],
            "path": str(path),
            "counts": result["counts"],
            "fingerprint": result["fingerprint"],
        }
        store.put("dataset", identity, record)
        return record

    @app.get("/api/datasets/{identity}/glossary")
    def glossary(identity: str):
        """Read operator-reviewed tag meanings stored inside the chosen dataset."""
        return read_json(Path(store.get("dataset", identity)["path"]) / "glossary.json")

    @app.put("/api/datasets/{identity}/glossary")
    def glossary_save(identity: str, body: dict):
        """Persist reviewed definitions with citations; never label a web search result verified automatically."""
        entries = body.get("entries", {})
        if set(body) != {"entries"} or not isinstance(entries, dict) or len(entries) > 200:
            raise ValueError("Expected at most 200 glossary entries")
        for term, value in entries.items():
            if (
                not isinstance(term, str)
                or len(term) > 100
                or not isinstance(value, dict)
                or set(value) != {"definition", "source", "reviewed"}
            ):
                raise ValueError("Glossary entries need definition, source and reviewed fields")
            if (
                not isinstance(value["definition"], str)
                or len(value["definition"]) > 1000
                or not isinstance(value["source"], str)
                or len(value["source"]) > 1000
                or type(value["reviewed"]) is not bool
            ):
                raise ValueError("Invalid glossary fields")
        path = Path(store.get("dataset", identity)["path"]) / "glossary.json"
        atomic_json(path, {"schema": 1, "entries": entries})
        return {"saved": True}

    @app.post("/api/models")
    def model(data: ModelImport):
        """Register an operator-selected verified local model; never downloads or executes custom model code."""
        path = Path(data.path).resolve(strict=True)
        if data.kind == "native":
            from studio.checkpoints import verify

            details = verify(path)
            summary = {
                "resolution": details["resolution"],
                "trained_steps": details["trained_steps"],
                **details["validation"],
            }
        else:
            # Inspect model JSON/files without importing the heavy ML stack in the server process.
            inspect_diffusers(path)
            summary = {
                "family": "classic Stable Diffusion",
                "inspection": "Fixed component classes and safe tensor files inspected; worker validates tensor loading",
            }
        identity = uuid.uuid4().hex
        result = {
            "id": identity,
            "name": data.name,
            "kind": data.kind,
            "path": str(path),
            "license_note": data.license_note,
            "details": summary,
        }
        store.put("model", identity, result)
        return result

    @app.post("/api/images")
    def upload(data: Upload):
        """Normalize one raster input into a private generated-identity PNG and strip EXIF metadata."""
        try:
            content = base64.b64decode(data.content, validate=True)
        except (binascii.Error, ValueError):
            raise ValueError("Invalid base64 image") from None
        identity = uuid.uuid4().hex
        directory = store.root / "images"
        directory.mkdir(exist_ok=True)
        temporary = directory / f"{identity}.upload"
        path = directory / f"{identity}.png"
        try:
            temporary.write_bytes(content)
            with normalized_image(temporary) as image:
                image.save(path)
        finally:
            temporary.unlink(missing_ok=True)
        record = {
            "id": identity,
            "name": data.name,
            "path": str(path),
            "request": None,
            "details": {"source": "user-upload"},
        }
        store.put("image", identity, record)
        return record

    @app.get("/api/images/{identity}/file")
    def image_file(identity: str):
        """Serve only registered local image artifacts behind the private session boundary."""
        return FileResponse(
            store.get("image", identity)["path"],
            media_type="image/png",
            filename=f"image-{identity}.png",
        )

    @app.post("/api/train")
    def training(settings: Training):
        """Validate selections before admitting a real training job; no placeholder training exists."""
        references = {
            "datasets": [
                store.get("dataset", identity)["path"] for identity in settings.dataset_ids
            ]
        }
        if settings.resume_model_id:
            resumed = store.get("model", settings.resume_model_id)
            if resumed["kind"] != "native":
                raise ValueError("Native resume needs a native checkpoint")
            references["resume"] = resumed["path"]
        if settings.base_model_id:
            base = store.get("model", settings.base_model_id)
            if base["kind"] != "diffusers":
                raise ValueError("LoRA needs a registered classic SD base")
            references["base"] = base["path"]
        return jobs.submit("train", settings.model_dump(), references)

    @app.post("/api/generate")
    def generation(settings: Generation):
        """Compile numeric weights, enforce local policy and queue a supported learned inference job."""
        compiled = compile_prompt(settings.prompt.model_dump())
        policy = store.list("policy", 1)
        enforce_policy(compiled, policy[0]["denied_terms"] if policy else [])
        selected = store.get("model", settings.model_id)
        references = {
            "model_kind": selected["kind"],
            "model": selected.get("base", selected["path"]),
        }
        if selected["kind"] == "lora":
            references["adapter"] = selected["path"]
        if settings.image_id:
            references["source"] = store.get("image", settings.image_id)["path"]
        if settings.mask_id:
            references["mask"] = store.get("image", settings.mask_id)["path"]
        return jobs.submit("generate", settings.model_dump(), references)

    @app.post("/api/jobs/{identity}/cancel")
    def cancellation(identity: str):
        """Cancel one known workspace job; completed results remain intact."""
        return jobs.cancel(identity)

    @app.get("/api/jobs/{identity}/report")
    def report(identity: str):
        """Download an auditable job report; source paths/prompts are private and not telemetry."""
        job = store.get("job", identity)
        return JSONResponse(
            job, headers={"content-disposition": f'attachment; filename="job-{identity}.json"'}
        )

    @app.post("/api/images/{identity}/feedback")
    def feedback_save(identity: str, feedback: Feedback):
        """Store human notes and consent; a new revision/training run must be explicitly requested."""
        store.add_feedback(identity, feedback.model_dump())
        return {"saved": True}

    @app.get("/api/images/{identity}/feedback")
    def feedback_read(identity: str):
        """Return recorded human feedback without fabricating model-generated scores."""
        return store.feedback(identity)

    @app.put("/api/policy")
    def policy_save(policy: Policy):
        """Configure simple transparent phrase rules without claiming semantic enforcement."""
        if any(not term.strip() or len(term) > 100 for term in policy.denied_terms):
            raise ValueError("Policy phrases must be 1..100 characters")
        store.put("policy", "local", policy.model_dump())
        return {"saved": True}

    static = static or Path(__file__).resolve().parents[1] / "dist"
    if static.exists():
        app.mount("/", StaticFiles(directory=static, html=True), name="ui")
    return app
