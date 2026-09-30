/** Real-browser configuration. ML workflow tests run in a dedicated ML-equipped lane. */
// Index: declarations none; variables interpreter@L5. Purposes/parameters: docs/code-map.json.
import { defineConfig, devices } from "@playwright/test";

const interpreter =
  process.env.IMAGE_STUDIO_TEST_PYTHON ||
  (process.platform === "win32" ? ".venv/Scripts/python.exe" : "python");
export default defineConfig({
  testDir: "./tests",
  testMatch:
    process.env.RUN_ML_BROWSER === "1"
      ? "browser-ml.spec.ts"
      : "browser.spec.ts",
  workers: 1,
  timeout: 150000,
  reporter: [
    ["list"],
    ["json", { outputFile: "artifacts/browser-results.json" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:8017",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects:
    process.env.RUN_ML_BROWSER === "1"
      ? [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }]
      : [
          { name: "chromium", use: { ...devices["Desktop Chrome"] } },
          { name: "firefox", use: { ...devices["Desktop Firefox"] } },
          { name: "webkit", use: { ...devices["Desktop Safari"] } },
          { name: "mobile", use: { ...devices["iPhone 13"] } },
        ],
  webServer: {
    command: `"${interpreter}" -m studio.cli --port 8017 --data runtime/browser-${Date.now()}`,
    url: "http://127.0.0.1:8017/health",
    reuseExistingServer: false,
    timeout: 60000,
    env: { IMAGE_STUDIO_TOKEN: "test-session-" + "x".repeat(40) },
  },
});
