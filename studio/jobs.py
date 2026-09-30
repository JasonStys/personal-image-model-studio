"""One bounded local ML worker at a time; persistent status, timeout, cancellation and safe publication."""

# Index: declarations module.Jobs@L18, Jobs.__init__@L21, Jobs.submit@L43, Jobs.cancel@L70, Jobs.execute@L77, Jobs.close@L213; variables TERMINAL@L15, interpreter@L22, self@L22, store@L22, worker_source@L22, record@L31, config@L43, kind@L43, references@L43, self@L43, j@L50, identity@L52, directory@L53, request@L55, record@L57, identity@L70, self@L70, record@L72, directory@L77, identity@L77, self@L77, record@L79, request@L84, timeout@L85, started@L86, environment@L87, key@L89, value@L89, word@L90, flags@L101, log@L103, process@L104, cancellation_started@L114, cancellation_started@L117, progress_path@L126, progress@L128, current@L129, result@L138, status@L139, model_path@L145, model@L146, image_path@L160, adapter_path@L175, adapter@L176, current@L194, current@L201, self@L213, record@L217. Purposes/parameters: docs/code-map.json.
import os
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from studio.files import atomic_json, confined, read_json
from studio.store import Store

TERMINAL = {"completed", "failed", "cancelled", "interrupted"}


class Jobs:
    """Serialize resource-heavy jobs while keeping HTTP/UI responsive; never execute applicant/user scripts."""

    def __init__(
        self, store: Store, interpreter: str | None = None, worker_source: Path | None = None
    ):
        """Recover stale statuses on restart; callers explicitly decide whether to resume a model."""
        self.store = store
        self.interpreter = interpreter if interpreter is not None else sys.executable
        self.worker_source = worker_source or Path(__file__).resolve().parents[1]
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="image-worker")
        self.lock = threading.Lock()
        self.closed = False
        for record in self.store.list("job"):
            if record["status"] not in TERMINAL:
                self.store.put(
                    "job",
                    record["id"],
                    {
                        **record,
                        "status": "interrupted",
                        "error": "Application restarted; no automatic retraining was performed",
                    },
                )

    def submit(self, kind: str, config: dict, references: dict) -> dict:
        """Admit at most eight queued/running jobs under one lock and persist before execution."""
        with self.lock:
            if not self.interpreter:
                raise ValueError(
                    "Select an installed, trusted ML Python runtime in Method & limits first"
                )
            if self.closed or sum(j["status"] not in TERMINAL for j in self.store.list("job")) >= 8:
                raise ValueError("Worker queue is full or shutting down")
            identity = uuid.uuid4().hex
            directory = self.store.root / "jobs" / identity
            directory.mkdir(parents=True)
            request = {"kind": kind, "config": config, "references": references}
            atomic_json(directory / "request.json", request)
            record = {
                "id": identity,
                "kind": kind,
                "status": "queued",
                "created": time.time(),
                "progress": {},
                "result": None,
                "error": None,
            }
            self.store.put("job", identity, record)
            self.executor.submit(self.execute, identity, directory)
            return record

    def cancel(self, identity: str) -> dict:
        """Set a job-scoped cancellation flag; no unrelated process is interrupted."""
        record = self.store.get("job", identity)
        if record["status"] not in TERMINAL:
            confined(self.store.root, f"jobs/{identity}/cancel").touch()
        return record

    def execute(self, identity: str, directory: Path) -> None:
        """Launch trusted module without shell, enforce deadline, and register only complete verified results."""
        record = self.store.get("job", identity)
        if (directory / "cancel").exists():
            self.store.put("job", identity, {**record, "status": "cancelled"})
            return
        self.store.put("job", identity, {**record, "status": "running"})
        request = read_json(directory / "request.json")
        timeout = request["config"].get("max_seconds", 300) + 180
        started = time.monotonic()
        environment = {
            key: value
            for key, value in os.environ.items()
            if not any(word in key.upper() for word in ("TOKEN", "SECRET", "PASSWORD", "API_KEY"))
        }
        environment.update(
            {
                "PYTHONPATH": str(self.worker_source),
                "PYTHONDONTWRITEBYTECODE": "1",
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "PYTHONUNBUFFERED": "1",
            }
        )
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            with (directory / "worker.log").open("w", encoding="utf-8") as log:
                process = subprocess.Popen(
                    [self.interpreter, "-m", "studio.worker", str(directory)],
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    env=environment,
                    shell=False,
                    creationflags=flags,
                )
                try:
                    cancellation_started = None
                    while process.poll() is None:
                        if (directory / "cancel").exists():
                            cancellation_started = cancellation_started or time.monotonic()
                            if time.monotonic() - cancellation_started > 15:
                                process.kill()
                                raise InterruptedError(
                                    "Worker stopped after cancellation grace period"
                                )
                        if time.monotonic() - started > timeout:
                            process.kill()
                            raise TimeoutError("Worker deadline exceeded")
                        progress_path = directory / "progress.json"
                        if progress_path.exists():
                            progress = read_json(progress_path)
                            current = self.store.get("job", identity)
                            self.store.put("job", identity, {**current, "progress": progress})
                        time.sleep(0.3)
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.wait()
            if not (directory / "result.json").exists():
                raise ValueError("Worker did not publish a result; inspect its private log")
            result = read_json(directory / "result.json", 2_000_000)
            status = result.get("status", "failed")
            if process.returncode != 0 or status not in {"completed", "cancelled"}:
                raise ValueError(result.get("error", "Worker failed"))
            if result.get("model"):
                from studio.checkpoints import verify

                model_path = confined(directory, result["model"])
                model = verify(model_path)
                self.store.put(
                    "model",
                    identity,
                    {
                        "id": identity,
                        "name": model["name"],
                        "kind": "native",
                        "path": str(model_path),
                        "details": model["validation"],
                        "resolution": model["resolution"],
                    },
                )
            if result.get("image"):
                image_path = confined(directory, result["image"])
                self.store.put(
                    "image",
                    identity,
                    {
                        "id": identity,
                        "name": "Generated image",
                        "path": str(image_path),
                        "request": request["config"],
                        "details": result["details"],
                    },
                )
            if result.get("lora"):
                from studio.files import digest

                adapter_path = confined(directory, result["lora"])
                adapter = read_json(adapter_path / "adapter.json")
                if (
                    digest(adapter_path / "pytorch_lora_weights.safetensors")
                    != adapter["weights_sha256"]
                ):
                    raise ValueError("Adapter integrity failure")
                self.store.put(
                    "model",
                    identity,
                    {
                        "id": identity,
                        "name": adapter["name"],
                        "kind": "lora",
                        "path": str(adapter_path),
                        "base": request["references"]["base"],
                        "details": adapter,
                    },
                )
            current = self.store.get("job", identity)
            self.store.put(
                "job",
                identity,
                {**current, "status": status, "result": result, "finished": time.time()},
            )
        except Exception as error:
            current = self.store.get("job", identity)
            self.store.put(
                "job",
                identity,
                {
                    **current,
                    "status": "cancelled" if isinstance(error, InterruptedError) else "failed",
                    "error": str(error)[:500],
                    "finished": time.time(),
                },
            )

    def close(self):
        """Cancel this application's active jobs and wait for cooperative workers to finish."""
        with self.lock:
            self.closed = True
            for record in self.store.list("job"):
                self.cancel(record["id"])
        self.executor.shutdown(wait=True, cancel_futures=False)
