import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Check } from "lucide-react";
import { apiUrl, send, useApi } from "../api";
import { amount, day, percent, usd, when } from "../format";
import { Notice, PageHead, Segmented, Skeleton, StatusBadge, useDataset } from "../components/ui";

interface Row {
  id: string; vendor: string; department: string; category: string | null; date: string; amount: number; currency: string;
  amount_usd: number; score: number; reasons: string[]; status: string; labelled_anomaly: boolean;
}
interface QueueData {
  method: string; budget: number; selected: string; statuses: string[];
  methods: { key: string; label: string; blurb: string }[]; rows: Row[];
}
interface CaseRecord { status: string; reviewer: string; notes: string; version: number; updated_at?: string }
interface Detail extends Row {
  rate: number; rate_source: string;
  dates: { invoice: string; approved: string; paid: string; approval_delay_days: number };
  details: { label: string; value: string | null }[];
  scores: { key: string; label: string; score: number; in_queue: boolean }[];
  evaluated: boolean;
  case: CaseRecord;
  history: (CaseRecord & { updated_at: string })[];
}

export default function Review() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { dataset } = useDataset();
  const [method, setMethod] = useState("");
  const [status, setStatus] = useState("");
  const queue = useApi<QueueData>(apiUrl("queue", { dataset, method, status }));
  const rows = queue.data?.rows ?? [];

  return (
    <>
      <PageHead title="Review queue">
        The {queue.data ? percent(queue.data.budget) : "10%"} of payments most worth a second look. Open one to see why it was flagged and
        record what you found.
      </PageHead>
      {queue.data && (
        <div className="row between" style={{ marginBottom: 14 }}>
          <Segmented label="Ranking method" value={queue.data.method} onChange={setMethod}
            options={queue.data.methods.map((item) => ({ key: item.key, label: item.label + (item.key === queue.data!.selected ? " ★" : "") }))} />
          <Segmented label="Case status" value={status} onChange={setStatus}
            options={[{ key: "", label: "All" }, ...queue.data.statuses.map((item) => ({ key: item, label: item }))]} />
        </div>
      )}
      {queue.data && <p className="small muted" style={{ marginTop: -6 }}>{queue.data.methods.find((item) => item.key === queue.data!.method)?.blurb} ★ = chosen on the validation period.</p>}

      {queue.error ? <Notice tone="warn">{queue.error}</Notice> : !queue.data ? <Skeleton height={480} /> : (
        <div className={`inbox ${id ? "has-selection" : ""}`}>
          <div className="inbox-list" role="list">
            {rows.length === 0 && <p className="muted" style={{ padding: 16 }}>Nothing matches these filters.</p>}
            {rows.map((row) => (
              <button key={row.id} type="button" className="inbox-item" role="listitem" aria-current={row.id === id}
                onClick={() => navigate(`/review/${row.id}`)}>
                <div className="row between" style={{ gap: 6 }}>
                  <strong>{row.vendor}</strong>
                  <strong className="num">{usd(row.amount_usd)}</strong>
                </div>
                <div className="row between small muted" style={{ gap: 6 }}>
                  <span>{row.department} · {day(row.date)}</span>
                  <StatusBadge status={row.status} />
                </div>
                <div className="small" style={{ marginTop: 4, color: "var(--brand)" }}>{row.reasons.join(" · ")}</div>
              </button>
            ))}
          </div>
          <div className="inbox-detail">
            {id ? <TransactionDetail id={id} onSaved={queue.reload} /> : (
              <div className="muted" style={{ display: "grid", placeItems: "center", height: "100%", textAlign: "center" }}>
                <div><strong style={{ color: "var(--ink)" }}>Pick a payment from the list</strong><br />Its details, the reasons it was flagged and its case notes will appear here.</div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

function TransactionDetail({ id, onSaved }: { id: string; onSaved: () => void }) {
  const { dataset } = useDataset();
  const detail = useApi<Detail>(apiUrl(`transactions/${encodeURIComponent(id)}`, { dataset }));
  const [form, setForm] = useState<CaseRecord>({ status: "New", reviewer: "", notes: "", version: 0 });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ tone: "info" | "warn"; text: string }>();

  useEffect(() => {
    if (detail.data) setForm(detail.data.case);
    setMessage(undefined);
  }, [detail.data]);

  if (detail.error) return <Notice tone="warn">{detail.error}</Notice>;
  if (!detail.data) return <Skeleton height={400} />;
  const d = detail.data;

  const save = async () => {
    setSaving(true);
    try {
      await send(`/api/cases/${encodeURIComponent(id)}`, "PUT", form);
      setMessage({ tone: "info", text: "Case saved." });
      detail.reload();
      onSaved();
    } catch (error) {
      setMessage({ tone: "warn", text: (error as Error).message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="stack" style={{ gap: 18 }}>
      <Link to="/review" className="button" style={{ alignSelf: "flex-start" }}><ArrowLeft size={16} aria-hidden /> Queue</Link>
      <div>
        <div className="small muted">{d.id} · {d.department}{d.category ? ` · ${d.category}` : ""}</div>
        <div className="row between">
          <h2 style={{ fontSize: 24 }}>{d.vendor}</h2>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 24, fontWeight: 700 }} className="num">{usd(d.amount_usd)}</div>
            {d.currency !== "USD" && <div className="small muted num">{amount(d.amount, d.currency)} at {d.rate} USD each</div>}
          </div>
        </div>
      </div>

      <div>
        <div className="stat-label" style={{ marginBottom: 8 }}>Why it was flagged</div>
        <div className="row" style={{ gap: 6 }}>{d.reasons.map((reason) => <span key={reason} className="reason">{reason}</span>)}</div>
      </div>

      <div className="grid cols-3" style={{ gap: 10 }}>
        {d.scores.map((score) => (
          <div key={score.key} className="card" style={{ padding: 12 }}>
            <div className="stat-label">{score.label}</div>
            <div className="row" style={{ gap: 6 }}>
              {score.in_queue ? <><Check size={16} color="var(--brand)" aria-hidden /><strong>In its queue</strong></> : <span className="muted">Not in its queue</span>}
            </div>
          </div>
        ))}
      </div>

      <div>
        <div className="stat-label" style={{ marginBottom: 6 }}>Timeline</div>
        <div className="row small" style={{ gap: 18 }}>
          <span>Invoiced <strong>{day(d.dates.invoice)}</strong></span>
          <span>Approved <strong>{day(d.dates.approved)}</strong></span>
          <span>Paid <strong>{day(d.dates.paid)}</strong></span>
          <span className="muted">{Math.round(d.dates.approval_delay_days)} days to approve</span>
        </div>
      </div>

      <dl className="kv" style={{ margin: 0 }}>
        {d.details.map((item) => <div key={item.label}><dt>{item.label}</dt><dd>{item.value ?? "—"}</dd></div>)}
      </dl>

      <section className="card" style={{ background: "var(--surface-2)", boxShadow: "none" }}>
        <h3 style={{ marginBottom: 12 }}>Case</h3>
        <div className="stack">
          <Segmented label="Case status" value={form.status} onChange={(value) => setForm({ ...form, status: value })}
            options={["New", "In review", "Resolved", "Dismissed"].map((item) => ({ key: item, label: item }))} />
          <label className="field"><span>Reviewer</span>
            <input className="input" value={form.reviewer} maxLength={120} onChange={(event) => setForm({ ...form, reviewer: event.target.value })} placeholder="Your name" />
          </label>
          <label className="field"><span>Notes</span>
            <textarea className="input" value={form.notes} maxLength={5000} onChange={(event) => setForm({ ...form, notes: event.target.value })}
              placeholder="What did you check? What did you find?" />
          </label>
          {message && <Notice tone={message.tone}>{message.text}</Notice>}
          <div className="row between">
            <span className="small muted">{form.version ? `Version ${form.version}` : "Not saved yet"}</span>
            <button className="button button-primary" type="button" onClick={save} disabled={saving}>{saving ? "Saving…" : "Save case"}</button>
          </div>
        </div>
      </section>

      {d.history.length > 0 && (
        <div>
          <div className="stat-label" style={{ marginBottom: 10 }}>History</div>
          <div className="timeline">
            {[...d.history].reverse().map((entry) => (
              <div key={entry.version}>
                <div className="row" style={{ gap: 8 }}><StatusBadge status={entry.status} /><span className="small muted">{when(entry.updated_at)}{entry.reviewer ? ` · ${entry.reviewer}` : ""}</span></div>
                {entry.notes && <div className="small" style={{ whiteSpace: "pre-wrap" }}>{entry.notes}</div>}
              </div>
            ))}
          </div>
        </div>
      )}
      {!d.evaluated && <Notice>This payment is outside the test period, so it doesn't count toward the accuracy figures.</Notice>}
      {d.labelled_anomaly && <p className="small muted">In the evaluation labels this payment is marked as a genuine anomaly.</p>}
    </div>
  );
}
