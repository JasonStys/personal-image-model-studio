"""Jason Stys: preserve real browser coverage and exact nonroot runner environment identities."""
# Index: declarations module.test_complete_browser_image_matches_the_locked_package_and_preserves_all_engines@L11, module.test_validation_and_release_use_the_same_real_native_host_probe@L30; variables ROOT@L8, source@L13, browser@L14, version@L15, configuration@L25, name@L26, filename@L32, source@L33. Purposes/parameters: docs/code-map.json.

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_complete_browser_image_matches_the_locked_package_and_preserves_all_engines():
    """A browser update must review its nonroot image as well as the package lock; no engine disappears."""
    source = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
    browser = source.split("  browsers:\n", 1)[1].split("  machine-learning:\n", 1)[0]
    version = json.loads((ROOT / "package-lock.json").read_text())["packages"][
        "node_modules/playwright-core"
    ]["version"]
    assert f"image: mcr.microsoft.com/playwright:v{version}-noble@sha256:" in browser
    assert "options: --user 1001" in browser
    assert "node scripts/check_browser_host.mjs chromium firefox webkit" in browser
    assert "npm run test:browser" in browser and "npm run test:private" in browser
    assert "install-deps" not in source and "--with-deps" not in source
    assert "PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS" not in source
    assert "RUN_ML_BROWSER: '1'" in source and "RUN_PRIVATE_ML_BROWSER: '1'" in source
    configuration = (ROOT / "playwright.config.ts").read_text(encoding="utf-8")
    for name in ("chromium", "firefox", "webkit", "mobile"):
        assert f'name: "{name}"' in configuration


def test_validation_and_release_use_the_same_real_native_host_probe():
    """Both build paths require actual launches; the existing three-platform native tests remain intact."""
    for filename in ("native-validation.yml", "release-native.yml"):
        source = (ROOT / ".github/workflows" / filename).read_text(encoding="utf-8")
        assert "run: node scripts/check_browser_host.mjs chromium" in source
        assert "install-deps" not in source and "--with-deps" not in source
        assert "PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS" not in source
        assert "os: [ubuntu-24.04, windows-latest, macos-latest]" in source
        assert source.count("python scripts/native_acceptance.py --built-directory release") == 3
        assert source.count("tests/test_native_notices.py tests/test_runtime_terms.py -q") == 3
