"""Jason Stys: stable entry point for source-bound native portable packaging.
# Index: declarations none; variables none. Purposes/parameters: docs/code-map.json.

Implementation and parameter locations are indexed in scripts/native_package.py.
This entry selects only this checkout; it never executes uploaded application code.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.native_package import (
    main,  # noqa: E402 -- ensure the current trusted checkout precedes installed copies
)

if __name__ == "__main__":
    main()
