import { createContext, useContext, useState, type ReactNode } from "react";
import { AlertTriangle, Info } from "lucide-react";
import { STATUS_TONE } from "../format";

export function PageHead({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <header className="page-head">
      <h2>{title}</h2>
      {children && <p>{children}</p>}
    </header>
  );
}

export function Card({ title, sub, action, children, className = "" }: {
  title?: string; sub?: ReactNode; action?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      {(title || action) && (
        <div className="card-head">
          <div>{title && <h3>{title}</h3>}{sub && <div className="card-sub">{sub}</div>}</div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function Stat({ label, value, note }: { label: string; value: ReactNode; note?: ReactNode }) {
  return (
    <div className="card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {note && <div className="stat-note">{note}</div>}
    </div>
  );
}

export function Segmented<T extends string>({ options, value, onChange, label }: {
  options: { key: T; label: string }[]; value: T; onChange: (value: T) => void; label: string;
}) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((option) => (
        <button key={option.key} type="button" aria-pressed={option.key === value} onClick={() => onChange(option.key)}>{option.label}</button>
      ))}
    </div>
  );
}

export function Notice({ tone = "info", children }: { tone?: "info" | "warn"; children: ReactNode }) {
  const Icon = tone === "warn" ? AlertTriangle : Info;
  return <div className={`notice notice-${tone}`}><Icon size={18} style={{ flexShrink: 0, marginTop: 2 }} aria-hidden /><div>{children}</div></div>;
}

export function Skeleton({ height = 120 }: { height?: number }) {
  return <div className="skeleton" style={{ height }} role="status" aria-label="Loading" />;
}

export function StatusBadge({ status }: { status: string }) {
  return <span className="status" style={{ color: STATUS_TONE[status] ?? "var(--muted)" }}>{status}</span>;
}

// ---------- which dataset is active (demo, or an upload held by the server) ----------
interface DatasetState { dataset: string; label: string; setDataset: (key: string, label: string) => void }
const DatasetContext = createContext<DatasetState | null>(null);

const STORAGE_KEY = "audit-desk-dataset";

function initialDataset(): { dataset: string; label: string } {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null");
    if (saved && typeof saved.dataset === "string" && saved.dataset.startsWith("usa-")) return saved;
  } catch {
    /* ignore */
  }
  return { dataset: "demo", label: "Demo data" };
}

export function DatasetProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState(initialDataset);
  const setDataset = (dataset: string, label: string) => {
    setState({ dataset, label });
    try {
      // Public datasets can be reloaded from the server; uploads live only in server memory, so they aren't remembered.
      if (dataset.startsWith("usa-")) localStorage.setItem(STORAGE_KEY, JSON.stringify({ dataset, label }));
      else localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* storage unavailable */
    }
  };
  return (
    <DatasetContext.Provider value={{ ...state, setDataset }}>
      {children}
    </DatasetContext.Provider>
  );
}

export function useDataset(): DatasetState {
  const value = useContext(DatasetContext);
  if (!value) throw new Error("useDataset must be used inside DatasetProvider");
  return value;
}
