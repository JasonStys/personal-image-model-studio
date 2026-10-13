/** Jason Stys: browser-to-real-account worker, learned model, generated image and encrypted relaunch. */
// Index: declarations none; variables page@L7, image@L79. Purposes/parameters: docs/code-map.json.
import { test, expect } from "@playwright/test";
import { randomUUID } from "node:crypto";

test("real private custom training and generation through browser controls", async ({
  page,
}) => {
  test.setTimeout(180000);
  await page.goto("/");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await page
    .getByLabel("Account alias", { exact: true })
    .fill("ml_" + randomUUID().replaceAll("-", "").slice(0, 20));
  await page
    .getByLabel("Login password", { exact: true })
    .fill("synthetic-only-ml-login-password");
  await page
    .getByRole("button", { name: "Register account", exact: true })
    .click();
  await page.getByRole("button", { name: "I saved it privately" }).click();
  await page
    .getByLabel("Vault phrase", { exact: true })
    .fill("six synthetic words for real private model testing");
  await page
    .getByRole("button", { name: "Unlock or create workspace" })
    .click();
  await page
    .getByRole("button", { name: "02 · Datasets & glossary", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Create owned synthetic test dataset" })
    .click();
  // Includes real generation/normalization/encryption of 384 owned images;
  // on a busy disk the following metadata read waits for its complete snapshot.
  await expect(page.locator("#datasets")).toContainText('"flagged": 0', {
    timeout: 30000,
  });
  await page
    .getByRole("button", { name: "03 · Train & models", exact: true })
    .click();
  await page.locator("input[name=dataset_ids]").first().check();
  await page
    .getByLabel("Model name", { exact: true })
    .fill("Real private browser model");
  await page.getByLabel("Additional steps", { exact: true }).fill("20");
  await page.getByLabel("Batch size", { exact: true }).fill("4");
  await page.locator("#train select[name=device]").selectOption("cpu");
  await page.getByRole("button", { name: "Start bounded training" }).click();
  await expect(page.locator("#models")).toContainText(
    "Real private browser model",
    { timeout: 100000 },
  );
  await page
    .getByRole("button", { name: "01 · Compose & generate", exact: true })
    .click();
  await page
    .getByLabel("Scene description", { exact: true })
    .fill("red circle on white background");
  await page.getByLabel("Width", { exact: true }).fill("32");
  await page.getByLabel("Height", { exact: true }).fill("32");
  await page.getByLabel("Steps", { exact: true }).fill("4");
  await page
    .getByRole("button", { name: "Generate with learned weights" })
    .click();
  await page
    .getByRole("button", { name: "04 · History & feedback", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Preview image" }).first(),
  ).toBeVisible({ timeout: 100000 });
  await page.getByRole("button", { name: "Preview image" }).first().click();
  await expect(page.locator("#preview")).toBeVisible();
  expect(
    await page
      .locator("#preview")
      .evaluate((image: HTMLImageElement) => image.naturalWidth),
  ).toBe(32);
  await page.screenshot({
    path: "artifacts/private-real-model-ui.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Lock workspace", exact: true })
    .click();
  await expect(page.getByLabel("Vault phrase", { exact: true })).toBeVisible();
  await page
    .getByLabel("Vault phrase", { exact: true })
    .fill("six synthetic words for real private model testing");
  await page
    .getByRole("button", { name: "Unlock or create workspace" })
    .click();
  await page
    .getByRole("button", { name: "03 · Train & models", exact: true })
    .click();
  await expect(page.locator("#models")).toContainText(
    "Real private browser model",
  );
  await page
    .getByRole("button", { name: "Lock workspace", exact: true })
    .click();
});
