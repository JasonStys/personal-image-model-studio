"""Jason Stys: portable private-account application/CPU-worker entry; no external runtime setup for native ML."""
# Index: declarations none; variables none. Purposes/parameters: docs/code-map.json.

from multiprocessing import freeze_support

from studio.private_cli import main


if __name__ == "__main__":
    freeze_support()
    main()
