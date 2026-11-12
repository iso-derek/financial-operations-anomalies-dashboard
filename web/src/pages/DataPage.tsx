import { useState, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Download, FileUp } from "lucide-react";
import { apiUrl, send } from "../api";
import { Card, Notice, PageHead, useDataset } from "../components/ui";

const TRANSACTION_COLUMNS = ["transaction_id", "invoice_id", "vendor_id", "vendor_name", "department", "transaction_date", "invoice_date",
  "approval_date", "amount", "currency", "payment_status", "approval_level", "account_age_days", "vendor_risk_score",
  "previous_failed_payments", "urgent_payment_flag", "is_anomaly"];
const RATE_COLUMNS = ["currency", "rate_date", "usd_per_unit", "source"];

function FilePicker({ label, file, onPick }: { label: string; file: File | null; onPick: (file: File | null) => void }) {
  return (
    <label className="dropzone">
      <FileUp size={24} aria-hidden style={{ color: "var(--brand)" }} />
      <div><strong>{file ? file.name : label}</strong></div>
      <div className="small muted">{file ? `${(file.size / 1024).toFixed(0)} KB` : "Click to choose a CSV file"}</div>
      <input type="file" accept=".csv,text/csv" hidden onChange={(event: ChangeEvent<HTMLInputElement>) => onPick(event.target.files?.[0] ?? null)} />
    </label>
  );
}

export default function DataPage() {
  const { dataset, label, setDataset } = useDataset();
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState<File | null>(null);
  const [rates, setRates] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  const analyse = async () => {
    if (!transactions || !rates) return;
    setBusy(true);
    setError(undefined);
    try {
      const result = await send<{ dataset: string; transactions: number }>("/api/upload", "POST", {
        transactions_csv: await transactions.text(), rates_csv: await rates.text(),
      });
      setDataset(result.dataset, `${transactions.name} · ${result.transactions.toLocaleString()} payments`);
      navigate("/");
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHead title="Your data">Analyse your own payments, or keep exploring the demo. Files are processed in memory and not saved.</PageHead>
      <Card title="Now showing" action={dataset !== "demo" ? <button className="button" type="button" onClick={() => setDataset("demo", "Demo data")}>Back to demo data</button> : null}>
        <div className="row between">
          <strong>{label}</strong>
          <a className="button" href={apiUrl("downloads/scores", { dataset })}><Download size={16} aria-hidden /> Download scored payments</a>
        </div>
      </Card>
      <Card title="Upload payments" className="section" sub="Two CSV files: the payments, and the exchange rates to convert them to US dollars">
        <div className="grid cols-2">
          <FilePicker label="Payments CSV" file={transactions} onPick={setTransactions} />
          <FilePicker label="Exchange rates CSV" file={rates} onPick={setRates} />
        </div>
        {error && <div className="section"><Notice tone="warn">{error}</Notice></div>}
        <div className="row section" style={{ justifyContent: "flex-end" }}>
          <button className="button button-primary" type="button" disabled={!transactions || !rates || busy} onClick={analyse}>
            {busy ? "Analysing…" : "Analyse my data"}
          </button>
        </div>
      </Card>
      <Card title="What the files need" className="section">
        <p className="small" style={{ marginTop: 0 }}><strong>Payments</strong> — at least 100 rows with these columns:</p>
        <p className="small muted" style={{ wordBreak: "break-word" }}>{TRANSACTION_COLUMNS.join(", ")}</p>
        <p className="small"><strong>Exchange rates</strong> — one row per currency and date, giving US dollars per unit, with the rate's source:</p>
        <p className="small muted">{RATE_COLUMNS.join(", ")}</p>
        <p className="small muted">Each payment uses the latest rate available on its payment date. <code>is_anomaly</code> (0 or 1) is only used to measure accuracy.</p>
      </Card>
    </>
  );
}
