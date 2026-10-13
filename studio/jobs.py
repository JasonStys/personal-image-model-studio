"""One bounded local ML worker at a time; persistent status, timeout, cancellation and safe publication."""

# Index: declarations module.Jobs@L19, Jobs.__init__@L22, Jobs.submit@L45, Jobs.cancel@L72, Jobs.execute@L79, Jobs.close@L246; variables TERMINAL@L16, interpreter@L23, self@L23, store@L23, worker_source@L23, record@L33, config@L45, kind@L45, references@L45, self@L45, j@L52, identity@L54, directory@L55, request@L57, record@L59, identity@L72, self@L72, record@L74, directory@L79, identity@L79, self@L79, record@L81, request@L86, timeout@L87, started@L88, permitted_environment@L89, environment@L111, key@L112, value@L112, flags@L128, log@L130, process@L131, cancellation_started@L145, cancellation_started@L148, progress_path@L157, progress@L159, current@L160, result@L171, status@L172, model_path@L178, model@L179, image_path@L193, adapter_path@L208, adapter@L209, current@L227, current@L234, self@L246, record@L250. Purposes/parameters: docs/code-map.json.
import os
import subprocess
import sys
import threading
import time
import uuid
import psutil
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
        self.embedded = False
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
        permitted_environment = {
            "PATH",
            "PATHEXT",
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
            "HOME",
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
            "VIRTUAL_ENV",
            "LD_LIBRARY_PATH",
            "DYLD_LIBRARY_PATH",
            "OMP_NUM_THREADS",
            "MKL_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "CUDA_VISIBLE_DEVICES",
            "CUDA_PATH",
            "CUDA_HOME",
            "NVIDIA_VISIBLE_DEVICES",
        }
        environment = {
            key: value for key, value in os.environ.items() if key.upper() in permitted_environment
        }
        environment.update(
            {
                "PYTHONPATH": str(self.worker_source),
                "PYTHONDONTWRITEBYTECODE": "1",
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "PYTHONUNBUFFERED": "1",
                "PIMS_PARENT_GUARD": "1",
                "PIMS_PARENT_PID": str(os.getpid()),
                "PIMS_PARENT_STARTED": str(psutil.Process().create_time()),
                "HF_HUB_DISABLE_TELEMETRY": "1",
                "DO_NOT_TRACK": "1",
            }
        )
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            with (directory / "worker.log").open("w", encoding="utf-8") as log:
                process = subprocess.Popen(
                    (
                        [sys.executable, "--studio-worker", str(directory)]
                        if self.embedded
                        else [self.interpreter, "-m", "studio.worker", str(directory)]
                    ),
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
                    if process.stdin:
                        process.stdin.close()
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
