import { render, screen, within } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { CoverageTable, Empty, Notice } from "@/components/ui";
import { api } from "@/lib/api";
const c = {
  obligation_id: "tuition",
  label: "Tuition",
  amount: 3200,
  currency: "EUR",
  due_date: "2026-09-30",
  priority: "CRITICAL",
  nominal: 1,
  verified: 0.8,
  on_time_verified: 0.6,
  shortfall: 1280,
  in_horizon: true,
};
afterEach(() => vi.unstubAllGlobals());
describe("honest coverage presentation", () => {
  it("does not call full nominal coverage safe when verified arrival is incomplete", () => {
    render(<CoverageTable coverage={[c]} />);
    const row = screen.getByText("Tuition").closest("tr")!;
    expect(within(row).getByText("100%")).toBeVisible();
    expect(within(row).getByText("60%")).toBeVisible();
    expect(within(row).getByText("At risk")).toBeVisible();
    expect(within(row).queryByText("Safe")).toBeNull();
  });
  it("keeps deferred installment visible outside horizon", () => {
    render(
      <CoverageTable
        coverage={[
          {
            ...c,
            label: "Installment 2",
            due_date: "2026-11-15",
            nominal: 0,
            verified: 0,
            on_time_verified: 0,
            in_horizon: false,
          },
        ]}
      />,
    );
    expect(screen.getByText("Outside horizon")).toBeVisible();
    expect(screen.getByText("Installment 2")).toBeVisible();
  });
  it("renders safe only for full on-time verified coverage", () => {
    render(
      <CoverageTable coverage={[{ ...c, verified: 1, on_time_verified: 1 }]} />,
    );
    expect(screen.getByText("Safe")).toBeVisible();
  });
  it("shows actionable empty state without invented figures", () => {
    render(
      <Empty title="No benchmark computed">Run FAST to compute results.</Empty>,
    );
    expect(screen.getByText("Run FAST to compute results.")).toBeVisible();
    expect(screen.queryByText("100%")).toBeNull();
  });
  it("renders security rejection without HTML interpretation", () => {
    render(<Notice danger>{"<script>steal()</script>"}</Notice>);
    expect(screen.getByText("<script>steal()</script>")).toBeVisible();
    expect(document.querySelector("script")).toBeNull();
  });
  it("propagates server authorization failure instead of reporting success", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue({
          ok: false,
          json: async () => ({
            detail: "All required approvals must be present",
          }),
        }),
    );
    await expect(api("/actions/a/sandbox-execute", "POST")).rejects.toThrow(
      "All required approvals",
    );
  });
});
