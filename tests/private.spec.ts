/** Jason Stys: real private login, account isolation, encrypted export, file pickers, recovery and accessible help. */
// Index: declarations register@L12, unlock@L33, lock@L44; variables password@L8, phrase@L9, page@L12, alias@L17, recovery@L26, page@L33, page@L44, page@L54, destinations@L56, unlockBodies@L57, request@L58, identity@L66, event@L92, bytes@L96, url@L114, page@L133, browser@L134, context@L145, other@L146, page@L169, png@L176, archive@L180, response@L215, page@L228, identity@L230, page@L273, destinations@L276, request@L277, fixtures@L283, archive@L286, split@L287, fixture@L288, report@L322, images@L346, image@L348, downloading@L355, downloaded@L362, exported@L366, first@L380, second@L390, options@L392, option@L393, release@L395, held@L396, resolve@L396, responseReady@L399, ready@L400, resolve@L400, route@L403, response@L404, identity@L415, reopened@L446, images@L459, image@L461, url@L469. Purposes/parameters: docs/code-map.json.
import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { zipSync, strToU8 } from "fflate";
const password = "synthetic-only-test-login-password";
const phrase = "six synthetic random words protect this image workspace";

/** Create only fictional QA accounts in this profile's disposable service. */
async function register(page: Page) {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  const alias = "qa_" + randomUUID().replaceAll("-", "").slice(0, 20);
  await page.getByLabel("Account alias", { exact: true }).fill(alias);
  await page.getByLabel("Login password", { exact: true }).fill(password);
  await page
    .getByRole("button", { name: "Register account", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Save your login recovery code" }),
  ).toBeVisible();
  const recovery = await page.locator("#recovery-code").innerText();
  await page.getByRole("button", { name: "I saved it privately" }).click();
  await expect(page.getByLabel("Vault phrase", { exact: true })).toBeVisible();
  return { alias, recovery };
}

/** Browser KDF and actual local key unlock, not a mocked authentication response. */
async function unlock(page: Page) {
  await page.getByLabel("Vault phrase", { exact: true }).fill(phrase);
  await page
    .getByRole("button", { name: "Unlock or create workspace" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Give every idea its own field" }),
  ).toBeVisible();
}

/** Lock and wait for the new document, dropping the prior workspace and image blob references. */
async function lock(page: Page) {
  await page
    .getByRole("button", { name: "Lock workspace", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Unlock your private image workspace" }),
  ).toBeVisible();
}

test("real login, local key transport, accessible help and encrypted saved workspace", async ({
  page,
}) => {
  const destinations: string[] = [];
  const unlockBodies: string[] = [];
  page.on("request", (request) => {
    destinations.push(request.url());
    if (request.url().endsWith("/private/unlock"))
      unlockBodies.push(request.postData() || "");
  });
  await page.goto("/");
  await page.getByText("Help, privacy & installation", { exact: true }).click();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  const identity = await register(page);
  await unlock(page);
  expect(unlockBodies.length).toBe(1);
  expect(unlockBodies[0]).not.toContain(phrase);
  expect(Object.keys(JSON.parse(unlockBodies[0])).sort()).toEqual([
    "key",
    "salt",
  ]);
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([]);
  expect(await page.evaluate(() => Object.keys(sessionStorage))).toEqual([]);
  expect(await page.evaluate(() => document.cookie)).not.toContain(
    "pims_account",
  );
  await page
    .getByRole("button", { name: "02 · Datasets & glossary", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Create owned synthetic test dataset" })
    .click();
  await expect(page.locator("#datasets")).toContainText('"flagged": 0');
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  const event = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Download encrypted archive" })
    .click();
  const bytes = readFileSync((await (await event).path())!);
  expect(bytes.subarray(0, 8).toString()).toBe("PIMSV001");
  expect(bytes.includes(Buffer.from("red circle"))).toBeFalsy();
  await lock(page);
  await page
    .getByLabel("Vault phrase", { exact: true })
    .fill("wrong synthetic key phrase with many words");
  await page
    .getByRole("button", { name: "Unlock or create workspace" })
    .click();
  await expect(page.locator("#portal-status")).toContainText("Cannot unlock");
  await unlock(page);
  await page
    .getByRole("button", { name: "02 · Datasets & glossary", exact: true })
    .click();
  await expect(page.locator("#datasets")).toContainText('"flagged": 0');
  expect(
    destinations.every(
      (url) => new URL(url).origin === new URL(page.url()).origin,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "artifacts/private-ui-" + test.info().project.name + ".png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByLabel("Login password", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Account alias", { exact: true }).fill(identity.alias);
  await page.getByLabel("Login password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in securely" }).click();
  await unlock(page);
  await lock(page);
});

test("another account cannot read or unlock the active owner", async ({
  page,
  browser,
}) => {
  await register(page);
  await unlock(page);
  await page
    .getByRole("button", { name: "02 · Datasets & glossary", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Create owned synthetic test dataset" })
    .click();
  await expect(page.locator("#datasets")).toContainText('"flagged": 0');
  const context = await browser.newContext();
  const other = await context.newPage();
  await other.goto(page.url(), { waitUntil: "commit" });
  await register(other);
  await other.getByLabel("Vault phrase", { exact: true }).fill(phrase);
  await other
    .getByRole("button", { name: "Unlock or create workspace" })
    .click();
  await expect(other.locator("#portal-status")).toContainText(
    "Another account",
  );
  expect((await other.request.get("/private/api/workspace")).status()).toBe(
    423,
  );
  await lock(page);
  await unlock(other);
  expect(
    await (await other.request.get("/private/api/workspace")).json(),
  ).toMatchObject({ dataset: [], image: [], model: [] });
  await lock(other);
  await context.close();
});

test("selected ZIP uploads stay scoped and unsafe text remains inert", async ({
  page,
}) => {
  await register(page);
  await unlock(page);
  await page
    .getByRole("button", { name: "02 · Datasets & glossary", exact: true })
    .click();
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aLMkAAAAASUVORK5CYII=",
    "base64",
  );
  const archive = zipSync({
    "art.png": png,
    "art.txt": strToU8("owned monochrome image"),
    "art.json": strToU8(
      JSON.stringify({
        origin: "human",
        license: "Owned synthetic QA fixture",
      }),
    ),
  });
  await page.getByLabel("Dataset files / ZIP", { exact: true }).setInputFiles({
    name: "owned-fixture.zip",
    mimeType: "application/zip",
    buffer: Buffer.from(archive),
  });
  await expect(page.locator("#portal-status")).toContainText(
    "Files staged privately",
  );
  await page
    .getByLabel("Dataset name", { exact: true })
    .fill("<script>inert local label</script>");
  await page
    .getByLabel("I own or have permission to train on every selected source.", {
      exact: true,
    })
    .check();
  await page
    .getByRole("button", { name: "Import selected sources", exact: true })
    .click();
  await expect(page.locator("#datasets")).toContainText("inert local label");
  expect(
    await page.evaluate(
      () => document.querySelectorAll("script:not([src])").length,
    ),
  ).toBe(0);
  const response = await page.request.post("/private/api/datasets", {
    headers: { "X-PIMS-Request": "v1" },
    data: {
      name: "forbidden",
      paths: ["C:/Users/another/private"],
      rights_confirmed: true,
    },
  });
  expect(response.status()).toBe(400);
  await lock(page);
});

test("login recovery, once-only code and explicit password-protected deletion", async ({
  page,
}) => {
  const identity = await register(page);
  await unlock(page);
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await page
    .getByRole("button", { name: "Recover login", exact: true })
    .click();
  await page.getByLabel("Account alias", { exact: true }).fill(identity.alias);
  await page
    .getByLabel("New login password", { exact: true })
    .fill(password + "-new");
  await page
    .getByLabel("Login recovery code", { exact: true })
    .fill(identity.recovery);
  await page.getByRole("button", { name: "Reset login", exact: true }).click();
  await expect(page.locator("#recovery-code")).not.toHaveText(
    identity.recovery,
  );
  await page.getByRole("button", { name: "I saved it privately" }).click();
  await page.getByLabel("Account alias", { exact: true }).fill(identity.alias);
  await page
    .getByLabel("Login password", { exact: true })
    .fill(password + "-new");
  await page.getByRole("button", { name: "Sign in securely" }).click();
  await unlock(page);
  await page.getByText("Delete local account", { exact: true }).click();
  await page
    .getByLabel("Current login password", { exact: true })
    .fill(password + "-new");
  await page
    .getByLabel(
      "I backed up what I need and approve permanent deletion of this local account.",
      { exact: true },
    )
    .check();
  await page
    .getByRole("button", { name: "Delete my local account", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Sign in to your local studio" }),
  ).toBeVisible();
});

test("trainer reviews owned data, exports exact evidence and cannot keep a stale selection", async ({
  page,
}) => {
  /** Real account/upload/review API; owned gradients deliberately span both deterministic splits. */
  const destinations: string[] = [];
  page.on("request", (request) => destinations.push(request.url()));
  await register(page);
  await unlock(page);
  await page
    .getByRole("button", { name: "02 · Datasets & glossary", exact: true })
    .click();
  const fixtures = JSON.parse(
    readFileSync("tests/fixtures/dataset-review.json", "utf8"),
  );
  const archive: Record<string, Uint8Array> = {};
  for (const split of ["train", "validation"]) {
    const fixture = fixtures[split];
    archive[fixture.filename] = Buffer.from(fixture.png_base64, "base64");
    archive[fixture.filename.replace(".png", ".txt")] = strToU8(
      fixture.caption,
    );
    archive[fixture.filename.replace(".png", ".json")] = strToU8(
      JSON.stringify(fixture.metadata),
    );
  }
  await page.getByLabel("Dataset files / ZIP", { exact: true }).setInputFiles({
    name: "owned-gradients.zip",
    mimeType: "application/zip",
    buffer: Buffer.from(zipSync(archive)),
  });
  await expect(page.locator("#portal-status")).toContainText(
    "Files staged privately",
  );
  await page
    .getByLabel("Dataset name", { exact: true })
    .fill("Owned gradients for review");
  await page
    .getByLabel("I own or have permission to train on every selected source.", {
      exact: true,
    })
    .check();
  await page
    .getByRole("button", { name: "Import selected sources", exact: true })
    .click();
  await expect(page.locator("#datasets")).toContainText(
    "Owned gradients for review",
  );
  await page
    .getByRole("button", { name: "Review dataset quality", exact: true })
    .click();
  const report = page.getByRole("region", {
    name: "Dataset quality review",
    exact: true,
  });
  await expect(report).toContainText(fixtures.expected_fingerprint);
  await expect(report).toContainText("Near-duplicate candidates: 1");
  await expect(report).toContainText("<script>inert gradient</script>");
  await expect(report).toContainText("0 sampled file integrity errors");
  await expect(report).toContainText(
    "Verified 2 images; 0 eligible images not verified",
  );
  await expect(report).toContainText("Not enough eligible data");
  expect(await report.locator("script").count()).toBe(0);
  await expect(
    page.getByLabel("Dataset to review", { exact: true }),
  ).toHaveCount(1);
  await report
    .getByRole("button", { name: "Preview candidate pair", exact: true })
    .click();
  await expect(report.locator("img")).toHaveCount(2);
  await expect
    .poll(() =>
      report
        .locator("img")
        .evaluateAll((images) =>
          (images as HTMLImageElement[]).every(
            (image) => image.naturalWidth > 0 && image.naturalWidth <= 192,
          ),
        ),
    )
    .toBe(true);

  await expect(page.locator("input[name=dataset_ids]:checked")).toHaveCount(0);
  const downloading = page.waitForEvent("download");
  await page
    .getByRole("button", {
      name: "Download reviewed dataset report",
      exact: true,
    })
    .click();
  const downloaded = await downloading;
  expect(downloaded.suggestedFilename()).toBe(
    `dataset-review-${fixtures.expected_fingerprint.slice(0, 12)}.json`,
  );
  const exported = JSON.parse(readFileSync((await downloaded.path())!, "utf8"));
  expect(exported.dataset_fingerprint).toBe(fixtures.expected_fingerprint);
  expect(exported.candidate_pairs_total).toBe(1);
  expect(exported.inspection.verified_images).toBe(2);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await report.screenshot({
    path: `artifacts/dataset-review-${test.info().project.name}.png`,
  });
  // Add a second real dataset, then deliberately change selection while a genuine response is held.
  const first = await page
    .getByLabel("Dataset to review", { exact: true })
    .inputValue();
  await page
    .getByRole("button", {
      name: "Create owned synthetic test dataset",
      exact: true,
    })
    .click();
  await expect(page.locator("#review-dataset option")).toHaveCount(2);
  const second = await page
    .locator("#review-dataset option")
    .evaluateAll((options) =>
      (options as HTMLOptionElement[]).map((option) => option.value),
    );
  let release!: () => void;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  let responseReady!: () => void;
  const ready = new Promise<void>((resolve) => {
    responseReady = resolve;
  });
  await page.route(`**/datasets/${first}/review`, async (route) => {
    const response = await route.fetch();
    responseReady();
    await held;
    await route.fulfill({ response });
  });
  await page
    .getByRole("button", { name: "Review dataset quality", exact: true })
    .click();
  await ready;
  await page
    .getByLabel("Dataset to review", { exact: true })
    .selectOption(second.find((identity) => identity !== first)!);
  release();
  await expect(page.locator("#message")).toContainText(
    "Dataset selection changed",
  );
  await expect(report).toContainText("Selection changed");
  await expect(report).not.toContainText(fixtures.expected_fingerprint);
  await expect(
    page.getByRole("button", {
      name: "Download reviewed dataset report",
      exact: true,
    }),
  ).toBeDisabled();
  await lock(page);
  await unlock(page);
  // Locked plaintext DOM is gone. Reopen on Compose, then explicitly navigate to the saved dataset.
  await page
    .getByRole("button", { name: "02 · Datasets & glossary", exact: true })
    .click();
  await page
    .getByLabel("Dataset to review", { exact: true })
    .selectOption(first);
  await expect(
    page.getByRole("button", {
      name: "Download reviewed dataset report",
      exact: true,
    }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Review dataset quality", exact: true })
    .click();
  const reopened = page.getByRole("region", {
    name: "Dataset quality review",
    exact: true,
  });
  await expect(reopened).toContainText(exported.report_sha256);
  await reopened
    .getByRole("button", { name: "Preview candidate pair", exact: true })
    .click();
  await expect(reopened.locator("img")).toHaveCount(2);
  await expect
    .poll(() =>
      reopened
        .locator("img")
        .evaluateAll((images) =>
          (images as HTMLImageElement[]).every(
            (image) => image.naturalWidth > 0 && image.naturalWidth <= 192,
          ),
        ),
    )
    .toBe(true);
  await lock(page);
  expect(
    destinations.every(
      (url) => new URL(url).origin === new URL(page.url()).origin,
    ),
  ).toBe(true);
});
