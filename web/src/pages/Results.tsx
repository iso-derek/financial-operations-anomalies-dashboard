import { apiUrl, useApi } from "../api";
import { percent, usd } from "../format";
import { Card, Notice, PageHead, Skeleton, Stat, useDataset } from "../components/ui";

interface ResearchData {
  methods: { key: string; label: string; blurb: string; reviewed: number; precision: number; recall: number | null; value: number; selected: boolean }[];
  budget: number; hybrid_weight: number; large_payment_threshold: number; purged: number;
  partitions: Record<string, number>; test_transactions: number; labelled_anomalies: number; interpretation: string;
}

export default function Results() {
  const { dataset } = useDataset();
  const { data, error } = useApi<ResearchData>(apiUrl("research", { dataset }));
  if (error) return <Notice tone="warn">{error}</Notice>;
  if (!data) return <Skeleton height={360} />;
  const best = data.methods.find((method) => method.selected)!;

  return (
    <>
      <PageHead title="How well does the queue work?">
        Each method picks its top {percent(data.budget)} of payments from a later period it never learned from. Here's how many of those
        picks were real problems.
      </PageHead>
      <div className="grid cols-3">
        <Stat label="Payments in the test period" value={data.test_transactions.toLocaleString()} />
        <Stat label="Known problems among them" value={data.labelled_anomalies.toLocaleString()} note={`${percent(data.labelled_anomalies / data.test_transactions, 1)} of payments`} />
        <Stat label="Method in use" value={best.label} note="Chosen on the earlier validation period" />
      </div>

      <div className="grid cols-3 section">
        {data.methods.map((method) => (
          <Card key={method.key} title={method.label} sub={method.blurb} className={method.selected ? "selected" : ""}
            action={method.selected ? <span className="tag" style={{ background: "var(--brand-soft)", color: "var(--brand)" }}>In use</span> : null}>
            <div className="stack">
              <div>
                <div className="stat-value">{Math.round(method.precision * method.reviewed)} <span className="muted" style={{ fontSize: 16 }}>of {method.reviewed}</span></div>
                <div className="small muted">reviewed payments were real problems ({percent(method.precision)})</div>
              </div>
              <div>
                <div className="row between small"><span>Share of all problems caught</span><strong>{percent(method.recall)}</strong></div>
                <div className="bar-track" style={{ marginTop: 6 }}><span style={{ width: `${(method.recall ?? 0) * 100}%` }} /></div>
              </div>
              <div className="row between small"><span>Value of problems caught</span><strong className="num">{usd(method.value, true)}</strong></div>
            </div>
          </Card>
        ))}
      </div>

      <Card title="How the test is kept fair" className="section">
        <ul style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 6 }}>
          <li>Payments are split by time: {data.partitions.train?.toLocaleString()} to learn from, {data.partitions.validation?.toLocaleString()} to choose the method, and {data.partitions.test?.toLocaleString()} to test it.</li>
          <li>The labels of which payments are real problems are never used to train the models — only to score them afterwards.</li>
          <li>{data.purged} repeat invoices were removed from later periods, so the same invoice can't help the model in both training and testing.</li>
          <li>"Unusually large" means at least {usd(data.large_payment_threshold)}, the top 5% of payments in the learning period.</li>
          <li>The blend uses {percent(data.hybrid_weight)} machine learning and {percent(1 - data.hybrid_weight)} rules, picked on the validation period.</li>
        </ul>
      </Card>
      <div className="section"><Notice>{data.interpretation.replace("Retrospective synthetic audit; captured labelled value is not fraud loss or savings.", "This is a look back at labelled demo data. The value of problems caught is not proven fraud or money saved.")}</Notice></div>
    </>
  );
}
