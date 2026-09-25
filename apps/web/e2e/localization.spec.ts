import { test, expect } from "@playwright/test";
import vi from "../lib/i18n/vi.json" with { type: "json" };
import zh from "../lib/i18n/zh.json" with { type: "json" };

for (const locale of ["vi", "zh"] as const) {
  const dictionary: Record<string, string> = locale === "vi" ? vi : zh;
  const t = (key: string) => dictionary[key] || key;
  test(`${locale}: language persists, every route fits mobile, currency forms and policy gates work`, async ({
    page,
  }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto("/");
    await page.getByTestId("language-select").selectOption(locale);
    await expect(
      page.getByRole("heading", { name: t("Open the demo workspace") }),
    ).toBeVisible();
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
    await page.reload();
    await expect(page.getByTestId("language-select")).toHaveValue(locale);
    await expect(page.locator("html")).toHaveAttribute(
      "lang",
      locale === "zh" ? "zh-Hans" : "vi",
    );
    const pages = [
      ["", "Your next commitments, accounted for."],
      ["commitments", "Financial commitments"],
      ["funding", "Funding sources"],
      ["graph", "Follow the funding."],
      ["documents", "Evidence, before decisions."],
      ["plan", "A plan you can trace."],
      ["scenarios", "What if the timing changes?"],
      ["rescue", "The smallest change that helps."],
      ["permissions", "Permissions & people"],
      ["audit", "Audit history"],
      ["benchmark", "Evaluation workbench"],
    ];
    for (const [route, title] of pages) {
      await page.goto("/" + route);
      await expect(page.locator("main.content h1")).toHaveText(t(title));
      await page.setViewportSize({ width: 390, height: 844 });
      expect(
        await page.evaluate(
          () =>
            document.documentElement.scrollWidth -
            document.documentElement.clientWidth,
        ),
        `${locale}/${route}`,
      ).toBeLessThanOrEqual(1);
      await page.setViewportSize({ width: 1440, height: 1000 });
    }
    await page.goto("/funding");
    const panel = page.locator(".transfer-routes");
    await expect(panel.locator('[name="from_currency"] option')).toHaveCount(
      13,
    );
    for (const [from, to] of [
      ["USD", "VND"],
      ["CNY", "VND"],
      ["JPY", "USD"],
      ["SGD", "CNY"],
      ["VND", "CNY"],
    ]) {
      await panel.locator('[name="from_currency"]').selectOption(from);
      await panel.locator('[name="to_currency"]').selectOption(to);
      await expect(panel.locator("tbody")).toContainText(`${from} → ${to}`);
      await expect(panel.locator("tbody tr")).toHaveCount(1);
    }
    await page.screenshot({
      path: `test-results/funding-${locale}.png`,
      fullPage: true,
    });
    await page
      .getByRole("button", { name: t("Add funding"), exact: true })
      .click();
    const form = page.locator("form");
    await form
      .locator('[name="label"]')
      .fill(locale === "vi" ? "Tiết kiệm nhân dân tệ" : "人民币储蓄");
    await form.locator('[name="currency"]').selectOption("CNY");
    await form.locator('[name="amount"]').fill("5000.25");
    await form.locator('[name="available_from"]').fill("2026-09-16");
    await form
      .locator('[name="confirmation_note"]')
      .fill("Explicit sandbox balance confirmation");
    await form.getByRole("button", { name: t("Confirm funding") }).click();
    await expect(page.getByRole("status")).toContainText(
      t("Funding added with explicit confirmation."),
    );
    const sources = await (
      await page.request.get("/api/v1/funding-sources")
    ).json();
    expect(
      sources.some(
        (f: { currency: string; amount: number; source_type: string }) =>
          f.currency === "CNY" &&
          f.amount === 5000.25 &&
          f.source_type === "STUDENT_BALANCE",
      ),
    ).toBe(true);
    await page.goto("/commitments");
    await page
      .getByRole("button", { name: t("Add commitment"), exact: true })
      .click();
    await form
      .locator('[name="label"]')
      .fill(locale === "vi" ? "Học phí bằng yên" : "日元学费");
    await form.locator('[name="currency"]').selectOption("JPY");
    await expect(form.locator('[name="amount"]')).toHaveAttribute("step", "1");
    await form.locator('[name="amount"]').fill("10001");
    await form.locator('[name="due_date"]').fill("2026-09-30");
    await form.locator('[name="beneficiary"]').fill("JPN123");
    await form
      .locator('[name="confirmation_note"]')
      .fill("Explicit sandbox invoice confirmation");
    await form.getByRole("button", { name: t("Confirm commitment") }).click();
    await expect(page.getByRole("status")).toContainText(
      t("Commitment confirmed and financial state updated."),
    );
    const obligations = await (
      await page.request.get("/api/v1/obligations")
    ).json();
    expect(
      obligations.some(
        (o: { currency: string; amount: number; type: string }) =>
          o.currency === "JPY" && o.amount === 10001 && o.type === "TUITION",
      ),
    ).toBe(true);
    await page.goto("/plan");
    await page
      .getByRole("button", { name: t("Generate optimized plan"), exact: true })
      .click();
    await expect(page.getByRole("status")).toContainText(
      t("A new optimized plan is ready."),
    );
    const plans = await (await page.request.get("/api/v1/plans")).json();
    expect(plans[0].summary.constraint_violations).toBe(0);
    expect(
      plans[0].summary.allocations.some(
        (a: { source_currency: string }) => a.source_currency === "CNY",
      ),
    ).toBe(true);
    expect(
      plans[0].summary.coverage.some(
        (c: { currency: string; on_time_verified: number }) =>
          c.currency === "JPY" && c.on_time_verified === 1,
      ),
    ).toBe(true);
    await page.goto("/rescue");
    await page.getByRole("button", { name: t("Generate rescue plan") }).click();
    await page
      .locator(".recommended")
      .getByRole("button", { name: t("Prepare intervention") })
      .click();
    await page
      .getByRole("button", { name: t("Sandbox execute"), exact: true })
      .click();
    await expect(page.locator(".toast.error")).toContainText(
      t("All required approvals must be present before sandbox execution"),
    );
    await page.goto("/documents");
    await page
      .getByRole("button", { name: t("Load malicious update") })
      .click();
    await expect(page.getByText(t("Security review required."))).toBeVisible();
    await page.goto("/plan");
    await page
      .locator(".allocation-grid .panel")
      .filter({ hasText: t("Autumn tuition") })
      .getByRole("button", { name: t("Prepare tuition payment") })
      .click();
    await expect(page.locator(".toast.error")).toContainText(
      t("Beneficiary verification is required; payment blocked"),
    );
    await page.goto("/");
    await expect(page.locator("main.content h1")).toHaveText(
      t("Your next commitments, accounted for."),
    );
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({
      path: `test-results/overview-${locale}.png`,
      fullPage: true,
    });
    expect(errors).toEqual([]);
  });
}
