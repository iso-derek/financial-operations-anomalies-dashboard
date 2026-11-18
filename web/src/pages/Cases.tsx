import { useState } from "react";
import { Link } from "react-router-dom";
import { apiUrl, useApi } from "../api";
import { usd, when } from "../format";
import { Card, Notice, PageHead, Segmented, Skeleton, StatusBadge, useDataset } from "../components/ui";

interface CaseRow {
  transaction_id: string; status: string; reviewer: string; notes: string; version: number; updated_at: string;
  vendor: string | null; amount_usd: number | null; reasons: string[];
}

export default function Cases() {
  const { dataset } = useDataset();
  const [status, setStatus] = useState("");
  const { data, error } = useApi<{ statuses: string[]; rows: CaseRow[] }>(apiUrl("cases", { dataset }));
  if (error) return <Notice tone="warn">{error}</Notice>;
  if (!data) return <Skeleton height={300} />;
  const rows = status ? data.rows.filter((row) => row.status === status) : data.rows;
  const counts = Object.fromEntries(data.statuses.map((item) => [item, data.rows.filter((row) => row.status === item).length]));

  return (
    <>
      <PageHead title="Cases">Every payment someone has opened a case on, most recently updated first. Each save is kept in the case history.</PageHead>
      <div className="grid cols-4" style={{ marginBottom: 14 }}>
        {data.statuses.map((item) => (
          <div key={item} className="card"><StatusBadge status={item} /><div className="stat-value">{counts[item]}</div></div>
        ))}
      </div>
      <Card action={<Segmented label="Status" value={status} onChange={setStatus}
        options={[{ key: "", label: "All" }, ...data.statuses.map((item) => ({ key: item, label: item }))]} />} title="All cases">
        {rows.length === 0 ? (
          <p className="muted">No cases yet. Open a payment in the <Link to="/review">review queue</Link> and save a case.</p>
        ) : (
          <div className="scroll-x">
            <table className="table">
              <thead><tr><th>Payment</th><th>Status</th><th>Reviewer</th><th>Notes</th><th className="right">Amount</th><th className="right">Updated</th></tr></thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.transaction_id}>
                    <td><Link to={`/review/${row.transaction_id}`}><strong>{row.vendor ?? row.transaction_id}</strong></Link><div className="small muted">{row.transaction_id}</div></td>
                    <td><StatusBadge status={row.status} /></td>
                    <td>{row.reviewer || <span className="muted">—</span>}</td>
                    <td className="small" style={{ maxWidth: 320 }}>{row.notes || <span className="muted">—</span>}</td>
                    <td className="right">{usd(row.amount_usd)}</td>
                    <td className="right small muted">{when(row.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <p className="small muted section">Cases are stored in a local database on this computer. Shared use would need sign-in and access controls.</p>
    </>
  );
}
