"""Jason Stys: no-secret loopback account launcher and bundled CPU worker entry."""
# Index: declarations module.data_directory@L19, module.main@L32; variables base@L24, base@L26, base@L28, parser@L39, args@L45, frozen@L48, interpreter@L49, candidate@L51, interpreter@L62, bundle@L63, listener@L64, port@L67, app@L68, server@L75, thread@L87, deadline@L90, url@L97. Purposes/parameters: docs/code-map.json.

import argparse
import os
import re
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

from studio.private_api import create_private_app


def data_directory() -> Path:
    """Private per-OS data location distinct from the old single-user plaintext workspace."""
    if os.environ.get("PIMS_PRIVATE_DATA"):
        return Path(os.environ["PIMS_PRIVATE_DATA"])
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "PersonalImageModelStudioAccounts"


def main():
    """Launch one-file native CPU app or explicit source/full-runtime mode; never bind a public interface."""
    if len(sys.argv) == 3 and sys.argv[1] == "--studio-worker":
        from studio.worker import run

        run(Path(sys.argv[2]).resolve(strict=True))
        return
    parser = argparse.ArgumentParser(description="Personal Image Model Studio — Jason Stys")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--worker-python")
    parser.add_argument("--trust-worker-runtime", action="store_true")
    args = parser.parse_args()
    if args.port and not 1024 <= args.port <= 65535:
        raise SystemExit("Port must be 0 (automatic) or 1024..65535")
    frozen = bool(getattr(sys, "frozen", False))
    interpreter = None
    if args.worker_python:
        candidate = Path(args.worker_python).resolve(strict=True)
        if (
            not args.trust_worker_runtime
            or not candidate.is_file()
            or not re.fullmatch(
                r"python(?:3(?:\.[0-9]+)?)?(?:\.exe)?", candidate.name, re.IGNORECASE
            )
        ):
            raise SystemExit(
                "An alternate runtime requires --trust-worker-runtime and a trusted installed Python executable"
            )
        interpreter = str(candidate)
    bundle = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", args.port))
    listener.listen(128)
    port = listener.getsockname()[1]
    app = create_private_app(
        args.data or data_directory(),
        port,
        bundle / "dist",
        interpreter,
        frozen and interpreter is None,
    )
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            access_log=False,
            proxy_headers=False,
            limit_concurrency=50,
            timeout_keep_alive=5,
        )
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=False)
    thread.start()
    try:
        deadline = time.monotonic() + 20
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.05)
        if not server.started:
            raise SystemExit(
                "Local account service failed to start; preserve your private data directory"
            )
        url = f"http://127.0.0.1:{port}/"
        print("Personal Image Model Studio — Jason Stys:", url, flush=True)
        print(
            "Local only. Keep this process running; close it to stop the application.", flush=True
        )
        if not args.no_browser and os.environ.get("PIMS_NO_BROWSER") != "1":
            webbrowser.open(url)
        while thread.is_alive():
            thread.join(timeout=0.5)
    except KeyboardInterrupt:
        server.should_exit = True
        thread.join(timeout=30)
    finally:
        server.should_exit = True
        listener.close()


if __name__ == "__main__":
    main()
