"""Build an unsigned native shell from local verified source; no system service, registry change or ML bundle."""

# Index: declarations module.main@L10; variables root@L12. Purposes/parameters: docs/code-map.json.
import subprocess
import sys
import os
from pathlib import Path


def main():
    """Bundle UI/API/worker sources with PyInstaller; fail on any build error and preserve existing data."""
    root = Path(__file__).resolve().parents[1]
    os.environ["PYINSTALLER_CONFIG_DIR"] = str(root / "build" / "pyinstaller-cache")
    if not (root / "dist" / "index.html").exists():
        raise SystemExit("Build the TypeScript UI first: npm ci && npm run build")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onedir",
            "--windowed",
            "--name",
            "PersonalImageModelStudio",
            "--distpath",
            "artifacts/desktop",
            "--workpath",
            "build/desktop",
            "--specpath",
            "build",
            "--add-data",
            f"{root / 'dist'}:dist",
            "--add-data",
            f"{root / 'studio'}:studio-source/studio",
            "--collect-all",
            "webview",
            "--exclude-module",
            "torch",
            "--exclude-module",
            "transformers",
            "--exclude-module",
            "diffusers",
            "--exclude-module",
            "numpy",
            "--exclude-module",
            "peft",
            "--exclude-module",
            "pytest",
            "--exclude-module",
            "hypothesis",
            "scripts/desktop_entry.py",
        ],
        cwd=root,
        check=True,
    )


if __name__ == "__main__":
    main()
