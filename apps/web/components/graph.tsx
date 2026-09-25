"use client";
import { useI18n } from "@/lib/i18n/context";
import { useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MarkerType,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useData } from "@/lib/hooks";
import type { GraphData } from "@/lib/types";

import { Badge, Empty, Loading, PageHeader, Notice } from "./ui";
export function GraphPage() {
  const { t, label, money, date } = useI18n();

  const query = useData<GraphData>("graph", "/graph");
  const [selected, setSelected] = useState<Record<string, unknown> | null>(
    null,
  );
  const nodes = useMemo(
    () =>
      query.data?.nodes.map((n) => ({
        id: n.id,
        position: n.position,
        data: {
          label: (
            <div className="graph-node">
              <span>{label(n.type)}</span>
              <strong>{t(String(n.data.label))}</strong>
              {n.data.amount !== undefined && (
                <small>
                  {money(Number(n.data.amount), String(n.data.currency))}
                </small>
              )}
              <Badge value={String(n.data.state)} />
            </div>
          ),
        },
        style: {
          width: n.type === "actor" ? 170 : 235,
          borderRadius: 12,
          border:
            "1px solid " +
            (n.data.state === "BLOCKED"
              ? "#df968b"
              : n.data.state === "EXPECTED"
                ? "#d8b95c"
                : "#91beb2"),
          background: n.data.state === "EXPECTED" ? "#fffbed" : "white",
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      })) || [],
    [query.data, t, label, money],
  );
  const edges = useMemo(
    () =>
      query.data?.edges.map((e) => ({
        ...e,
        label:
          e.data.type === "allocation"
            ? money(Number(e.data.destination_amount), String(e.data.currency))
            : t(e.label),
        animated: e.data.risk_state === "EXPECTED",
        style: {
          stroke: e.data.risk_state === "EXPECTED" ? "#bd9435" : "#368571",
          strokeWidth: e.data.type === "allocation" ? 2 : 1,
        },
        labelStyle: { fill: "#28473f", fontSize: 11, fontWeight: 600 },
        labelBgPadding: [7, 4] as [number, number],
        markerEnd: { type: MarkerType.ArrowClosed, color: "#368571" },
      })) || [],
    [query.data, t, money],
  );
  return (
    <>
      <PageHeader
        eyebrow={t("02 / ORCHESTRATE")}
        title={t("Follow the funding.")}
        description={t(
          "Explore how actors, sources, payment routes, and commitments connect.",
        )}
      />
      <div className="graph-legend">
        {["VERIFIED", "EXPECTED", "AT RISK", "BLOCKED"].map((s) => (
          <Badge value={s} key={s} />
        ))}
        <span>{t("Click a node or allocation to inspect its details.")}</span>
      </div>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <Notice danger>{query.error.message}</Notice>
      ) : !nodes.length ? (
        <Empty title={t("The graph is empty")} />
      ) : (
        <div className="graph-layout">
          <section
            className="graph-canvas"
            aria-label={t("Funding-to-Obligation Graph")}
          >
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodesDraggable={false}
              fitView
              minZoom={0.3}
              maxZoom={1.5}
              ariaLabelConfig={{
                "controls.zoomIn.ariaLabel": t("Zoom in"),
                "controls.zoomOut.ariaLabel": t("Zoom out"),
                "controls.fitView.ariaLabel": t("Fit view"),
              }}
              onNodeClick={(_, n) =>
                setSelected(
                  query.data?.nodes.find((x) => x.id === n.id)?.data || null,
                )
              }
              onEdgeClick={(_, e) => setSelected(e.data || null)}
            >
              <Background gap={24} color="#dfe5e1" />
              <Controls showInteractive={false} />
            </ReactFlow>
          </section>
          <aside className="panel inspector">
            <span className="eyebrow">{t("INSPECTOR")}</span>
            <h2>
              {selected
                ? t(String(selected.label || "Allocation details"))
                : t("Select a connection")}
            </h2>
            {selected ? (
              <dl>
                {Object.entries(selected)
                  .filter(([k]) =>
                    [
                      "nominal_coverage",
                      "on_time_verified_coverage",
                      "state",
                      "amount",
                      "currency",
                      "beneficiary",
                      "due_date",
                      "available_from",
                      "verification_status",
                      "restriction_type",
                      "destination_amount",
                      "source_amount",
                      "source_currency",
                      "estimated_fee",
                      "transfer_route_id",
                      "scheduled_date",
                      "expected_arrival_date",
                      "verification_state",
                      "risk_state",
                      "type",
                    ].includes(k),
                  )
                  .map(([k, v]) => (
                    <div key={k}>
                      <dt>{label(k)}</dt>
                      <dd>
                        {k.includes("date") || k === "available_from"
                          ? date(String(v))
                          : k.includes("amount") || k === "estimated_fee"
                            ? money(
                                Number(v),
                                String(
                                  k === "source_amount" || k === "estimated_fee"
                                    ? selected.source_currency
                                    : selected.currency || "EUR",
                                ),
                              )
                            : t(String(v))}
                      </dd>
                    </div>
                  ))}
              </dl>
            ) : (
              <p className="muted">
                {t(
                  "Trace an allocation back to its source, route, timing, and verification state.",
                )}
              </p>
            )}
          </aside>
        </div>
      )}
    </>
  );
}
