import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  fireEvent,
  render,
  screen,
  within,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nProvider, LanguageSelect } from "@/lib/i18n/context";
import { LifeCapture } from "@/components/life/capture";
import { LifeInboxPage } from "@/components/life/inbox";
import { toMinor } from "@/lib/life";
import type { LifeEvent, LifeInbox, LifeProposal } from "@/lib/life";
import { translate } from "@/lib/i18n/core";

const proposal: LifeProposal = {
  event_type: "PURCHASE_INTENT",
  mode: "HYPOTHETICAL",
  title: "Purchase intent",
  amount_minor: 18000,
  amount_min_minor: null,
  amount_max_minor: null,
  currency: "EUR",
  event_date: null,
  expected_date: null,
  date_window_start: null,
  date_window_end: null,
  counterparty: null,
  category: "OTHER",
  essentiality: "DISCRETIONARY",
  priority: "OPTIONAL",
  recurrence_rule: null,
  confidence: 0.65,
  funding_source_id: null,
  obligation_id: null,
  delay_days: null,
  amount_is_delta: false,
  receivable_minor: null,
  repayment_date: null,
  repayment_minor: null,
  envelope: [],
  security_flags: [],
  question: false,
};
const budget = {
  currency: "EUR",
  today: 120,
  this_week: 120,
  this_month: 120,
  dates: ["2026-09-16", "2026-09-20", "2026-09-30"],
  horizon_days: 365,
  plan_state: "SAFE",
  liquid_eur: 1200,
  reserve_eur: 600,
  shortfall_eur: 0,
  committed_eur: 1080,
  verified_coverage: 1,
  coverage: [],
  pending_events: 0,
  explanation:
    "Verified critical and essential commitments are protected for 365 days. Expected income and emergency reserves are excluded. Future budgets assume recorded funds remain available. Demo FX routes and fees apply.",
};
const impact = {
  before: budget,
  after: { ...budget, today: 0, plan_state: "AT_RISK" },
  missing: [],
  affected: [],
  options: [{ type: "LOWER_BUDGET", amount: 120, currency: "EUR" }],
  variants: [],
};
const event: LifeEvent = {
  id: "e1",
  version: 1,
  status: "INTERPRETED",
  raw_input: "I want headphones for EUR 180",
  title: "Purchase intent",
  verification_status: "REVIEW_REQUIRED",
  proposal,
  impact: null,
  missing: [],
  linked_funding_source_id: null,
  linked_obligation_id: null,
  metadata_json: {},
};
const inbox: LifeInbox = {
  events: [],
  budget,
  runway: {
    verified: { days: 30, bounded: false, first_gap: null },
    including_expected: { days: 90, bounded: true, first_gap: null },
    next_critical: null,
    limitation:
      "Runway covers recorded essential commitments only. Unrecorded daily living costs can shorten it. Expected funding is conditional, not guaranteed.",
  },
  notifications: [],
};
let calls: { path: string; method: string; body: Record<string, unknown> }[] =
  [];
let events: LifeEvent[] = [];
let captured: LifeEvent = event;
function wrapper(children: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <I18nProvider>{children}</I18nProvider>
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  calls = [];
  events = [];
  captured = event;
  localStorage.setItem("lattice-locale", "en");
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string, init?: RequestInit) => {
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      calls.push({ path, method: init?.method ?? "GET", body });
      let data: unknown = [];
      if (path.endsWith("/currencies"))
        data = {
          currencies: [
            { code: "EUR", decimals: 2, eur_value: 1 },
            { code: "VND", decimals: 0, eur_value: 0.000036 },
            { code: "CNY", decimals: 2, eur_value: 0.127 },
          ],
        };
      else if (path.endsWith("/health")) data = { as_of: "2026-09-16" };
      else if (path.endsWith("/life-events/interpret")) {
        captured = { ...event, raw_input: String(body.raw_input) };
        data = captured;
      } else if (path.endsWith("/simulate"))
        data = {
          ...captured,
          status: "SIMULATED",
          version: 2,
          proposal: body.proposal,
          impact,
        };
      else if (path.includes("/life-inbox")) data = { ...inbox, events };
      return { ok: true, json: async () => data };
    }),
  );
});
afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.setItem("lattice-locale", "en");
});
const actor = {
  id: "maya",
  role: "STUDENT",
  display_name: "Maya",
  email: "student@lattice.demo",
  student_id: null,
};
describe("private life event interface", () => {
  it.each(["en", "vi", "zh"] as const)(
    "captures, simulates and keeps a purchase without a ledger write in %s",
    async (locale) => {
      localStorage.setItem("lattice-locale", locale);
      const t = (s: string) => translate(locale, s);
      const close = vi.fn();
      wrapper(
        <LifeCapture
          target={{}}
          actor={actor}
          onClose={close}
          notify={vi.fn()}
        />,
      );
      const dialog = screen.getByRole("dialog");
      fireEvent.change(within(dialog).getByLabelText(t("What’s happening?")), {
        target: { value: "I want headphones for EUR 180" },
      });
      fireEvent.click(
        within(dialog).getByRole("button", {
          name: t("Understand and check impact"),
        }),
      );
      expect(await within(dialog).findByTestId("life-impact")).toBeVisible();
      expect(within(dialog).getByText(t("Financial impact"))).toBeVisible();
      fireEvent.click(
        within(dialog).getByRole("button", { name: t("Keep as idea") }),
      );
      await waitFor(() => expect(close).toHaveBeenCalledOnce());
      expect(
        calls.filter((c) => /\/apply|\/confirm|\/received/.test(c.path)),
      ).toHaveLength(0);
      expect(
        calls.find((c) => c.path.endsWith("/interpret"))?.body.locale,
      ).toBe(locale);
    },
  );
  it("preserves the sentence and structured amount when switching languages", async () => {
    wrapper(
      <LifeCapture
        target={{}}
        actor={actor}
        onClose={vi.fn()}
        notify={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByLabelText("What’s happening?"), {
      target: { value: "My private idea" },
    });
    fireEvent.change(screen.getByTestId("language-select"), {
      target: { value: "vi" },
    });
    expect(screen.getByLabelText("Có chuyện gì đang xảy ra?")).toHaveValue(
      "My private idea",
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Diễn giải và kiểm tra tác động" }),
    );
    await screen.findByTestId("life-impact");
    const field = document.querySelector('[name="amount_minor"]');
    expect(field).toHaveValue(180);
    fireEvent.change(screen.getByTestId("language-select"), {
      target: { value: "zh" },
    });
    expect(field).toHaveValue(180);
    expect(screen.getByText("My private idea")).toBeVisible();
  });
  it("keeps real expense confirmation explicit", async () => {
    wrapper(
      <LifeCapture
        target={{}}
        actor={actor}
        onClose={vi.fn()}
        notify={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByLabelText("What’s happening?"), {
      target: { value: "I want headphones" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Understand and check impact" }),
    );
    await screen.findByTestId("life-impact");
    fireEvent.click(screen.getByRole("button", { name: "I bought it" }));
    expect(
      screen.getByRole("button", { name: "Confirm details" }),
    ).toBeDisabled();
    expect(screen.getByLabelText("Funding source")).toHaveValue("");
    expect(document.querySelector('[name="event_date"]')).toHaveValue("");
    expect(calls.some((c) => c.path.endsWith("/apply"))).toBe(false);
  });
  it("shows an empty inbox and lets the user open capture", async () => {
    const open = vi.fn();
    wrapper(<LifeInboxPage open={open} />);
    expect(await screen.findByText("No life events here yet")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Capture an event" }));
    expect(open).toHaveBeenCalled();
  });
  it("filters closed records and renders translated inbox controls", async () => {
    events = [{ ...event, status: "DISMISSED" }];
    localStorage.setItem("lattice-locale", "zh");
    wrapper(
      <>
        <LanguageSelect />
        <LifeInboxPage open={vi.fn()} />
      </>,
    );
    await screen.findByText("暂无生活事项");
    fireEvent.change(screen.getByRole("combobox", { name: "筛选生活事项" }), {
      target: { value: "ALL" },
    });
    expect(
      await screen.findByRole("button", { name: "查看记录" }),
    ).toBeVisible();
    expect(screen.getByText("I want headphones for EUR 180")).toBeVisible();
  });
  it("does not silently round invalid minor units or decimal separators", () => {
    expect(toMinor("1234567", 0)).toBe(1234567);
    expect(toMinor("100.25", 2)).toBe(10025);
    for (const raw of ["10.5", "1,000", "-1", "NaN"])
      expect(() => toMinor(raw, 0)).toThrow();
  });
});
