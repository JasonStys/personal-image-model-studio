"""Jason Stys: real native owner window around the complete private image-generation workspace.
# Index: declarations module.trusted_interpreter@L22, module.main@L38, main.factory@L73; variables permitted@L22, selected@L22, path@L26, argv@L38, parser@L40, args@L46, nonce@L49, no_browser@L50, bundle@L55, root@L56, service@L56, stage@L57, identity@L59, interpreter@L62, stage@L63, root@L64, notices@L67, directory@L73, origin@L73, ui@L73, stage@L84, service@L85, window@L88. Purposes/parameters: docs/code-map.json.

Account storage and vault formats retain their original paths and schemas.
Declaration and variable locations are generated in docs/code-map.json.
"""

import argparse
import os
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from studio.native_host import LocalService, OwnerWindow
from studio.native_identity import bounded_bytes, verify_bundle, verify_gui
from studio.private_api import create_private_app
from studio.private_cli import data_directory


def trusted_interpreter(selected, permitted):
    """Retain the explicit original alternate-worker trust boundary without accepting arbitrary executable names."""
    if not selected:
        return None
    path = Path(selected).resolve(strict=True)
    if (
        not permitted
        or not path.is_file()
        or re.fullmatch(r"python(?:3(?:\.[0-9]+)?)?(?:\.exe)?", path.name, re.IGNORECASE) is None
    ):
        raise ValueError(
            "An alternate worker requires an explicitly trusted installed Python runtime"
        )
    return str(path)


def main(argv=None) -> int:
    """Verify resources before private data; retain the existing manager's OS ownership through actual service draining."""
    parser = argparse.ArgumentParser(description="Personal Image Model Studio — Jason Stys")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--worker-python")
    parser.add_argument("--trust-worker-runtime", action="store_true")
    args = parser.parse_args(argv)
    if args.port and not 1024 <= args.port <= 65535:
        parser.error("Choose automatic port 0 or a loopback port in 1024..65535")
    nonce = os.environ.get("PIMS_ACCEPTANCE_NONCE")
    no_browser = args.no_browser or os.environ.get("PIMS_NO_BROWSER") == "1"
    if nonce and (not (args.data or os.environ.get("PIMS_PRIVATE_DATA")) or not no_browser):
        parser.error(
            "Explicit acceptance requires a selected synthetic profile and no automatic browser"
        )
    bundle = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    root = service = None
    stage = "bundle-integrity"
    try:
        identity = verify_bundle(bundle)
        if not (bundle / "dist/index.html").is_file():
            raise ValueError("The complete built application UI is required")
        interpreter = trusted_interpreter(args.worker_python, args.trust_worker_runtime)
        stage = "native-display"
        root = tk.Tk()
        root.withdraw()
        verify_gui(root.tk, identity)
        notices = (
            bounded_bytes(bundle / "NATIVE_NOTICES.txt", 4 * 1024**2).decode("utf-8")
            if getattr(sys, "frozen", False)
            else "Development source. Packaged downloads include the actual Python, Tcl/Tk and dependency notices."
        )

        def factory(directory, origin, ui):
            """Use only the port of the already-owned literal loopback socket and the original account manager."""
            return create_private_app(
                directory,
                int(origin.rsplit(":", 1)[1]),
                ui,
                interpreter,
                bool(getattr(sys, "frozen", False)) and interpreter is None,
                native_identity=identity if getattr(sys, "frozen", False) else None,
            )

        stage = "private-service"
        service = LocalService(
            factory, args.data or data_directory(), bundle / "dist", port=args.port
        )
        window = OwnerWindow(root, service, open_browser=not no_browser, notices=notices)
        if nonce:
            window.acceptance_input(nonce)
        service.thread.start()
        root.deiconify()
        root.mainloop()
        return 2 if service.failed else 0
    except (OSError, ValueError, tk.TclError) as error:
        print(
            f"PIMS_STARTUP_REFUSED phase={stage} type={type(error).__name__}",
            file=sys.stderr,
            flush=True,
        )
        if root is not None and not no_browser:
            messagebox.showerror(
                "Personal Image Model Studio",
                "The application or private workspace could not be opened. Check the complete package, permissions and other running copies. Existing account and recovery data were not reset.",
                parent=root,
            )
        return 2
    finally:
        try:
            if service is not None:
                service.close()
        finally:
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass
