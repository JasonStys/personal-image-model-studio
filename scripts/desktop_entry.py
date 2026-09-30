"""Frozen portable desktop entry; ML stays in an explicit separately configured trusted Python runtime."""

# Index: declarations none; variables none. Purposes/parameters: docs/code-map.json.
import sys
from studio.cli import main


if __name__ == "__main__":
    sys.argv.append("--desktop")
    main()
