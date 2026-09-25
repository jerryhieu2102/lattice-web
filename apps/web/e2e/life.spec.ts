import { test, expect } from "@playwright/test";
import vi from "../lib/i18n/vi.json" with { type: "json" };
import zh from "../lib/i18n/zh.json" with { type: "json" };
for (const locale of ["en", "vi", "zh"] as const) {
  const dict: Record<string, string> =
    locale === "vi" ? vi : locale === "zh" ? zh : {};
  const t = (s: string) => dict[s] ?? s;
  test(`${locale}: mobile quick capture, impact and saved idea preserve balances`, async ({
    page,
  }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto("/");
    await page.getByTestId("language-select").selectOption(locale);
    await page
      .getByRole("button", { name: new RegExp(t("Demo administrator")) })
      .click();
    await page
      .getByRole("button", { name: t("Reset Maya"), exact: true })
      .click();
    await expect(page.getByRole("status")).toContainText(
      t("Maya reset and loaded. The evidence-to-action walkthrough is ready."),
    );
    await page.getByLabel(t("Demo actor")).selectOption("student");
    await expect(page.getByLabel(t("Demo actor"))).toHaveValue("student");
    const before = await (
      await page.request.get("/api/v1/funding-sources")
    ).json();
    const plans = await (await page.request.get("/api/v1/plans")).json();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator(".life-floating").click();
    const modal = page.getByRole("dialog");
    const raw =
      locale === "en"
        ? "I want headphones for EUR 180."
        : locale === "vi"
          ? "Mình muốn mua tai nghe giá 180 EUR."
          : "我想买180欧元的耳机。";
    await modal.getByLabel(t("What’s happening?")).fill(raw);
    await modal
      .getByRole("button", { name: t("Understand and check impact") })
      .click();
    await expect(modal.getByTestId("life-impact")).toBeVisible();
    await expect(
      modal.getByText(t("Financial impact"), { exact: true }),
    ).toBeVisible();
    expect(
      await modal.evaluate((e) => e.scrollWidth - e.clientWidth),
    ).toBeLessThanOrEqual(1);
    const amount = modal.locator('[name="amount_minor"]');
    await expect(amount).toHaveValue("180");
    const another = locale === "vi" ? "zh" : "vi";
    await modal.getByTestId("language-select").selectOption(another);
    await expect(amount).toHaveValue("180");
    await expect(modal.locator("blockquote")).toHaveText(raw);
    await modal.getByTestId("language-select").selectOption(locale);
    await modal.getByTestId("life-impact").scrollIntoViewIfNeeded();
    await page.screenshot({
      path: `test-results/life-capture-${locale}.png`,
      fullPage: true,
    });
    await modal.getByRole("button", { name: t("Keep as idea") }).click();
    await expect(modal).not.toBeVisible();
    expect(
      await (await page.request.get("/api/v1/funding-sources")).json(),
    ).toEqual(before);
    expect(await (await page.request.get("/api/v1/plans")).json()).toEqual(
      plans,
    );
    await page.goto("/life");
    await expect(
      page.getByRole("heading", {
        name: t("Your life, in the financial picture."),
      }),
    ).toBeVisible();
    await expect(page.locator(".life-event")).toContainText(raw);
    expect(
      await page.evaluate(
        () =>
          document.documentElement.scrollWidth -
          document.documentElement.clientWidth,
      ),
    ).toBeLessThanOrEqual(1);
    await page.screenshot({
      path: `test-results/life-inbox-${locale}.png`,
      fullPage: true,
    });
    await page.getByLabel(t("Demo actor")).selectOption("parent");
    await expect(page.getByLabel(t("Demo actor"))).toHaveValue("parent");
    await expect(page.locator(".life-floating")).toHaveCount(0);
    for (const path of [
      "life-events",
      "life-inbox",
      "safe-to-spend",
      "runway",
    ]) {
      expect((await page.request.get(`/api/v1/${path}`)).status()).toBe(403);
    }
    expect(errors).toEqual([]);
  });
}

test("real shared expense requires confirmation; reimbursement remains separate until received", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Demo administrator/ }).click();
  await page.getByRole("button", { name: "Reset Maya", exact: true }).click();
  await expect(page.getByRole("status")).toContainText(
    "Maya reset and loaded.",
  );
  await page.getByLabel("Demo actor").selectOption("student");
  await expect(page.getByLabel("Demo actor")).toHaveValue("student");
  await page.locator(".life-floating").click();
  const modal = page.getByRole("dialog");
  await modal
    .getByLabel("What’s happening?")
    .fill("I paid EUR 80 and David owes me EUR 40 today");
  await modal
    .getByRole("button", { name: "Understand and check impact" })
    .click();
  await expect(modal.getByTestId("life-impact")).toBeVisible();
  await modal
    .getByLabel("Funding source", { exact: true })
    .selectOption("student-eur");
  await expect(
    modal.getByRole("button", { name: "Confirm details", exact: true }),
  ).toBeDisabled();
  await modal
    .getByLabel("Confirmation note", { exact: true })
    .fill("I checked the dinner receipt and paid from my EUR account.");
  await modal
    .getByLabel(
      "I checked the amount, currency, date and selected source. This is my explicit confirmation.",
    )
    .check();
  await modal
    .getByRole("button", { name: "Confirm details", exact: true })
    .click();
  await expect(
    modal.getByRole("button", { name: "Apply to sandbox ledger" }),
  ).toBeVisible();
  let funds = await (await page.request.get("/api/v1/funding-sources")).json();
  expect(funds.find((f: { id: string }) => f.id === "student-eur").amount).toBe(
    1700,
  );
  await modal.getByRole("button", { name: "Apply to sandbox ledger" }).click();
  await expect(
    modal.getByText("Recorded in SANDBOX. No real payment was executed."),
  ).toBeVisible();
  funds = await (await page.request.get("/api/v1/funding-sources")).json();
  expect(funds.find((f: { id: string }) => f.id === "student-eur").amount).toBe(
    1620,
  );
  await modal.getByRole("button", { name: "Close capture" }).click();
  await page.goto("/life");
  const child = page.locator(".life-event").filter({
    has: page.getByRole("heading", {
      name: "Expected reimbursement",
      exact: true,
    }),
  });
  await child.getByRole("button", { name: "Review event" }).click();
  await modal.getByText("Mark received", { exact: true }).click();
  await modal.getByLabel("Receipt date", { exact: true }).fill("2026-09-16");
  await modal
    .getByLabel("Receipt evidence or confirmation note")
    .fill("David repaid EUR 40 and I checked the incoming receipt.");
  await modal.getByLabel("I checked that the money arrived.").check();
  await modal
    .getByRole("button", { name: "Confirm receipt", exact: true })
    .click();
  await expect(
    modal.locator(".badge").filter({ hasText: "Resolved" }),
  ).toBeVisible();
  const events = await (await page.request.get("/api/v1/life-events")).json();
  const receipt = events.find(
    (e: { proposal: { event_type: string } }) =>
      e.proposal.event_type === "REIMBURSEMENT_EXPECTED",
  );
  funds = await (await page.request.get("/api/v1/funding-sources")).json();
  expect(
    funds.find((f: { id: string }) => f.id === receipt.linked_funding_source_id)
      .amount,
  ).toBe(40);
});
