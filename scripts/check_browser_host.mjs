/** Jason Stys: launch each exact locked browser and fail closed on absent host dependencies; no profile or provider access. */
// Index: declarations none; variables engines@L9, requested@L10, name@L12, lock@L14, installed@L15, temporary@L22, name@L26, engine@L27, browser@L34, page@L36. Purposes/parameters: docs/code-map.json.
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { chromium, firefox, webkit } from "@playwright/test";

const engines = { chromium, firefox, webkit };
const requested = process.argv.slice(2);
assert(requested.length > 0 && new Set(requested).size === requested.length);
assert(requested.every((name) => Object.hasOwn(engines, name)));
assert(!process.env.PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS);
const lock = JSON.parse(await fs.readFile("package-lock.json", "utf8"));
const installed = JSON.parse(
  await fs.readFile("node_modules/playwright-core/package.json", "utf8"),
);
assert.equal(
  installed.version,
  lock.packages["node_modules/playwright-core"].version,
);
const temporary = await fs.mkdtemp(
  path.join(os.tmpdir(), "pims-browser-host-"),
);
try {
  for (const name of requested) {
    const engine = engines[name];
    // A real missing executable must fail. Never accept a caught failure of the
    // subsequent ordinary launch, and never bypass Playwright's host validation.
    await assert.rejects(
      engine.launch({ executablePath: path.join(temporary, "absent-browser") }),
      /executable doesn't exist|Executable doesn't exist/i,
    );
    const browser = await engine.launch();
    try {
      const page = await browser.newPage();
      await page.setContent(
        '<main><label for="entry">Résumé — 123 mm</label><input id="entry"></main>',
      );
      await page.locator("#entry").fill("host dependency probe");
      assert.equal(
        await page.locator("#entry").inputValue(),
        "host dependency probe",
      );
      assert.equal(await page.locator("label").innerText(), "Résumé — 123 mm");
      console.log(
        JSON.stringify({
          browser: name,
          version: browser.version(),
          launch: "passed",
          missingExecutable: "rejected",
        }),
      );
    } finally {
      await browser.close();
    }
  }
} finally {
  // Remove only the one empty directory this probe created; no recursive cleanup.
  await fs.rmdir(temporary);
}
