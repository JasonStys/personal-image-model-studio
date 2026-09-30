"""Browser and native desktop launchers with local data roots and private per-process session links."""

# Index: declarations module.main@L15; variables parser@L17, args@L22, frozen@L25, root@L26, data@L27, interpreter@L33, interpreter@L38, interpreter@L40, token@L41, app@L42, server@L50, url@L59, thread@L63, deadline@L65. Purposes/parameters: docs/code-map.json.
import argparse
import os
import secrets
import sys
import threading
import time
from pathlib import Path
import uvicorn
from studio.api import create_app


def main():
    """Serve a browser workspace or open its bundled native window; never binds to a public host."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path)
    parser.add_argument("--port", type=int, default=8016)
    parser.add_argument("--desktop", action="store_true")
    parser.add_argument("--worker-python", default=os.environ.get("IMAGE_STUDIO_PYTHON"))
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        raise SystemExit("Port must be 1024..65535")
    frozen = getattr(sys, "frozen", False)
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    data = args.data or (
        Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
        / "PersonalImageModelStudio"
        if frozen
        else Path("runtime/default")
    )
    interpreter = args.worker_python
    if frozen and interpreter is None:
        try:
            from studio.store import Store

            interpreter = Store(data).get("runtime", "worker")["python"]
        except KeyError:
            interpreter = ""
    token = os.environ.get("IMAGE_STUDIO_TOKEN") or secrets.token_urlsafe(32)
    app = create_app(
        data,
        token,
        args.port,
        root / "dist",
        interpreter,
        worker_source=root / "studio-source" if frozen else None,
    )
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=args.port,
            log_level="warning",
            log_config=None if frozen else uvicorn.config.LOGGING_CONFIG,
        )
    )
    url = f"http://127.0.0.1:{args.port}/#token={token}"
    if args.desktop:
        import webview

        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        deadline = time.monotonic() + 20
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.05)
        if not server.started:
            raise SystemExit("Local server failed to start; port may already be in use")
        webview.create_window(
            "Personal Image Model Studio", url, width=1280, height=880, min_size=(400, 600)
        )
        webview.start()
        server.should_exit = True
        thread.join(timeout=15)
    else:
        print("Private local session (do not publish):", url, flush=True)
        server.run()


if __name__ == "__main__":
    main()
