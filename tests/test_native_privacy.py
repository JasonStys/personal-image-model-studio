"""Jason Stys: fresh-process vendor opt-out ordering and parent environment preservation.
# Index: declarations module.test_early_hook_overrides_conflicting_child_flags_before_vendor_import@L14; variables tmp_path@L14, root@L16, environment@L17, code@L18, result@L19. Purposes/parameters: docs/code-map.json.

No models, provider accounts, outside requests or installed app profiles are used.
Declaration and variable locations are generated in docs/code-map.json.
"""

import os
from pathlib import Path
import subprocess
import sys


def test_early_hook_overrides_conflicting_child_flags_before_vendor_import(tmp_path):
    """Inspect the actual vendor constant in a fresh interpreter, not just an authored dictionary."""
    root = Path(__file__).resolve().parents[1]
    environment = {**os.environ, "HF_HUB_DISABLE_TELEMETRY": "0", "DO_NOT_TRACK": "0"}
    code = "import os,runpy,sys; runpy.run_path(sys.argv[1]); from huggingface_hub import constants; assert constants.HF_HUB_DISABLE_TELEMETRY is True; assert os.environ['DO_NOT_TRACK']=='1'"
    result = subprocess.run(
        [sys.executable, "-c", code, str(root / "studio/native_privacy.py")],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert environment["HF_HUB_DISABLE_TELEMETRY"] == environment["DO_NOT_TRACK"] == "0"
