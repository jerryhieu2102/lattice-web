"use client";
import { useI18n } from "@/lib/i18n/context";
import { useState } from "react";
import {
  Play,
  Download,
  ShieldCheck,
  LockKeyhole,
  CheckCircle2,
} from "lucide-react";
import { api } from "@/lib/api";
import { useData, useTask } from "@/lib/hooks";
import type {
  Actor,
  Notify,
  Permission,
  Audit,
  Funding,
  Obligation,
} from "@/lib/types";
import { Badge, Empty, Loading, PageHeader, Metric, Notice } from "./ui";
import { ActionsPanel } from "./actions";
type Props = { actor: Actor; notify: Notify };
export function PermissionsPage({ actor, notify }: Props) {
  const { t, label } = useI18n();

  const query = useData<Permission[]>("permissions", "/permissions");
  const funds = useData<Funding[]>("funding", "/funding-sources");
  const obligations = useData<Obligation[]>("obligations", "/obligations");
  const { busy, run } = useTask(notify);
  const [type, setType] = useState("FUNDING");
  const ownFunds =
    funds.data?.filter((f) => f.owner_actor_id === actor.id) || [];
  return (
    <>
      <PageHeader
        eyebrow={t("AUTHORITY IS EXPLICIT")}
        title={t("Permissions & people")}
        description={t(
          "Seeing an obligation does not grant access to balances or permission to spend.",
        )}
      />
      <div className="privacy-grid">
        <section className="panel">
          <div className="card-top">
            <ShieldCheck className="accent" />
            <span className="eyebrow">{t("PARENT VIEW")}</span>
          </div>
          <h2>{t("Only what is shared.")}</h2>
          <ul className="check-list">
            <li>
              <CheckCircle2 />
              {t("Shared tuition obligation")}
            </li>
            <li>
              <CheckCircle2 />
              {t("Own funding contribution")}
            </li>
            <li>
              <LockKeyhole />
              {t("No private student balances")}
            </li>
            <li>
              <LockKeyhole />
              {t("No unshared rent or spending")}
            </li>
            <li>
              <LockKeyhole />
              {t("No student-only documents")}
            </li>
          </ul>
          <p className="caption">
            {t(
              "The same access rules protect direct API requests, graph responses, and action details.",
            )}
          </p>
        </section>
        <section className="panel">
          <span className="eyebrow">{t("GRANT A SPECIFIC CAPABILITY")}</span>
          <h2>{t("Share with a purpose.")}</h2>
          <form
            className="form-grid compact"
            onSubmit={(e) => {
              e.preventDefault();
              const values = Object.fromEntries(new FormData(e.currentTarget));
              run(
                () => api("/permissions", "POST", values),
                "Permission granted for this resource only.",
              );
            }}
          >
            <label>
              {t("Resource type")}
              <select
                name="resource_type"
                value={type}
                onChange={(e) => setType(e.target.value)}
              >
                <option value="FUNDING">{t("FUNDING")}</option>
                <option value="OBLIGATION">{t("OBLIGATION")}</option>
              </select>
            </label>
            <label>
              {t("Resource")}
              <select name="resource_id" required>
                {type === "FUNDING"
                  ? ownFunds.map((f) => (
                      <option key={f.id} value={f.id}>
                        {t(f.label)}
                      </option>
                    ))
                  : actor.role === "STUDENT"
                    ? obligations.data?.map((o) => (
                        <option key={o.id} value={o.id}>
                          {t(o.label)}
                        </option>
                      ))
                    : null}
              </select>
            </label>
            <label>
              {t("Recipient")}
              <select name="target_actor_id">
                <option value={actor.role === "PARENT" ? "maya" : "father"}>
                  {actor.role === "PARENT" ? t("Maya") : t("Father")}
                </option>
              </select>
            </label>
            <label>
              {t("Permission")}
              <select name="permission_type">
                {(type === "OBLIGATION"
                  ? ["VIEW_SHARED_OBLIGATION"]
                  : [
                      "VIEW_OWN_CONTRIBUTION",
                      "APPROVE_OWN_FUNDS",
                      "VIEW_PRIVATE_FINANCES",
                    ]
                ).map((p) => (
                  <option key={p} value={p}>
                    {label(p)}
                  </option>
                ))}
              </select>
            </label>
            <button
              className="button primary"
              disabled={busy || actor.role === "ADMIN_DEMO"}
            >
              {t("Grant permission")}
            </button>
          </form>
          <small className="muted">
            {t(
              "Only the resource owner can grant or revoke access. Administrators cannot approve someone else’s funds.",
            )}
          </small>
        </section>
      </div>
      <section className="panel">
        <h2>{t("Resource permissions")}</h2>
        {query.isPending ? (
          <Loading />
        ) : query.error ? (
          <Notice danger>{query.error.message}</Notice>
        ) : !query.data?.length ? (
          <Empty title={t("No permissions granted")} />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{t("Owner → recipient")}</th>
                  <th>{t("Resource")}</th>
                  <th>{t("Permission")}</th>
                  <th>{t("Status")}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {query.data.map((p) => (
                  <tr key={p.id}>
                    <td>
                      {p.owner_actor_id} → {p.target_actor_id}
                    </td>
                    <td>
                      <small>{label(p.resource_type)}</small>
                      {p.resource_id}
                    </td>
                    <td>{label(p.permission_type)}</td>
                    <td>
                      <Badge value={p.revoked_at ? "REVOKED" : "ACTIVE"} />
                    </td>
                    <td>
                      {p.owner_actor_id === actor.id && !p.revoked_at && (
                        <button
                          className="button small"
                          disabled={busy}
                          onClick={() =>
                            run(
                              () => api("/permissions/" + p.id, "DELETE"),
                              "Permission revoked. Dependent plans and approvals invalidated.",
                            )
                          }
                        >
                          {t("Revoke")}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <ActionsPanel actor={actor} notify={notify} />
    </>
  );
}
export function AuditPage() {
  const { t, label, time } = useI18n();

  const [category, setCategory] = useState("");
  const query = useData<Audit[]>(
    "audit",
    "/audit" + (category ? "?category=" + category : ""),
  );
  return (
    <>
      <PageHeader
        eyebrow={t("A RECORD YOU CAN FOLLOW")}
        title={t("Audit history")}
        description={t(
          "Evidence decisions, financial changes, blocked actions, and permissions leave a trace.",
        )}
      />
      <div className="tabs" role="group" aria-label={t("Audit category")}>
        {["", "FINANCIAL", "AI", "SECURITY", "PERMISSION", "ACTION"].map(
          (c) => (
            <button
              key={c}
              className={category === c ? "selected" : ""}
              onClick={() => setCategory(c)}
            >
              {c ? label(c) : t("All events")}
            </button>
          ),
        )}
      </div>
      <section className="panel audit-panel">
        <Notice>
          {t(
            "Append-only application history with chained SHA-256 hashes. Reset preserves history. Database operators remain a trust boundary.",
          )}
        </Notice>
        {query.isPending ? (
          <Loading />
        ) : query.error ? (
          <Notice danger>{query.error.message}</Notice>
        ) : !query.data?.length ? (
          <Empty title={t("No matching audit events")} />
        ) : (
          <div className="timeline">
            {query.data.map((e) => (
              <article className="timeline-event" key={e.id}>
                <div
                  className={`event-point ${e.category === "SECURITY" ? "security" : ""}`}
                />
                <div className="event-time">
                  <strong>#{e.sequence}</strong>
                  <small>{time(e.created_at)}</small>
                </div>
                <div className="event-content">
                  <div>
                    <h3>{label(e.event_type)}</h3>
                    <Badge value={e.category} />
                  </div>
                  <details>
                    <summary>{t("Inspect event details")}</summary>
                    <pre>{JSON.stringify(e.payload, null, 2)}</pre>
                    <small>
                      {t("Hash:")}
                      {e.event_hash}
                    </small>
                    <small>
                      {t("Previous:")}
                      {e.previous_hash}
                    </small>
                  </details>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
interface Benchmark {
  id: string;
  mode: string;
  case_count: number;
  seed: number;
  duration_ms: number;
  passed: number;
  failed: number;
  generated_at: string;
  categories: Record<
    string,
    { passed: number; total: number; metrics: Record<string, number> }
  >;
  baselines: {
    name: string;
    critical_coverage: number;
    on_time_coverage: number;
    constraint_violations: number;
    total_cost: number;
  }[];
  cases: {
    id: string;
    category: string;
    passed: boolean;
    duration_ms: number;
  }[];
}
export function BenchmarkPage({ notify }: Props) {
  const { t, money, percent, label, number, date, time } = useI18n();

  const query = useData<Benchmark | null>("benchmark", "/benchmark/latest");
  const { busy, run } = useTask(notify);
  const result = query.data;
  return (
    <>
      <PageHeader
        eyebrow={t("MEASURED, NEVER INVENTED")}
        title={t("Evaluation workbench")}
        description={t(
          "Deterministic ground truth. Reproducible cases. Computed results.",
        )}
        action={
          <div className="toolbar">
            <button
              className="button"
              disabled={busy}
              onClick={() =>
                run(
                  () => api("/benchmark/run", "POST", { mode: "FAST" }),
                  "FAST benchmark computed and saved.",
                )
              }
            >
              <Play size={15} />
              {t("Run FAST · 48")}
            </button>
            <button
              className="button primary"
              disabled={busy}
              onClick={() =>
                run(
                  () => api("/benchmark/run", "POST", { mode: "FULL" }),
                  "FULL benchmark computed and saved.",
                )
              }
            >
              <Play size={15} />
              {t("Run FULL · 500")}
            </button>
          </div>
        }
      />
      {busy && (
        <Notice>
          {t(
            "Running real cases against extraction, planning, replanning, and policy modules. Results appear when computation finishes.",
          )}
        </Notice>
      )}
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <Notice danger>{query.error.message}</Notice>
      ) : !result ? (
        <Empty title={t("No benchmark has been computed")}>
          {t(
            "Run FAST to evaluate 48 deterministic cases. No evaluation numbers are displayed before execution.",
          )}
        </Empty>
      ) : (
        <>
          <div className="plan-bar">
            <span>
              <Badge value={result.mode} /> {t("Seed")}
              {result.seed} · {date(result.generated_at)}{" "}
              {time(result.generated_at)}
            </span>
            <div className="toolbar">
              <a
                className="button small"
                download="lattice-benchmark.json"
                href="/api/v1/benchmark/export?format=json"
              >
                <Download size={14} />
                JSON
              </a>
              <a
                className="button small"
                download="lattice-benchmark.csv"
                href="/api/v1/benchmark/export?format=csv"
              >
                <Download size={14} />
                CSV
              </a>
            </div>
          </div>
          <div className="metrics">
            <Metric
              label={t("Cases computed")}
              value={String(result.case_count)}
              detail={`${result.mode} deterministic suite`}
            />
            <Metric
              label={t("Passed")}
              value={String(result.passed)}
              detail={t("Compared with generated ground truth")}
            />
            <Metric
              label={t("Failed")}
              value={String(result.failed)}
              detail={t("Failures remain visible")}
            />
            <Metric
              label={t("Wall time")}
              value={`${number(result.duration_ms / 1000)} ${t("seconds")}`}
              detail={t("Measured in this run")}
            />
          </div>
          <div className="evaluation-grid">
            {Object.entries(result.categories).map(([name, category]) => (
              <section className="panel" key={name}>
                <div className="panel-heading">
                  <h2>{label(name)}</h2>
                  <span className="count">
                    {category.passed}/{category.total}
                  </span>
                </div>
                <dl>
                  {Object.entries(category.metrics).map(([k, v]) => (
                    <div key={k}>
                      <dt>{label(k)}</dt>
                      <dd>
                        {k.includes("rate") ||
                        k.includes("accuracy") ||
                        k.includes("precision") ||
                        k.includes("coverage")
                          ? percent(v)
                          : number(v)}
                      </dd>
                    </div>
                  ))}
                </dl>
              </section>
            ))}
          </div>
          <section className="panel">
            <h2>{t("Planning baselines")}</h2>
            <p className="caption">
              {t(
                "B0–B3 are deterministic approximations, not evaluations of external language models. Coverage is measured against the same scenarios.",
              )}
            </p>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>{t("Baseline")}</th>
                    <th>{t("Critical coverage")}</th>
                    <th>{t("On-time coverage")}</th>
                    <th>{t("Violations")}</th>
                    <th>{t("Mean cost")}</th>
                  </tr>
                </thead>
                <tbody>
                  {result.baselines.map((b) => (
                    <tr key={b.name}>
                      <td>
                        <strong>{t(b.name)}</strong>
                      </td>
                      <td>{percent(b.critical_coverage)}</td>
                      <td>{percent(b.on_time_coverage)}</td>
                      <td>{b.constraint_violations}</td>
                      <td>{money(b.total_cost)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="panel">
            <details>
              <summary>
                {t("Inspect all")}
                {result.case_count} {t("case outcomes")}
              </summary>
              <div className="table-scroll case-results">
                <table>
                  <thead>
                    <tr>
                      <th>{t("Case")}</th>
                      <th>{t("Category")}</th>
                      <th>{t("Result")}</th>
                      <th>{t("Time")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.cases.map((c) => (
                      <tr key={c.id}>
                        <td>{c.id}</td>
                        <td>{label(c.category)}</td>
                        <td>
                          <Badge value={c.passed ? "VERIFIED" : "FAILED"} />
                        </td>
                        <td>{c.duration_ms.toFixed(2)} ms</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </section>
        </>
      )}
    </>
  );
}
