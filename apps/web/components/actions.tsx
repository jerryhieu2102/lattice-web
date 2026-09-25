"use client";
import { useI18n } from "@/lib/i18n/context";
import { api } from "@/lib/api";
import { useData, useTask } from "@/lib/hooks";
import type { Actor, Notify, Action } from "@/lib/types";
import { Badge, Notice, Empty, Loading } from "./ui";
export function ActionsPanel({
  actor,
  notify,
}: {
  actor: Actor;
  notify: Notify;
}) {
  const { t, money, label } = useI18n();

  const query = useData<Action[]>("actions", "/actions");
  const { busy, run } = useTask(notify);
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">{t("PERMISSION-CONTROLLED")}</span>
          <h2>{t("Prepared sandbox actions")}</h2>
        </div>
        <span className="sandbox">{t("NO REAL MONEY")}</span>
      </div>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <Notice danger>{query.error.message}</Notice>
      ) : !query.data?.length ? (
        <Empty title={t("No actions prepared")}>
          {t(
            "A plan is a proposal. Preparation, approval, and sandbox execution are separate steps.",
          )}
        </Empty>
      ) : (
        <div className="actions-list">
          {query.data.map((a) => {
            const required =
              a.payload?.required_approvals || a.required_approvals || [];
            const approvals = a.payload?.approvals || a.approvals || [];
            return (
              <article className="action-row" key={a.id}>
                <div>
                  <strong>{label(a.type)}</strong>
                  <small>
                    {a.contribution_eur !== undefined
                      ? t(
                          `Your proposed contribution: ${money(a.contribution_eur)}`,
                        )
                      : t(
                          `Approvals: ${approvals.length}/${required.length} · ${required.join(", ")}`,
                        )}
                  </small>
                  <Badge value={a.status} />
                </div>
                <div className="toolbar">
                  {["PREPARED", "APPROVED"].includes(a.status) &&
                    required.includes(actor.id) &&
                    !approvals.includes(actor.id) && (
                      <button
                        className="button small"
                        disabled={busy}
                        onClick={() =>
                          run(
                            () =>
                              api("/actions/" + a.id + "/approve", "POST", {
                                confirmed: true,
                              }),
                            "Your approval was recorded. Other actors must approve their own funds.",
                          )
                        }
                      >
                        {t("Approve my part")}
                      </button>
                    )}
                  {["STUDENT", "ADMIN_DEMO"].includes(actor.role) &&
                    ["PREPARED", "APPROVED"].includes(a.status) && (
                      <button
                        className="button small primary"
                        disabled={busy}
                        onClick={() =>
                          run(
                            () =>
                              api(
                                "/actions/" + a.id + "/sandbox-execute",
                                "POST",
                              ),
                            "Sandbox execution completed; simulated state and audit updated.",
                          )
                        }
                      >
                        {t("Sandbox execute")}
                      </button>
                    )}
                </div>
              </article>
            );
          })}
        </div>
      )}
      <Notice>
        {t(
          "Execution requires every listed approval and a fresh state snapshot. Beneficiary changes invalidate authorization.",
        )}
      </Notice>
    </section>
  );
}
