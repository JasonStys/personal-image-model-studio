"""Deterministic queue/recovery/runtime and worker-dispatch tests without pretending to train ML."""

# Index: declarations module.test_restart_marks_unfinished_jobs_interrupted@L12, module.test_queue_bound_cancel_and_close@L23, test_queue_bound_cancel_and_close.dispatcher@L29, module.test_unconfigured_runtime_does_not_launch@L49, module.test_worker_rejects_unknown_dispatch@L59; variables tmp_path@L12, store@L14, jobs@L17, tmp_path@L23, store@L25, jobs@L26, release@L27, directory@L29, identity@L29, record@L32, _@L37, records@L37, tmp_path@L49, jobs@L51, tmp_path@L59. Purposes/parameters: docs/code-map.json.
import threading
import pytest
from studio.jobs import Jobs
from studio.store import Store
from studio.worker import run
from studio.files import atomic_json, read_json


def test_restart_marks_unfinished_jobs_interrupted(tmp_path):
    """Recovery does not silently retrain or replace an old finished result."""
    store = Store(tmp_path)
    store.put("job", "unfinished", {"id": "unfinished", "status": "running"})
    store.put("job", "finished", {"id": "finished", "status": "completed"})
    jobs = Jobs(store)
    assert store.get("job", "unfinished")["status"] == "interrupted"
    assert store.get("job", "finished")["status"] == "completed"
    jobs.close()


def test_queue_bound_cancel_and_close(tmp_path):
    """Block a test dispatcher, fill exactly eight slots, and reject further work without file leakage."""
    store = Store(tmp_path)
    jobs = Jobs(store)
    release = threading.Event()

    def dispatcher(identity, directory):
        """Test only queue lifecycle; real ML is covered by tensor and browser-worker tests."""
        release.wait(10)
        record = store.get("job", identity)
        store.put("job", identity, {**record, "status": "cancelled"})

    jobs.execute = dispatcher
    try:
        records = [jobs.submit("test-fixture", {}, {}) for _ in range(8)]
        with pytest.raises(ValueError, match="full"):
            jobs.submit("ninth", {}, {})
        jobs.cancel(records[0]["id"])
        assert (store.root / "jobs" / records[0]["id"] / "cancel").exists()
    finally:
        release.set()
        jobs.close()
    with pytest.raises(ValueError):
        jobs.submit("closed", {}, {})


def test_unconfigured_runtime_does_not_launch(tmp_path):
    """A portable shell with no selected ML interpreter provides a useful validation error."""
    jobs = Jobs(Store(tmp_path), "")
    try:
        with pytest.raises(ValueError, match="runtime"):
            jobs.submit("train", {}, {})
    finally:
        jobs.close()


def test_worker_rejects_unknown_dispatch(tmp_path):
    """No user-supplied task name can become executable code or a shell command."""
    atomic_json(tmp_path / "request.json", {"kind": "unexpected", "config": {}, "references": {}})
    run(tmp_path)
    assert read_json(tmp_path / "result.json")["status"] == "failed"
