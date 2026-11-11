"""Jason Stys: actual loopback draining, real OS ownership and exceptional-startup resource release.
# Index: declarations module.test_actual_service_drains_held_request_before_releasing_profile@L24, test_actual_service_drains_held_request_before_releasing_profile.lifespan@L31, test_actual_service_drains_held_request_before_releasing_profile.factory@L40, test_actual_service_drains_held_request_before_releasing_profile.factory.held@L46, module.test_unstarted_actual_account_manager_is_closed_if_window_setup_fails@L94, test_unstarted_actual_account_manager_is_closed_if_window_setup_fails.factory@L97, module.test_failed_server_configuration_closes_constructed_manager_and_socket@L108, test_failed_server_configuration_closes_constructed_manager_and_socket.listener@L114, test_failed_server_configuration_closes_constructed_manager_and_socket.refused@L120; variables tmp_path@L24, entered@L26, release@L26, lock@L27, completed@L28, app@L31, directory@L40, origin@L40, ui@L40, app@L42, service@L55, response@L56, client@L57, deadline@L65, owner@L85, tmp_path@L94, directory@L97, origin@L97, ui@L97, data@L101, service@L102, second@L104, monkeypatch@L108, tmp_path@L108, closed@L110, sockets@L111, actual_socket@L112, args@L114, opened@L116, args@L120, kwargs@L120, app@L126, _@L129. Purposes/parameters: docs/code-map.json.

All listeners, profiles, inputs and held requests are owned synthetic test fixtures.
Declaration and variable locations are generated in docs/code-map.json.
"""

import socket
import threading
import time
from contextlib import asynccontextmanager
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

from studio import native_host
from studio.native_host import LocalService
from studio.private_api import create_private_app
from studio.private_workspace import InstanceLock


def test_actual_service_drains_held_request_before_releasing_profile(tmp_path):
    """Use a real Uvicorn request and OS file lock; a stop request alone cannot authorize completion."""
    entered, release = threading.Event(), threading.Event()
    lock = InstanceLock(tmp_path / "instance.lock")
    completed = []

    @asynccontextmanager
    async def lifespan(app):
        """Release the real OS profile lock only after the held request drains."""
        app.state.lifecycle_started = True
        try:
            yield
        finally:
            lock.close()
            completed.append("ownership-released")

    def factory(directory, origin, ui):
        """Construct this test’s real application with an owned synthetic profile."""
        app = FastAPI(lifespan=lifespan)
        app.state.manager = SimpleNamespace(close=lock.close)

        @app.get("/held-fixture-only")
        def held():
            """Hold the real HTTP handler behind the explicit test release gate."""
            entered.set()
            assert release.wait(5), "Owned test gate was not released"
            completed.append("request-finished")
            return {"complete": True}

        return app

    service = LocalService(factory, tmp_path, tmp_path)
    response = []
    client = threading.Thread(
        target=lambda: response.append(
            httpx.get(service.origin + "/held-fixture-only", timeout=8, trust_env=False)
        ),
        daemon=False,
    )
    try:
        service.thread.start()
        deadline = time.monotonic() + 5
        while not service.server.started and time.monotonic() < deadline:
            time.sleep(0.01)
        assert service.server.started
        client.start()
        assert entered.wait(3)
        service.request_stop()
        assert not service.done.wait(0.15) and service.thread.is_alive()
        with pytest.raises(ValueError, match="Another instance"):
            InstanceLock(tmp_path / "instance.lock")
        release.set()
        client.join(8)
        service.close()
        assert not client.is_alive() and not service.thread.is_alive()
        assert response[0].status_code == 200 and response[0].json() == {"complete": True}
        assert completed == ["request-finished", "ownership-released"]
        with pytest.raises(OSError):
            socket.create_connection(
                ("127.0.0.1", int(service.origin.rsplit(":", 1)[1])), timeout=0.5
            )
        owner = InstanceLock(tmp_path / "instance.lock")
        owner.close()
    finally:
        release.set()
        if client.ident is not None:
            client.join(8)
        service.close()


def test_unstarted_actual_account_manager_is_closed_if_window_setup_fails(tmp_path):
    """Account construction owns a real lock before the server thread starts; exceptional GUI setup must release it."""

    def factory(directory, origin, ui):
        """Construct this test’s real application with an owned synthetic profile."""
        return create_private_app(directory, int(origin.rsplit(":", 1)[1]), ui)

    data = tmp_path / "accounts"
    service = LocalService(factory, data, tmp_path / "no-ui")
    service.close()
    second = create_private_app(data, 8056, tmp_path / "no-ui")
    second.state.manager.close()


def test_failed_server_configuration_closes_constructed_manager_and_socket(tmp_path, monkeypatch):
    """Exercise the concrete failure boundary after account-manager construction and before thread creation."""
    closed = []
    sockets = []
    actual_socket = socket.socket

    def listener(*args):
        """Record the actual OS socket so exceptional cleanup can be independently asserted."""
        opened = actual_socket(*args)
        sockets.append(opened)
        return opened

    def refused(*args, **kwargs):
        """Raise the controlled configuration error after account ownership was acquired."""
        raise ValueError("synthetic invalid server configuration")

    monkeypatch.setattr(native_host.socket, "socket", listener)
    monkeypatch.setattr(native_host.uvicorn, "Config", refused)
    app = FastAPI()
    app.state.manager = SimpleNamespace(close=lambda: closed.append(True))
    with pytest.raises(ValueError, match="synthetic invalid"):
        LocalService(lambda *_: app, tmp_path, tmp_path)
    assert closed == [True] and len(sockets) == 1 and sockets[0].fileno() == -1
