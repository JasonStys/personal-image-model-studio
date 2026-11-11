"""Jason Stys: actual Tk owner-window controls with real owned loopback requests.
# Index: declarations module.pump@L27, module.test_real_owner_help_and_all_normal_close_controls@L38, module.test_actual_quit_retains_window_and_profile_until_request_commits@L102, test_actual_quit_retains_window_and_profile_until_request_commits.factory@L107, test_actual_quit_retains_window_and_profile_until_request_commits.factory.pending@L114, test_actual_quit_retains_window_and_profile_until_request_commits.request@L129, module.test_invalid_acceptance_nonce_does_not_close_real_window@L173; variables predicate@L27, root@L27, seconds@L27, until@L29, close_control@L38, monkeypatch@L38, tmp_path@L38, service@L40, directory@L41, origin@L41, ui@L41, root@L47, window@L48, _url@L55, first_help@L60, texts@L64, frame@L66, child@L67, child@L77, nonce@L86, tmp_path@L102, _@L104, entered@L104, release@L104, returned@L104, results@L105, directory@L107, origin@L107, ui@L107, private@L109, app@L110, service@L124, root@L125, window@L126, client@L131, result@L132, worker@L136, reopened@L166, tmp_path@L173, service@L175, directory@L176, origin@L176, ui@L176, root@L182, window@L183. Purposes/parameters: docs/code-map.json.

Linux validation runs these mandatory tests under Xvfb. Windows/macOS use their
native runner display. No account directory or browser belonging to a user is
opened. All app windows and listeners are owned by this test.
"""

from __future__ import annotations

import asyncio
import io
import threading
import time
import tkinter as tk
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from studio.native_host import LocalService, OwnerWindow
from studio.private_workspace import InstanceLock
from studio.private_api import create_private_app


def pump(root: tk.Tk, predicate, seconds=8):
    """Dispatch real Tk events until observed completion; a timeout fails rather than skips."""
    until = time.monotonic() + seconds
    while not predicate():
        if time.monotonic() > until:
            raise AssertionError("Native control did not reach its observed state")
        root.update()
        time.sleep(0.01)


@pytest.mark.parametrize("close_control", ["button", "window", "stdin"])
def test_real_owner_help_and_all_normal_close_controls(tmp_path: Path, monkeypatch, close_control):
    """Real Open/Help controls and each close affordance retain the same service lifecycle."""
    service = LocalService(
        lambda directory, origin, ui: create_private_app(
            directory, int(origin.rsplit(":", 1)[1]), ui
        ),
        tmp_path / "profile",
        tmp_path,
    )
    root = tk.Tk()
    window = OwnerWindow(root, service, open_browser=False)
    service.thread.start()
    try:
        pump(root, lambda: window.ready)
        assert "Jason Stys" in root.title()
        assert not window.open_button.instate(["disabled"])
        # An unavailable browser leaves the actual local address usable.
        monkeypatch.setattr("studio.native_host.webbrowser.open", lambda _url: False)
        window.open_button.invoke()
        assert service.origin in window.status.get()
        window.help()
        root.update()
        first_help = window.help_window
        assert first_help is not None and first_help.winfo_ismapped()
        window.help()
        assert window.help_window is first_help
        texts = [
            child
            for frame in first_help.winfo_children()
            for child in frame.winfo_children()
            if isinstance(child, tk.Text)
        ]
        assert len(texts) == 1
        assert "Provider requests require explicit consent" in texts[0].get("1.0", "end")
        assert "Quit application waits for active requests" in texts[0].get("1.0", "end")
        window.show_notices()
        root.update()
        assert any(
            child.title() == "Bundled runtime notices · Jason Stys"
            for child in root.winfo_children()
            if isinstance(child, tk.Toplevel)
        )
        first_help.destroy()
        if close_control == "button":
            window.quit_button.invoke()
        elif close_control == "window":
            root.tk.call(root.protocol("WM_DELETE_WINDOW"))
        else:
            nonce = "a" * 64
            monkeypatch.setattr("studio.native_host.sys.stdin", io.StringIO(f"quit {nonce}\n"))
            window.acceptance_input(nonce)
        pump(root, lambda: service.done.is_set())
        root.update()
        assert window.closing
        assert not service.failed
        assert service.done.is_set()
    finally:
        service.close()
        try:
            root.destroy()
        except tk.TclError as error:
            assert "application has been destroyed" in str(error)


def test_actual_quit_retains_window_and_profile_until_request_commits(tmp_path: Path):
    """A real pending HTTP handler blocks Quit completion, then commits before the window/profile close."""
    entered, release, returned = (threading.Event() for _ in range(3))
    results = []

    def factory(directory, origin, ui):
        """Keep the actual account manager and lifespan around a real held test-only request."""
        private = create_private_app(directory, int(origin.rsplit(":", 1)[1]), ui)
        app = FastAPI(lifespan=private.router.lifespan_context)
        app.state.manager = private.state.manager

        @app.get("/pending")
        async def pending():
            """Commit this synthetic request before releasing real account ownership."""
            entered.set()
            while not release.is_set():
                await asyncio.sleep(0.01)
            (tmp_path / "request-commit.txt").write_text("retained")
            return {"saved": True}

        return app

    service = LocalService(factory, tmp_path / "profile", tmp_path)
    root = tk.Tk()
    window = OwnerWindow(root, service, open_browser=False)
    service.thread.start()

    def request():
        """Observe the actual held HTTP response from a separate client thread."""
        with httpx.Client(trust_env=False, timeout=10) as client:
            result = client.get(service.origin + "/pending")
            results.append((result.status_code, result.json()))
        returned.set()

    worker = threading.Thread(target=request)
    try:
        pump(root, lambda: window.ready)
        worker.start()
        pump(root, entered.is_set)
        window.quit_button.invoke()
        root.update()
        assert window.closing and root.winfo_exists()
        assert window.open_button.instate(["disabled"])
        assert window.quit_button.instate(["disabled"])
        with pytest.raises(ValueError, match="Another instance"):
            InstanceLock(tmp_path / "profile/instance.lock")
        assert not service.done.is_set()
        assert not (tmp_path / "request-commit.txt").exists()
        release.set()
        pump(root, lambda: service.done.is_set() and returned.is_set())
        root.update()
        service.close()
        assert results == [(200, {"saved": True})]
        assert (tmp_path / "request-commit.txt").read_text() == "retained"
    finally:
        release.set()
        service.close()
        if worker.ident is not None:
            worker.join(5)
        try:
            root.destroy()
        except tk.TclError as error:
            assert "application has been destroyed" in str(error)

    reopened = InstanceLock(tmp_path / "profile/instance.lock")
    try:
        assert (tmp_path / "request-commit.txt").read_text() == "retained"
    finally:
        reopened.close()


def test_invalid_acceptance_nonce_does_not_close_real_window(tmp_path: Path):
    """An invalid opt-in channel fails without starting or closing an unrelated service."""
    service = LocalService(
        lambda directory, origin, ui: create_private_app(
            directory, int(origin.rsplit(":", 1)[1]), ui
        ),
        tmp_path / "profile",
        tmp_path,
    )
    root = tk.Tk()
    window = OwnerWindow(root, service, open_browser=False)
    try:
        with pytest.raises(ValueError, match="acceptance channel"):
            window.acceptance_input("wrong")
        assert root.winfo_exists() and not window.closing
    finally:
        service.close()
        root.destroy()
