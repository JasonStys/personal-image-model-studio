"""Jason Stys: portable private-account application/CPU-worker entry; no external runtime setup for native ML."""
# Index: declarations none; variables none. Purposes/parameters: docs/code-map.json.

from multiprocessing import freeze_support

if __name__ == "__main__":
    freeze_support()
    import sys

    import studio.native_privacy  # noqa: F401 -- opt out before importing account/ML modules

    if len(sys.argv) == 3 and sys.argv[1] == "--studio-worker":
        from studio.private_cli import main

        main()
    else:
        from studio.native_desktop import main

        raise SystemExit(main())
