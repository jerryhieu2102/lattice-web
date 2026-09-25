"use client";
import { useI18n } from "@/lib/i18n/context";
import Link from "next/link";
import { LanguageSelect } from "@/lib/i18n/context";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  LayoutDashboard,
  Inbox,
  Plus,
  ListChecks,
  Wallet,
  Network,
  FileText,
  Route,
  FlaskConical,
  LifeBuoy,
  ShieldCheck,
  History,
  BarChart3,
  ArrowRight,
  RefreshCw,
  Layers3,
  LogOut,
  CheckCircle2,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Actor } from "@/lib/types";
import { Overview, FundingPage, CommitmentsPage } from "./finance";
import { DocumentsPage } from "./documents";
import { GraphPage } from "./graph";
import { PlanPage, ScenarioPage, RescuePage } from "./planning";
import { PermissionsPage, AuditPage, BenchmarkPage } from "./governance";
import { Loading, Notice } from "./ui";
import { LifeCapture } from "./life/capture";
import { LifeInboxPage, LifeSummary, LifeNotifications } from "./life/inbox";
const pages = [
  ["", "Overview", LayoutDashboard],
  ["life", "Life Inbox", Inbox],
  ["commitments", "Commitments", ListChecks],
  ["funding", "Funding", Wallet],
  ["graph", "LATTICE Graph", Network],
  ["documents", "Documents", FileText],
  ["plan", "Plan", Route],
  ["scenarios", "Scenario Lab", FlaskConical],
  ["rescue", "Rescue Center", LifeBuoy],
  ["permissions", "Permissions", ShieldCheck],
  ["audit", "Audit", History],
  ["benchmark", "Benchmark", BarChart3],
] as const;
export function Workspace() {
  const { t, date } = useI18n();

  const path = usePathname().split("/")[1] || "";
  const client = useQueryClient();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<{ as_of: string }>("/health"),
  });
  const auth = useQuery({
    queryKey: ["me"],
    queryFn: () => api<Actor>("/auth/me"),
  });
  const [toast, setToast] = useState<{ text: string; error: boolean } | null>(
    null,
  );
  const [busy, setBusy] = useState(false);
  const [lifeTarget, setLifeTarget] = useState<{
    id?: string;
    emergency?: boolean;
  } | null>(null);
  const openLife = (target?: { id?: string; emergency?: boolean }) =>
    setLifeTarget(target ?? {});
  const notify = (text: string, error = false) => setToast({ text, error });
  async function signIn(role: string) {
    setBusy(true);
    try {
      const actor = await api<Actor>("/auth/login", "POST", {
        email: `${role}@lattice.demo`,
        password: "LatticeDemo2026!",
      });
      client.clear();
      client.setQueryData(["me"], actor);
      notify(`Signed in as ${actor.display_name}`);
    } catch (e) {
      notify((e as Error).message, true);
    } finally {
      setBusy(false);
    }
  }
  async function reset() {
    setBusy(true);
    try {
      await api("/demo/reset", "POST");
      await api("/demo/load-maya", "POST");
      await client.invalidateQueries();
      notify(
        "Maya reset and loaded. The evidence-to-action walkthrough is ready.",
      );
    } catch (e) {
      notify((e as Error).message, true);
    } finally {
      setBusy(false);
    }
  }
  if (auth.isPending) return <Loading />;
  if (!auth.data)
    return (
      <main className="login">
        <div className="login-story">
          <div className="brand">
            <Layers3 /> LATTICE
          </div>
          <span className="eyebrow">
            {t("VERIFY · ORCHESTRATE · STRESS · REPAIR")}
          </span>
          <h1>
            {t("Every commitment.")}
            <br />
            {t("A plan you can")}
            <br />
            <em>{t("verify.")}</em>
          </h1>
          <p>
            {t("Cross-border finances are more than a balance.")}
            <br />
            {t(
              "Connect evidence, funding, deadlines, and the people who make it possible.",
            )}
          </p>
          <div className="login-line">
            <span>VND</span>
            <i />
            <ShieldCheck />
            <i />
            <span>{t("USD · CNY · EUR")}</span>
          </div>
          <small>
            {t("FICTIONAL MAYA DATA · DETERMINISTIC RATES · SANDBOX ONLY")}
          </small>
        </div>
        <div className="login-card">
          <LanguageSelect />
          <span className="eyebrow">LATTICE v1.0</span>
          <h2>{t("Open the demo workspace")}</h2>
          <p>
            {t(
              "Choose an actor to explore the same financial plan through different permissions.",
            )}
          </p>
          {[
            ["student", "Maya Nguyen", "Student workspace"],
            ["parent", "Minh Nguyen", "Parent · own contribution only"],
            [
              "admin",
              "Demo administrator",
              "Reset Maya · simulate institution approval",
            ],
          ].map(([role, name, description]) => (
            <button
              className="account"
              key={role}
              onClick={() => signIn(role)}
              disabled={busy}
            >
              <div>
                <strong>{t(name)}</strong>
                <small>{t(description)}</small>
              </div>
              <ArrowRight size={18} />
            </button>
          ))}
          <Notice>
            {t(
              "New database? Sign in as Demo administrator, then select Reset Maya.",
            )}
          </Notice>
          <small className="muted">
            {t("Demo password: LatticeDemo2026!")}
          </small>
          {toast && (
            <p role="alert" className="error-text">
              {t(toast.text)}
            </p>
          )}
        </div>
      </main>
    );
  const actor = auth.data;
  const privateAllowed = ["STUDENT", "ADMIN_DEMO"].includes(actor.role);
  const privatePage = [
    "",
    "life",
    "plan",
    "scenarios",
    "rescue",
    "benchmark",
  ].includes(path);
  const props = { actor, notify };
  const content =
    privatePage && !privateAllowed ? (
      <Notice danger>
        {t(
          "This is a student-only financial workspace. Your shared commitments and own contributions are available from the sidebar.",
        )}
      </Notice>
    ) : path === "" ? (
      <>
        <Overview {...props} />
        <LifeSummary open={openLife} />
      </>
    ) : path === "life" ? (
      <LifeInboxPage open={openLife} />
    ) : path === "funding" ? (
      <FundingPage {...props} />
    ) : path === "commitments" ? (
      <CommitmentsPage {...props} />
    ) : path === "documents" ? (
      <DocumentsPage {...props} />
    ) : path === "graph" ? (
      <GraphPage />
    ) : path === "plan" ? (
      <PlanPage {...props} />
    ) : path === "scenarios" ? (
      <ScenarioPage {...props} />
    ) : path === "rescue" ? (
      <RescuePage {...props} />
    ) : path === "permissions" ? (
      <PermissionsPage {...props} />
    ) : path === "audit" ? (
      <AuditPage />
    ) : path === "benchmark" ? (
      <BenchmarkPage {...props} />
    ) : (
      <Notice>
        {t("Page not found.")}
        <Link href="/">{t("Return to overview")}</Link>.
      </Notice>
    );
  return (
    <div className="app">
      <aside className="sidebar">
        <Link href="/" className="brand">
          <Layers3 size={25} />
          LATTICE<span>v1.0</span>
        </Link>
        <div className="workspace-label">
          <span className="avatar">M</span>
          <div>
            <strong>{t("Maya’s workspace")}</strong>
            <small>{t("Vietnam → Europe")}</small>
          </div>
        </div>
        <nav aria-label={t("Main navigation")}>
          {pages.map(([href, title, Icon], i) => (
            <Link
              key={href}
              className={`${path === href ? "active" : ""} ${i === 8 ? "nav-separator" : ""}`}
              href={"/" + href}
            >
              <Icon size={18} />
              {t(title)}
              {href === "scenarios" && <span className="dot" />}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <ShieldCheck size={19} />
          <strong>{t("Evidence before action")}</strong>
          <p>{t("Money moves only in the sandbox.")}</p>
          <small>{t("DEMO DATA · NOT LIVE RATES")}</small>
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <div>
            <span className="status-dot" />
            {t("DEMO WORKSPACE")}
            <span className="top-divider">/</span>
            <span>
              {t(pages.find((p) => p[0] === path)?.[1] || "Workspace")}
            </span>
          </div>
          <div className="top-actions">
            <LanguageSelect />
            {privateAllowed && <LifeNotifications />}
            <span className="sandbox">{t("SANDBOX")}</span>
            <label className="sr-only" htmlFor="actor">
              {t("Demo actor")}
            </label>
            <select
              id="actor"
              aria-label={t("Demo actor")}
              value={
                actor.role === "ADMIN_DEMO" ? "admin" : actor.role.toLowerCase()
              }
              onChange={(e) => signIn(e.target.value)}
              disabled={busy}
            >
              <option value="student">{t("Maya · Student")}</option>
              <option value="parent">{t("Minh · Parent")}</option>
              <option value="sponsor">{t("Sponsor")}</option>
              <option value="admin">{t("Demo administrator")}</option>
            </select>
            {actor.role === "ADMIN_DEMO" && (
              <button className="button small" onClick={reset} disabled={busy}>
                <RefreshCw size={14} />
                {t("Reset Maya")}
              </button>
            )}
            <button
              className="icon-button"
              aria-label={t("Sign out")}
              onClick={async () => {
                await api("/auth/logout", "POST");
                client.clear();
                await client.invalidateQueries();
              }}
            >
              <LogOut size={17} />
            </button>
          </div>
        </header>
        <main className="content">{content}</main>
        <footer>
          {t("Verified cross-border financial orchestration")}
          <span>
            {t("Planning clock:")}{" "}
            {health.data?.as_of ? date(health.data.as_of) : t("Loading…")}{" "}
            {t("· 45-day horizon · No real payments")}
          </span>
        </footer>
      </div>
      {privateAllowed && (
        <button className="life-floating" onClick={() => openLife()}>
          <Plus size={19} />
          {t("Tell LATTICE")}
        </button>
      )}
      {privateAllowed && lifeTarget && (
        <LifeCapture
          target={lifeTarget}
          actor={actor}
          onClose={() => setLifeTarget(null)}
          notify={notify}
        />
      )}
      {toast && (
        <div
          role={toast.error ? "alert" : "status"}
          className={`toast ${toast.error ? "error" : ""}`}
        >
          <CheckCircle2 size={18} />
          {t(toast.text)}
          <button
            aria-label={t("Dismiss notification")}
            onClick={() => setToast(null)}
          >
            <X size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
