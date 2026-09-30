/** End-to-end real UI → API → ML worker → trained model → generated preview. */
// Index: declarations none; variables page@L6, element@L46. Purposes/parameters: docs/code-map.json.
import { test, expect } from "@playwright/test";

test("train a genuine custom model and generate through the UI", async ({
  page,
}) => {
  await page.goto(`/#token=${"test-session-" + "x".repeat(40)}`);
  await page.getByRole("button", { name: "02 · Datasets & glossary" }).click();
  await page
    .getByRole("button", { name: "Create owned synthetic test dataset" })
    .click();
  await expect(page.locator("#datasets")).toContainText('"flagged": 0');
  await page.getByRole("button", { name: "03 · Train & models" }).click();
  await page.locator("input[name=dataset_ids]").first().check();
  await page
    .getByLabel("Model name", { exact: true })
    .fill("Browser tested real native model");
  await page.getByLabel("Additional steps").fill("20");
  await page.getByLabel("Batch size").fill("4");
  await page.locator("#train select[name=device]").selectOption("cpu");
  await page.getByRole("button", { name: "Start bounded training" }).click();
  await expect(page.locator("#models")).toContainText(
    "Browser tested real native model",
    { timeout: 100000 },
  );
  await page.getByRole("button", { name: "01 · Compose & generate" }).click();
  await page
    .getByLabel("Scene description", { exact: true })
    .fill("red circle on white background");
  await page.getByLabel("Width", { exact: true }).fill("32");
  await page.getByLabel("Height", { exact: true }).fill("32");
  await page.getByLabel("Steps", { exact: true }).fill("4");
  await page
    .getByRole("button", { name: "Generate with learned weights" })
    .click();
  await page.getByRole("button", { name: "04 · History & feedback" }).click();
  await expect(
    page.getByRole("button", { name: "Preview image" }).first(),
  ).toBeVisible({ timeout: 100000 });
  await page.getByRole("button", { name: "Preview image" }).first().click();
  await expect(page.locator("#preview")).toBeVisible();
  expect(
    await page
      .locator("#preview")
      .evaluate((element: HTMLImageElement) => element.naturalWidth),
  ).toBe(32);
  await page.screenshot({
    path: "artifacts/ui-real-model.png",
    fullPage: true,
  });
});
