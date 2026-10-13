/** Jason Stys: real private login, account isolation, encrypted export, file pickers, recovery and accessible help. */
// Index: declarations register@L12, unlock@L33, lock@L44; variables password@L8, phrase@L9, page@L12, alias@L17, recovery@L26, page@L33, page@L44, page@L54, destinations@L56, unlockBodies@L57, request@L58, identity@L66, event@L92, bytes@L96, url@L114, page@L133, browser@L134, context@L145, other@L146, page@L169, png@L176, archive@L180, response@L215, page@L228, identity@L230. Purposes/parameters: docs/code-map.json.
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
