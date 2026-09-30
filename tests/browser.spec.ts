/** Real navigation, authentication, data persistence, inert user text and accessible responsive UI. */
// Index: declarations none; variables token@L5, page@L8, name@L19, result@L27, page@L41, response@L62. Purposes/parameters: docs/code-map.json.
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
const token = "test-session-" + "x".repeat(40);

test("private session and accessible responsive workspace", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Connect to your local session" }),
  ).toBeVisible();
  await page.getByLabel("Session token").fill(token);
  await page.getByRole("button", { name: "Connect", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Give every idea its own field" }),
  ).toBeVisible();
  for (const name of [
    "02 · Datasets & glossary",
    "03 · Train & models",
    "04 · History & feedback",
    "05 · Method & limits",
    "01 · Compose & generate",
  ]) {
    await page.getByRole("button", { name, exact: true }).click();
    const result = await new AxeBuilder({ page }).analyze();
    expect(result.violations).toEqual([]);
  }
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: `artifacts/ui-${test.info().project.name}.png`,
    fullPage: true,
  });
});

test("owned dataset, glossary and guarded connector", async ({ page }) => {
  await page.goto(`/#token=${token}`);
  await page.getByRole("button", { name: "02 · Datasets & glossary" }).click();
  await page
    .getByRole("button", { name: "Create owned synthetic test dataset" })
    .click();
  await expect(page.locator("#datasets")).toContainText('"flagged": 0');
  await page.locator("textarea[name=entries]").fill(
    JSON.stringify({
      light: {
        definition: "<script>not HTML</script>",
        source: "Synthetic reviewed reference",
        reviewed: true,
      },
    }),
  );
  await page.getByRole("button", { name: "Save reviewed definitions" }).click();
  await expect(page.locator("#message")).toContainText("Saved");
  await page.getByRole("button", { name: "Load definitions" }).click();
  await expect(page.locator("textarea[name=entries]")).toHaveValue(/not HTML/);
  await expect(page.locator("#da-status")).toContainText("Not connected");
  const response = await page.request.post(
    "/api/connectors/deviantart/import",
    {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        name: "Unauthorized",
        rights_confirmed: true,
        provider_terms_reviewed: true,
      },
    },
  );
  expect(response.status()).toBe(400);
  expect(
    await page.evaluate(
      () => document.querySelectorAll("script:not([src])").length,
    ),
  ).toBe(0);
});
