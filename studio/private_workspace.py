"""Jason Stys: one account-scoped local ML workspace; locked archives and crash-safe recovery ownership."""
# Index: declarations module.InstanceLock@L25, InstanceLock.__init__@L28, InstanceLock.close@L50, module.rebase@L55, module.validate_workspace@L67, module.Workspaces@L111, Workspaces.__init__@L114, Workspaces.archive@L156, Workspaces.status@L165, Workspaces.unlock@L176, Workspaces.require@L243, Workspaces.save@L249, Workspaces.remove_active@L265, Workspaces.lock@L277, Workspaces.delete_data@L295, Workspaces.close@L307, Workspaces.usage@L315; variables path@L28, self@L28, self@L50, current@L55, old@L55, value@L55, suffix@L58, item@L61, key@L61, item@L63, original@L67, root@L67, name@L70, database@L71, database@L74, db@L76, rows@L77, identity@L80, kind@L80, text@L80, value@L83, field@L85, path@L90, request@L98, value@L99, field@L100, path@L100, selected@L103, embedded@L115, interpreter@L115, port@L115, root@L115, self@L115, static@L115, allowed@L120, p@L129, owner@L156, self@L156, c@L160, owner@L165, self@L165, config@L167, encoded@L176, owner@L176, salt@L176, self@L176, key@L184, current@L185, config@L186, plaintext@L189, nonce@L204, config@L205, original@L219, original@L221, path@L222, original@L225, owner@L243, self@L243, force@L249, self@L249, j@L254, current@L259, expected_owner@L265, self@L265, owner@L277, self@L277, app@L279, upload@L282, owner@L295, self@L295, self@L307, self@L315, p@L317, used@L317, reserved@L318, u@L318. Purposes/parameters: docs/code-map.json.

import asyncio
import base64
import json
import os
import secrets
import shutil
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from studio.accounts import Accounts, decode_field
from studio.api import create_app
from studio.files import atomic_json, confined, read_json
from studio.jobs import TERMINAL
from studio.permissions import protect_directory
from studio.vault import AAD, MAX_BYTES, decrypt_workspace, encrypt_workspace, members, signature


class InstanceLock:
    """OS advisory lock prevents a second launcher from sharing/cleaning an active plaintext workspace."""

    def __init__(self, path: Path):
        """Hold a nonblocking OS file lock until this exact application instance closes."""
        self.stream = path.open("a+b")
        self.stream.seek(0)
        self.stream.write(b"1")
        self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.stream.close()
            raise ValueError(
                "Another instance uses this account data directory; close it first"
            ) from None

    def close(self):
        """Closing the held descriptor releases only this instance's advisory lock."""
        self.stream.close()


def rebase(value, old: str, current: str):
    """Rebase only exact archived-root path prefixes; never evaluate strings or rewrite arbitrary substrings."""
    if isinstance(value, str) and value.startswith((old + "/", old + "\\")):
        suffix = value[len(old) + 1 :].replace("\\", "/")
        return str(confined(Path(current), suffix))
    if isinstance(value, dict):
        return {key: rebase(item, old, current) for key, item in value.items()}
    if isinstance(value, list):
        return [rebase(item, old, current) for item in value]
    return value


def validate_workspace(root: Path, original: str):
    """Validate restored record/reference paths before any file route or worker can use them."""
    members(root)
    for name in ("studio.sqlite", "quarantine.sqlite"):
        database = root / name
        if database.exists() and database.stat().st_size > 32 * 1024**2:
            raise ValueError("Restored metadata database exceeds its limit")
    database = root / "studio.sqlite"
    if database.exists():
        with closing(sqlite3.connect(database)) as db:
            rows = db.execute("SELECT kind,id,body FROM records LIMIT 20001").fetchall()
            if len(rows) > 20000:
                raise ValueError("Too many metadata records")
            for kind, identity, text in rows:
                if len(text) > 2_000_000:
                    raise ValueError("Restored metadata record exceeds its limit")
                value = rebase(json.loads(text), original, str(root))
                if kind in {"image", "dataset", "model"}:
                    for field in ("path", "base"):
                        if field not in value:
                            if field == "path":
                                raise ValueError("Restored artifact has no path")
                            continue
                        path = Path(value[field]).resolve()
                        if not path.is_relative_to(root) or path == root:
                            raise ValueError("Restored artifact escapes its account")
                db.execute(
                    "UPDATE records SET body=? WHERE kind=? AND id=?",
                    (json.dumps(value), kind, identity),
                )
            db.commit()
    for request in (root / "jobs").glob("*/request.json"):
        value = rebase(read_json(request), original, str(root))
        for field, path in value.get("references", {}).items():
            if field == "model_kind":
                continue
            for selected in path if isinstance(path, list) else [path]:
                if not isinstance(selected, str) or not Path(selected).resolve().is_relative_to(
                    root
                ):
                    raise ValueError("Restored worker reference escapes its account")
        atomic_json(request, value)


class Workspaces:
    """Explicit unlock/save/lock lifecycle; one active local account and no administrative read API."""

    def __init__(
        self, root: Path, port: int, static: Path, interpreter: str | None = None, embedded=False
    ):
        """Create a protected private data root without opening or migrating any legacy workspace."""
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        allowed = {
            "instance.lock",
            "accounts.sqlite",
            "accounts.sqlite-wal",
            "accounts.sqlite-shm",
            "active",
            "active-owner.json",
            "encrypted",
        }
        if any(p.name not in allowed for p in self.root.iterdir()):
            raise ValueError(
                "Choose an empty dedicated account data directory; existing unrelated files were not touched"
            )
        protect_directory(self.root)
        self.instance = InstanceLock(self.root / "instance.lock")
        self.accounts = Accounts(self.root / "accounts.sqlite")
        self.port, self.static = port, static
        self.interpreter = interpreter if interpreter is not None else sys.executable
        self.embedded = embedded
        self.active = self.root / "active"
        self.marker = self.root / "active-owner.json"
        self.archives = self.root / "encrypted"
        self.archives.mkdir(exist_ok=True, mode=0o700)
        self.owner = None
        self.key = None
        self.app = None
        self.saved_signature = None
        self.requests = asyncio.Lock()
        self.uploads = {}
        self.internal_token = secrets.token_urlsafe(32)
        if self.active.exists() != self.marker.exists():
            self.instance.close()
            raise ValueError(
                "Incomplete recovery state; preserve this data directory and contact support"
            )

    def archive(self, owner: str) -> Path:
        """Only server-assigned URL-safe owner IDs become archive names."""
        if not owner or any(
            c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
            for c in owner
        ):
            raise ValueError("Invalid internal account identity")
        return self.archives / (owner + ".pimsvault")

    def status(self, owner: str):
        """Disclose only the caller's unlocked/configured state; never the other account's alias or data."""
        config = self.accounts.vault(owner)["envelope"]
        return {
            "unlocked": self.owner == owner,
            "configured": bool(config),
            "salt": config["salt"] if config else None,
            "engine_busy": self.owner is not None and self.owner != owner,
            "recovery_pending": self.marker.exists() and self.owner is None,
        }

    def unlock(self, owner: str, encoded: str, salt: str | None):
        """Authenticate a browser-derived key, recover only this owner, then construct its genuine ML API."""
        if self.owner is not None:
            if self.owner != owner:
                raise ValueError(
                    "Another account has the local engine unlocked; it must lock first"
                )
            raise ValueError("Workspace is already unlocked; refresh this tab")
        key = decode_field(encoded, 32, 32)
        current = self.accounts.vault(owner)
        config = current["envelope"]
        if config:
            try:
                plaintext = AESGCM(key).decrypt(
                    decode_field(config["iv"], 12, 12), decode_field(config["proof"], 16, 256), AAD
                )
                if plaintext != b"local-workspace-key-v1":
                    raise ValueError()
            except Exception:
                raise ValueError(
                    "Cannot unlock: incorrect vault phrase or damaged key settings"
                ) from None
        else:
            if self.marker.exists():
                raise ValueError(
                    "An interrupted workspace belongs to another account; its owner must recover it first"
                )
            decode_field(salt or "", 16, 16)
            nonce = secrets.token_bytes(12)
            config = {
                "salt": salt,
                "iv": base64.b64encode(nonce).decode(),
                "proof": base64.b64encode(
                    AESGCM(key).encrypt(nonce, b"local-workspace-key-v1", AAD)
                ).decode(),
            }
            if not self.accounts.save(owner, config, current["revision"]):
                raise ValueError("Account changed in another tab; refresh")
        if self.marker.exists():
            if read_json(self.marker).get("owner") != owner:
                raise ValueError(
                    "An interrupted workspace belongs to another account; its owner must recover it first"
                )
            original = str(self.active)
        else:
            original = str(self.active)
            path = self.archive(owner)
            if path.exists():
                try:
                    original = decrypt_workspace(path, self.active, key)
                except Exception:
                    raise ValueError(
                        "Cannot unlock: damaged encrypted workspace. Existing archive was preserved"
                    ) from None
            else:
                self.active.mkdir(mode=0o700)
            atomic_json(self.marker, {"owner": owner})
        validate_workspace(self.active, original)
        self.app = create_app(
            self.active, self.internal_token, self.port, self.static, self.interpreter
        )
        self.app.state.jobs.embedded = self.embedded
        self.owner, self.key = owner, key
        self.saved_signature = None
        self.save(force=True)
        return self.status(owner)

    def require(self, owner: str):
        """Authorize against the authenticated cookie owner before accessing the local engine."""
        if self.owner != owner or self.app is None:
            raise ValueError("Unlock your account's workspace first")
        return self.app

    def save(self, force=False):
        """Seal idle changes only; ongoing workers/uploads continue without snapshotting inconsistent files."""
        if self.owner is None:
            return {"saved": False}
        if self.uploads or any(
            j["status"] not in TERMINAL for j in self.app.state.store.list("job")
        ):
            if force:
                raise ValueError("Finish uploads and ML jobs before taking a complete snapshot")
            return {"saved": False, "pending": True}
        current = signature(self.active)
        if current != self.saved_signature:
            encrypt_workspace(self.active, self.archive(self.owner), self.key)
            self.saved_signature = current
        return {"saved": True}

    def remove_active(self, expected_owner: str):
        """Remove only the exact managed plaintext directory after verifying its ownership marker and scope."""
        if (
            self.active.resolve() != self.root / "active"
            or self.active.is_symlink()
            or self.active.is_junction()
            or read_json(self.marker).get("owner") != expected_owner
        ):
            raise ValueError("Recovery target did not pass ownership and path checks")
        shutil.rmtree(self.active)
        self.marker.unlink()

    def lock(self, owner: str):
        """Cancel only this account's workers, save successfully, disconnect providers, then drop plaintext/key."""
        app = self.require(owner)
        app.state.jobs.close()
        app.state.connector.close()
        for upload in self.uploads.values():
            upload["temporary"].unlink(missing_ok=True)
        self.uploads.clear()
        try:
            self.save(force=True)
            self.remove_active(owner)
        except Exception:
            # Preserve key and recovery files for retry. Never erase data after a failed save.
            app.state.jobs.closed = True
            raise
        self.owner, self.key, self.app, self.saved_signature = None, None, None, None
        return {"locked": True}

    def delete_data(self, owner: str):
        """Called only after current-password verification; remove this account's live data, not other workspaces."""
        if self.owner == owner:
            self.app.state.jobs.close()
            self.app.state.connector.close()
            self.remove_active(owner)
            self.owner, self.key, self.app = None, None, None
            self.uploads.clear()
        elif self.marker.exists() and read_json(self.marker).get("owner") == owner:
            self.remove_active(owner)
        self.archive(owner).unlink(missing_ok=True)

    def close(self):
        """Clean shutdown locks the active account; a failed save remains recoverable and is not deleted."""
        try:
            if self.owner:
                self.lock(self.owner)
        finally:
            self.instance.close()

    def usage(self):
        """Bound workspace accounting, including reserved in-flight uploads, without reading file content."""
        used = sum(p.stat().st_size for p in members(self.active))
        reserved = sum(u["size"] - u["written"] for u in self.uploads.values())
        return used + reserved, MAX_BYTES
