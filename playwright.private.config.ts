/** Jason Stys: real private accounts on independent profile databases, plus a separate genuine ML UI lane. */
// Index: declarations none; variables python@L4, profiles@L7, profile@L17, profile@L20, index@L20, profile@L41, profile@L45. Purposes/parameters: docs/code-map.json.
import { defineConfig, devices } from "@playwright/test";
const python =
  process.env.IMAGE_STUDIO_TEST_PYTHON ||
  (process.platform === "win32" ? ".venv/Scripts/python.exe" : "python");
const profiles = [
  { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  { name: "firefox", use: { ...devices["Desktop Firefox"] } },
  { name: "webkit", use: { ...devices["Desktop Safari"] } },
  {
    name: "mobile",
    use: { ...devices["iPhone 13"], defaultBrowserType: "chromium" as const },
  },
]
  .filter(
    (profile) =>
      process.env.RUN_PRIVATE_ML_BROWSER !== "1" || profile.name === "chromium",
  )
  .map((profile, index) => ({
    ...profile,
    port: Number(process.env.PIMS_QA_FIRST_PORT || 8060) + index,
  }));
export default defineConfig({
  testDir: "tests",
  testMatch:
    process.env.RUN_PRIVATE_ML_BROWSER === "1"
      ? "private-ml.spec.ts"
      : "private.spec.ts",
  workers: 1,
  fullyParallel: false,
  timeout: 90000,
  // A complete encrypted snapshot may delay metadata responses on a busy CPU/disk.
  // Keep every assertion intact and fail slow operations without retries.
  expect: { timeout: 30000 },
  reporter: [
    ["list"],
    ["json", { outputFile: "artifacts/private-browser-results.json" }],
  ],
  use: { trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: profiles.map((profile) => ({
    name: profile.name,
    use: { ...profile.use, baseURL: "http://127.0.0.1:" + profile.port },
  })),
  webServer: profiles.map((profile) => ({
    command: `"${python}" scripts/private_browser_server.py`,
    env: { PIMS_QA_PORT: String(profile.port) },
    url: "http://127.0.0.1:" + profile.port + "/health",
    reuseExistingServer: false,
    timeout: 30000,
  })),
});
