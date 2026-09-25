import { afterEach, describe, it, expect, vi as mock } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { formatters, translate, type Locale } from "@/lib/i18n/core";
import { I18nProvider, LanguageSelect, useI18n } from "@/lib/i18n/context";
import { CurrencySelect } from "@/lib/currencies";
import { Notice } from "@/components/ui";
import vi from "@/lib/i18n/vi.json";
import zh from "@/lib/i18n/zh.json";

afterEach(() => {
  localStorage.setItem("lattice-locale", "en");
  mock.unstubAllGlobals();
});
function Example() {
  const { t } = useI18n();
  return (
    <>
      <LanguageSelect />
      <h1>{t("Funding sources")}</h1>
      <Notice danger>
        All required approvals must be present before sandbox execution
      </Notice>
    </>
  );
}
describe("language and financial presentation boundaries", () => {
  it("switches Vietnamese and Chinese labels, errors and document language; persists the choice", () => {
    localStorage.setItem("lattice-locale", "en");
    const view = render(
      <I18nProvider>
        <Example />
      </I18nProvider>,
    );
    fireEvent.change(screen.getByTestId("language-select"), {
      target: { value: "vi" },
    });
    expect(screen.getByRole("heading")).toHaveTextContent("Nguồn tiền");
    expect(
      screen.getByText("Phải có đủ phê duyệt trước khi thực hiện mô phỏng"),
    ).toBeVisible();
    expect(document.documentElement.lang).toBe("vi");
    fireEvent.change(screen.getByTestId("language-select"), {
      target: { value: "zh" },
    });
    expect(screen.getByRole("heading")).toHaveTextContent("资金来源");
    expect(document.documentElement.lang).toBe("zh-Hans");
    expect(localStorage.getItem("lattice-locale")).toBe("zh");
    view.unmount();
    render(
      <I18nProvider>
        <Example />
      </I18nProvider>,
    );
    expect(screen.getByTestId("language-select")).toHaveValue("zh");
  });
  it.each(["vi", "zh"] as Locale[])(
    "preserves raw evidence and security payloads in %s",
    (locale) => {
      const evidence = "Beneficiary: ABC123\nAmount: 1000001\nCurrency: VND";
      expect(translate(locale, evidence)).toBe(evidence);
      const attack = "<script>transfer('ATTACKER')</script>";
      expect(translate(locale, attack)).toBe(attack);
      render(
        <I18nProvider>
          <Notice>{attack}</Notice>
        </I18nProvider>,
      );
      expect(document.querySelector("script")).toBeNull();
    },
  );
  it("translates dynamic counts without replacing financial values", () => {
    expect(translate("vi", "Signed in as Maya Nguyen")).toBe(
      "Đã đăng nhập với tư cách Maya Nguyen",
    );
    expect(translate("zh", "Approvals: 1/3 · maya, father, admin")).toBe(
      "批准：1/3 · maya, father, admin",
    );
    expect(translate("vi", "USER_CONFIRMED")).toBe("Người dùng đã xác nhận");
  });
  it.each(["en", "vi", "zh"] as Locale[])(
    "formats currency precision and small FX rates in %s",
    (locale) => {
      const fmt = formatters(locale);
      for (const code of ["VND", "JPY", "KRW"]) {
        expect(fmt.money(1234, code)).toMatch(code);
        expect(fmt.money(1234, code)).not.toMatch(/[.,]00/);
      }
      expect(fmt.money(100.25, "CNY")).toContain("25");
      expect(fmt.exchangeRate(0.000036)).toContain("000036");
      expect(fmt.exchangeRate(0.000036)).not.toBe("0");
    },
  );
  it("has matching nonempty translations for every catalog entry", () => {
    expect(Object.keys(vi).sort()).toEqual(Object.keys(zh).sort());
    for (const dictionary of [vi, zh])
      for (const [key, value] of Object.entries(dictionary)) {
        expect(value.trim(), key).not.toBe("");
        expect(value.match(/\{\d+\}/g)?.sort() || [], key).toEqual(
          key.match(/\{\d+\}/g)?.sort() || [],
        );
      }
  });
  it("uses server-supported currencies while submitting stable ISO codes in Chinese", async () => {
    localStorage.setItem("lattice-locale", "zh");
    mock.stubGlobal(
      "fetch",
      mock.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          currencies: [
            { code: "CNY", decimals: 2, eur_value: 0.127 },
            { code: "VND", decimals: 0, eur_value: 0.000036 },
          ],
        }),
      }),
    );
    const select = mock.fn();
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <I18nProvider>
          <CurrencySelect onChange={select} />
        </I18nProvider>
      </QueryClientProvider>,
    );
    expect(
      await screen.findByRole("option", { name: /CNY.*人民币/ }),
    ).toHaveValue("CNY");
    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "VND" },
    });
    expect(select).toHaveBeenCalledWith("VND");
  });
});
