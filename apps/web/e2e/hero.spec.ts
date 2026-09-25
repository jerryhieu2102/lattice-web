import { test, expect, Page } from "@playwright/test";
async function setup(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: /Demo administrator/ }).click();
  await page.getByRole("button", { name: "Reset Maya", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Maya reset and loaded");
  await page.getByLabel("Demo actor").selectOption("student");
  await expect(page.getByLabel("Demo actor")).toHaveValue("student");
}
test("complete Maya hero loop, evidence, optimizer, stress, rescue, permission and attack block", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await setup(page);
  await page.getByRole("link", { name: "Documents", exact: true }).click();
  await page.getByRole("button", { name: /tuition-review.txt/ }).click();
  await page
    .getByRole("button", { name: "Extract facts", exact: true })
    .click();
  await expect(page.getByText("Amount: 3200", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Confirm all supported facts" })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "financial state updated",
  );
  await page.getByRole("link", { name: "Plan", exact: true }).click();
  await page
    .getByRole("button", { name: "Generate optimized plan", exact: true })
    .click();
  await expect(page.getByText("Coverage by commitment")).toBeVisible();
  await page.getByRole("button", { name: "Activate plan" }).click();
  await page.getByRole("link", { name: "LATTICE Graph", exact: true }).click();
  await expect(page.locator(".react-flow__edge").first()).toBeVisible();
  await page
    .locator(".react-flow__node")
    .filter({ hasText: "Autumn tuition" })
    .click();
  await expect(page.locator(".inspector")).toContainText("ABC123");
  await page.screenshot({
    path: "test-results/funding-graph.png",
    fullPage: true,
  });
  await page.getByRole("link", { name: "Scenario Lab", exact: true }).click();
  await page.getByLabel("Scholarship delay").fill("14");
  await page.getByRole("button", { name: "Run stress test" }).click();
  await expect(
    page.getByText("Verified scenario failure", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/scenario-lab.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Apply scholarship delay" }).click();
  await expect(page.getByRole("status")).toContainText("Plan invalidated");
  await page.getByRole("link", { name: "Rescue Center", exact: true }).click();
  await page.getByRole("button", { name: "Generate rescue plan" }).click();
  await expect(page.getByText("MINIMUM EVALUATED SCORE")).toBeVisible();
  await page
    .locator(".recommended")
    .getByRole("button", { name: "Prepare intervention" })
    .click();
  await expect(page.getByText("Apply rescue", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Sandbox execute", exact: true })
    .click();
  await expect(page.locator(".toast.error")).toContainText(
    "All required approvals",
  );
  await page.getByRole("link", { name: "Documents", exact: true }).click();
  await page.getByRole("button", { name: "Load malicious update" }).click();
  await expect(page.getByText("Security review required.")).toBeVisible();
  await page.getByRole("link", { name: "Plan", exact: true }).click();
  await page.getByRole("button", { name: "Prepare tuition payment" }).click();
  await expect(page.locator(".toast.error")).toContainText(
    "Beneficiary verification",
  );
  await page.getByRole("link", { name: "Audit", exact: true }).click();
  await page.getByRole("button", { name: "Security", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Security block", exact: true }).first(),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/hero-audit.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});
test("parent privacy is enforced through the actual HTTP API", async ({
  page,
}) => {
  await setup(page);
  await page.getByLabel("Demo actor").selectOption("parent");
  await expect(page.getByLabel("Demo actor")).toHaveValue("parent");
  const r = await page.request.get("/api/v1/funding-sources");
  expect(r.ok()).toBeTruthy();
  expect((await r.json()).map((f: { id: string }) => f.id)).toEqual([
    "parent-vnd",
  ]);
  expect((await page.request.get("/api/v1/obligations/rent")).status()).toBe(
    404,
  );
  expect((await page.request.get("/api/v1/plans")).status()).toBe(403);
  const docs = await (await page.request.get("/api/v1/documents")).json();
  expect(
    docs.every((d: { owner_id: string }) => d.owner_id === "father"),
  ).toBeTruthy();
  await page.getByRole("link", { name: "Commitments", exact: true }).click();
  await expect(page.getByText("Autumn tuition", { exact: true })).toBeVisible();
  await expect(page.getByText("October rent", { exact: true })).toHaveCount(0);
});
test("all routes render and remain inside a mobile viewport", async ({
  page,
}) => {
  await setup(page);
  for (const route of [
    "",
    "commitments",
    "funding",
    "graph",
    "documents",
    "plan",
    "scenarios",
    "rescue",
    "permissions",
    "audit",
    "benchmark",
  ]) {
    await page.goto("/" + route);
    await expect(page.locator("main.content")).toBeVisible();
    await expect(page.locator("main.content h1")).toBeVisible();
    await page.setViewportSize({ width: 390, height: 844 });
    const width = await page.evaluate(() => ({
      scroll: document.documentElement.scrollWidth,
      client: document.documentElement.clientWidth,
    }));
    expect(width.scroll, route).toBeLessThanOrEqual(width.client + 1);
    await page.setViewportSize({ width: 1440, height: 1000 });
  }
  await page.goto("/");
  await page.screenshot({ path: "test-results/overview.png", fullPage: true });
});

test("approved rescue executes in the sandbox and retains the deferred tuition debt", async ({
  page,
}) => {
  await setup(page);
  await page.getByRole("link", { name: "Rescue Center", exact: true }).click();
  await page.getByRole("button", { name: "Generate rescue plan" }).click();
  await page
    .locator(".recommended")
    .getByRole("button", { name: "Prepare intervention" })
    .click();
  await page.getByRole("link", { name: "Permissions", exact: true }).click();
  for (const role of ["student", "parent", "admin"]) {
    if (role !== "student")
      await page.getByLabel("Demo actor").selectOption(role);
    await page
      .getByRole("button", { name: "Approve my part", exact: true })
      .click();
    await expect(page.getByRole("status")).toContainText(
      "Your approval was recorded",
    );
  }
  await page.getByLabel("Demo actor").selectOption("student");
  await page
    .getByRole("button", { name: "Sandbox execute", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Sandbox execution completed",
  );
  const plans = await (await page.request.get("/api/v1/plans")).json();
  expect(plans[0].summary.verified_feasible).toBe(true);
  const obligations = await (
    await page.request.get("/api/v1/obligations")
  ).json();
  expect(
    obligations.filter((o: { label: string }) =>
      o.label.includes("installment 2"),
    ),
  ).toHaveLength(1);
  expect(
    obligations
      .filter((o: { label: string }) => o.label.includes("installment"))
      .reduce((s: number, o: { amount: number }) => s + o.amount, 0),
  ).toBe(3220);
  const actions = await (await page.request.get("/api/v1/actions")).json();
  expect(
    (
      await page.request.post(
        "/api/v1/actions/" + actions[0].id + "/sandbox-execute",
        { headers: { "x-lattice-request": "1" } },
      )
    ).status(),
  ).toBe(409);
  await page.getByRole("link", { name: "Plan", exact: true }).click();
  await expect(
    page.getByText("Autumn tuition · installment 2", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/repaired-plan.png",
    fullPage: true,
  });
});

test("Benchmark UI runs 48 computed cases and exports the same results", async ({
  page,
}) => {
  await setup(page);
  await page.getByRole("link", { name: "Benchmark", exact: true }).click();
  await page
    .getByRole("button", { name: "Run FAST · 48", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "FAST benchmark computed and saved",
  );
  await expect(
    page.locator(".metric").filter({ hasText: "Cases computed" }),
  ).toContainText("48");
  await expect(
    page.locator(".metric").filter({ hasText: "Failed" }),
  ).toContainText("0");
  const json = await (
    await page.request.get("/api/v1/benchmark/export?format=json")
  ).json();
  expect(json.case_count).toBe(48);
  expect(json.passed).toBe(48);
  const csv = await (
    await page.request.get("/api/v1/benchmark/export?format=csv")
  ).text();
  expect(csv.trim().split("\n")).toHaveLength(49);
  await page.screenshot({ path: "test-results/benchmark.png", fullPage: true });
});
