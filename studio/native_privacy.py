"""Jason Stys: process-only documented vendor telemetry opt-outs before frozen ML imports.
# Index: declarations none; variables none. Purposes/parameters: docs/code-map.json.

No global settings are changed. Explicit authorized model/API operations retain
their normal permission and offline-worker boundaries.
"""

import os

os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["DO_NOT_TRACK"] = "1"
