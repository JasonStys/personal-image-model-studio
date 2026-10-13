"""Jason Stys: real-account auth, crypto, scope, file-import and interrupted local-workspace regressions."""
# Index: declarations module.client@L24, module.register@L31, module.unlock@L38, module.raster@L44, module.test_real_registration_headers_and_empty_scope@L52, module.test_wrong_phrase_lock_archive_and_reload@L74, module.test_independent_accounts_and_locked_files@L99, module.test_origin_host_csrf_deny_before_mutation@L133, module.test_credentials_recovery_expiry_and_deletion@L142, module.test_expired_session@L183, module.test_upload_sequence_and_arbitrary_path_runtime_block@L191, module.test_portable_archive_names@L235, module.test_streaming_archive_integrity@L241, module.test_reserved_archive_metadata@L262, module.test_portable_snapshot_case_collision@L271, module.test_no_secret_fields_in_validation@L289, module.test_instance_lock_and_recovery_ownership@L298, module.test_recovery_disk_failure_preserves_credentials@L325, test_recovery_disk_failure_preserves_credentials.unavailable@L334; variables HEADERS@L17, PASSWORD@L18, KEY@L19, SALT@L20, tmp_path@L24, app@L26, session@L27, alias@L31, client@L31, response@L33, client@L38, key@L38, response@L40, stream@L46, image@L47, client@L52, account@L57, manager@L68, client@L74, uploaded@L78, identity@L82, manager@L84, owner@L85, archive@L88, bad@L90, client@L99, image@L103, cookies@L106, second@L113, change@L133, client@L133, result@L135, client@L142, recovery@L144, saved_cookies@L146, new_password@L147, response@L148, manager@L175, db@L179, client@L183, db@L186, client@L191, tmp_path@L191, start@L210, completed@L218, name@L235, tmp_path@L241, original@L243, archive@L246, key@L247, output@L250, damaged@L253, name@L262, tmp_path@L262, root@L264, root@L275, paths@L276, name@L277, path@L277, client@L289, result@L291, tmp_path@L298, root@L300, first@L301, client@L302, manager@L307, second@L312, client@L313, client@L325, monkeypatch@L325, recovery@L329, original@L332, args@L334, kwargs@L334, body@L339, manager@L341. Purposes/parameters: docs/code-map.json.

import base64
import io
import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from studio.private_api import create_private_app
from studio.vault import decrypt_workspace, encrypt_workspace, members, safe_name

HEADERS = {"X-PIMS-Request": "v1"}
PASSWORD = "synthetic-only-login-password-2026"
KEY = base64.b64encode(b"a" * 32).decode()
SALT = base64.b64encode(b"s" * 16).decode()


@pytest.fixture
def client(tmp_path):
    """Each test owns a new disposable service/database and never reads a real account."""
    app = create_private_app(tmp_path / "private", 8056)
    with TestClient(app, base_url="http://127.0.0.1:8056", headers=HEADERS) as session:
        yield session


def register(client, alias="fictional_one"):
    """Register empty synthetic accounts through the real service, not a mocked auth bypass."""
    response = client.post("/private/register", json={"alias": alias, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()["recovery"]


def unlock(client, key=KEY):
    """Use a fixed synthetic derived test key; browser KDF is covered separately by browser tests."""
    response = client.post("/private/unlock", json={"key": key, "salt": SALT})
    assert response.status_code == 200, response.text


def raster():
    """Owned tiny raster for privacy tests; no outside artwork or account download."""
    stream = io.BytesIO()
    with Image.new("RGB", (32, 32), "red") as image:
        image.save(stream, format="PNG")
    return base64.b64encode(stream.getvalue()).decode()


def test_real_registration_headers_and_empty_scope(client):
    """Credentials are hashed; session HttpOnly/Strict; new accounts have no inherited workspace data."""
    assert client.get("/private/api/workspace").status_code == 401
    assert client.get("/api/workspace").status_code in {404, 405}
    register(client)
    account = client.get("/private/account")
    assert account.json()["alias"] == "fictional_one"
    assert account.headers["cache-control"] == "no-store"
    assert "unsafe-inline" not in account.headers["content-security-policy"]
    unlock(client)
    assert client.get("/private/api/workspace").json() == {
        "model": [],
        "dataset": [],
        "image": [],
        "job": [],
    }
    manager = client.app.state.manager
    assert PASSWORD.encode() not in manager.accounts.path.read_bytes()
    assert client.post("/private/logout", json={}).status_code == 200
    assert client.get("/private/account").status_code == 401


def test_wrong_phrase_lock_archive_and_reload(client):
    """Only the right derived key can reopen an encrypted archive; plaintext staging disappears on lock."""
    register(client)
    unlock(client)
    uploaded = client.post(
        "/private/api/images", json={"name": "private-art-label", "content": raster()}
    )
    assert uploaded.status_code == 200, uploaded.text
    identity = uploaded.json()["id"]
    assert client.get(f"/private/api/images/{identity}/file").status_code == 200
    manager = client.app.state.manager
    owner = manager.owner
    assert client.post("/private/lock", json={}).status_code == 200
    assert not manager.active.exists()
    archive = manager.archive(owner).read_bytes()
    assert b"private-art-label" not in archive and b"\x89PNG" not in archive
    bad = client.post(
        "/private/unlock", json={"key": base64.b64encode(b"b" * 32).decode(), "salt": SALT}
    )
    assert bad.status_code == 400
    assert not manager.active.exists()
    unlock(client)
    assert client.get(f"/private/api/images/{identity}/file").status_code == 200


def test_independent_accounts_and_locked_files(client):
    """Another signed-in account cannot read or unlock the active owner's images, jobs or encrypted backup."""
    register(client)
    unlock(client)
    image = client.post(
        "/private/api/images", json={"name": "secret_one", "content": raster()}
    ).json()
    cookies = dict(client.cookies)
    client.cookies.clear()
    register(client, "fictional_two")
    assert client.get("/private/api/workspace").status_code == 423
    assert client.get(f"/private/api/images/{image['id']}/file").status_code == 423
    assert client.get("/private/backup").status_code == 404
    assert client.post("/private/unlock", json={"key": KEY, "salt": SALT}).status_code == 400
    second = dict(client.cookies)
    client.cookies.clear()
    client.cookies.update(cookies)
    assert client.post("/private/lock", json={}).status_code == 200
    client.cookies.clear()
    client.cookies.update(second)
    unlock(client)
    assert not client.get("/private/api/workspace").json()["image"]
    assert client.get(f"/private/api/images/{image['id']}/file").status_code == 404


@pytest.mark.parametrize(
    "change",
    [
        {"Origin": "https://evil.invalid"},
        {"Host": "evil.invalid"},
        {"Sec-Fetch-Site": "cross-site"},
        {"X-PIMS-Request": "bad"},
    ],
)
def test_origin_host_csrf_deny_before_mutation(client, change):
    """External origins cannot create accounts, steal inputs or execute account actions."""
    result = client.post(
        "/private/register", json={"alias": "fixture", "password": PASSWORD}, headers=change
    )
    assert result.status_code == 403
    assert PASSWORD not in result.text


def test_credentials_recovery_expiry_and_deletion(client):
    """Recovery rotates credentials/revokes sessions; password-protected deletion cascades only the owner."""
    recovery = register(client)
    unlock(client)
    saved_cookies = dict(client.cookies)
    new_password = PASSWORD + "-rotated"
    response = client.post(
        "/private/reset",
        json={"alias": "fictional_one", "password": new_password, "recovery": recovery},
    )
    assert response.status_code == 200
    assert client.get("/private/account").status_code == 401
    assert (
        client.post(
            "/private/login", json={"alias": "fictional_one", "password": PASSWORD}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/private/login", json={"alias": "fictional_one", "password": new_password}
        ).status_code
        == 200
    )
    unlock(client)
    assert (
        client.post("/private/delete", json={"password": PASSWORD, "confirm": True}).status_code
        == 401
    )
    assert (
        client.post("/private/delete", json={"password": new_password, "confirm": True}).status_code
        == 200
    )
    manager = client.app.state.manager
    assert not manager.active.exists()
    client.cookies.update(saved_cookies)
    assert client.get("/private/account").status_code == 401
    with manager.accounts.connection() as db:
        assert db.execute("SELECT count(*) FROM accounts").fetchone()[0] == 0


def test_expired_session(client):
    """Expired sessions do not gain an account or refresh themselves by polling."""
    register(client)
    with client.app.state.manager.accounts.connection() as db:
        db.execute("UPDATE sessions SET expires=?", (int(time.time()) - 1,))
    assert client.get("/private/account").status_code == 401


def test_upload_sequence_and_arbitrary_path_runtime_block(client, tmp_path):
    """Only permitted browser-chunked data enters imports; no user-selected executable or other PC path."""
    register(client)
    unlock(client)
    assert (
        client.post(
            "/private/api/datasets",
            json={"name": "attack", "paths": [str(tmp_path)], "rights": "owned"},
        ).status_code
        == 400
    )
    assert (
        client.put(
            "/private/api/runtime", json={"python": str(Path(os.sys.executable)), "trusted": True}
        ).status_code
        == 403
    )
    assert client.post("/private/files", json={"path": "../other.py", "size": 1}).status_code == 400
    assert client.post("/private/files", json={"path": "script.py", "size": 1}).status_code == 400
    start = client.post("/private/files", json={"path": "caption.txt", "size": 5}).json()
    assert (
        client.put(
            "/private/files/" + start["id"],
            json={"offset": 1, "content": base64.b64encode(b"hello").decode()},
        ).status_code
        == 400
    )
    completed = client.put(
        "/private/files/" + start["id"],
        json={"offset": 0, "content": base64.b64encode(b"hello").decode()},
    )
    assert completed.status_code == 200 and Path(completed.json()["path"]).read_bytes() == b"hello"
    assert (
        client.put(
            "/private/files/" + start["id"], json={"offset": 0, "content": "aGVsbG8="}
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "name",
    ["../escape", "a/../b", "a\\b", "/absolute", "C:/private", "a//b", "CON.txt", "a./b", "a\x00b"],
)
def test_portable_archive_names(name):
    """Reject traversal and platform-specific device/ambiguous paths before extraction."""
    with pytest.raises(ValueError):
        safe_name(name)


def test_streaming_archive_integrity(tmp_path):
    """Wrong keys and altered tags do not expose extracted plaintext or replace a valid existing workspace."""
    original = tmp_path / "original"
    original.mkdir()
    (original / "notes.txt").write_text("private test marker")
    archive = tmp_path / "private.pimsvault"
    key = b"x" * 32
    encrypt_workspace(original, archive, key)
    assert b"private test marker" not in archive.read_bytes()
    output = tmp_path / "restored"
    assert decrypt_workspace(archive, output, key) == str(original)
    assert (output / "notes.txt").read_text() == "private test marker"
    damaged = bytearray(archive.read_bytes())
    damaged[-1] ^= 1
    archive.write_bytes(damaged)
    with pytest.raises(Exception):
        decrypt_workspace(archive, tmp_path / "tampered", key)
    assert not (tmp_path / "tampered").exists()


@pytest.mark.parametrize("name", ["workspace-meta.json", "WORKSPACE-META.JSON"])
def test_reserved_archive_metadata(tmp_path, name):
    """Reject reserved archive names at snapshot time, before any plaintext is removed."""
    root = tmp_path / "original"
    root.mkdir()
    (root / name).write_text("Owned synthetic reserved name")
    with pytest.raises(ValueError, match="collide"):
        members(root)


def test_portable_snapshot_case_collision():
    """A case-sensitive filesystem must not produce archives that cannot reopen on Windows/macOS."""
    from unittest.mock import MagicMock

    root = MagicMock()
    paths = [MagicMock(), MagicMock()]
    for path, name in zip(paths, ("images/A.png", "images/a.png"), strict=True):
        path.is_symlink.return_value = False
        path.is_junction.return_value = False
        path.is_file.return_value = True
        path.name = "art.png"
        path.relative_to.return_value.as_posix.return_value = name
        path.stat.return_value.st_size = 1
    root.rglob.return_value = paths
    with pytest.raises(ValueError, match="collide"):
        members(root)


def test_no_secret_fields_in_validation(client):
    """Pydantic errors do not echo submitted secret strings."""
    result = client.post(
        "/private/register",
        json={"alias": "invalid <script>", "password": PASSWORD, "administrator": True},
    )
    assert result.status_code == 422 and PASSWORD not in result.text


def test_instance_lock_and_recovery_ownership(tmp_path):
    """A second service cannot share a data root; interrupted plaintext stays owner-bound and recoverable."""
    root = tmp_path / "private"
    first = create_private_app(root, 8056)
    with TestClient(first, base_url="http://127.0.0.1:8056", headers=HEADERS) as client:
        register(client)
        unlock(client)
        with pytest.raises(ValueError):
            create_private_app(root, 8057)
        manager = first.state.manager
        # Simulate interrupted shutdown without silently deleting the owner's working data.
        manager.app.state.jobs.close()
        manager.app.state.connector.close()
        manager.owner, manager.key, manager.app = None, None, None
    second = create_private_app(root, 8056)
    with TestClient(second, base_url="http://127.0.0.1:8056", headers=HEADERS) as client:
        assert (
            client.post(
                "/private/login", json={"alias": "fictional_one", "password": PASSWORD}
            ).status_code
            == 200
        )
        unlock(client)
        assert client.post("/private/lock", json={}).status_code == 200
        assert not second.state.manager.active.exists()


def test_recovery_disk_failure_preserves_credentials(client, monkeypatch):
    """A snapshot failure keeps the old password/code and plaintext recovery files available for retry."""
    import studio.private_workspace as workspace

    recovery = register(client)
    unlock(client)
    (client.app.state.manager.active / "unsaved.txt").write_text("Synthetic unsaved change")
    original = workspace.encrypt_workspace

    def unavailable(*args, **kwargs):
        """Simulate only the disposable account's encrypted snapshot failure."""
        raise OSError("Synthetic disk failure")

    monkeypatch.setattr(workspace, "encrypt_workspace", unavailable)
    body = {"alias": "fictional_one", "password": PASSWORD + "-new", "recovery": recovery}
    assert client.post("/private/reset", json=body).status_code == 400
    manager = client.app.state.manager
    assert manager.active.exists() and manager.key is not None
    assert manager.accounts.login("fictional_one", PASSWORD)
    assert manager.accounts.login("fictional_one", PASSWORD + "-new") is None
    monkeypatch.setattr(workspace, "encrypt_workspace", original)
    assert client.post("/private/reset", json=body).status_code == 200
    assert not manager.active.exists()
