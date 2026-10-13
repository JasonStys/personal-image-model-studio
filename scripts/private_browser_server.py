"""Jason Stys: disposable per-profile account data; browser tests never use a real person's workspace."""
# Index: declarations none; variables directory@L12. Purposes/parameters: docs/code-map.json.

import os
import sys
import tempfile

from studio.private_cli import main


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="pims-account-browser-") as directory:
        sys.argv = [
            "private-browser-qa",
            "--no-browser",
            "--port",
            os.environ["PIMS_QA_PORT"],
            "--data",
            directory,
        ]
        main()
