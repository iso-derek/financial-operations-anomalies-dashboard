import { useState } from "react";
import { Link } from "react-router-dom";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowRight } from "lucide-react";
import { apiUrl, useApi } from "../api";
import { day, month, usd } from "../format";
import { Card, Notice, PageHead, Skeleton, Stat, useDataset } from "../components/ui";

interface OverviewData {
  departments: string[];
  kpis: { transactions: number; spend: number; flagged: number; currencies: number; start: string; end: string };
  by_department: { department: string; spend: number }[];
  monthly: { month: string; spend: number }[];
  vendors: { vendor: string; spend: number; flagged: number; transactions: number }[];
  method: string;
}

export default function Overview() {
  const { dataset } = useDataset();
  const [department, setDepartment] = useState("");
  const { data, error } = useApi<OverviewData>(apiUrl("overview", { dataset, department }));
  if (error) return <Notice tone="warn">{error}</Notice>;
  if (!data) return <Skeleton height={420} />;
  const { kpis } = data;

  return (
    <>
      <PageHead title="Spending at a glance">
        Payments from {day(kpis.start)} to {day(kpis.end)} — the period the review model is judged on. Amounts are converted to US dollars.
      </PageHead>
      {dataset === "demo" && <div style={{ marginBottom: 14 }}><Notice tone="warn">Demo data: vendors, amounts and exchange rates are fictional.</Notice></div>}

      <div className="row between" style={{ marginBottom: 14 }}>
        <label className="row" style={{ gap: 8 }}>
          <span className="stat-label">Department</span>
          <select className="input" style={{ width: "auto" }} value={department} onChange={(event) => setDepartment(event.target.value)}>
            <option value="">All departments</option>
            {data.departments.map((name) => <option key={name}>{name}</option>)}
          </select>
        </label>
        <Link className="button button-primary" to="/review">Open review queue <ArrowRight size={16} aria-hidden /></Link>
      </div>

      <div className="grid cols-4">
        <Stat label="Payments" value={kpis.transactions.toLocaleString()} note={`In ${kpis.currencies} currencies`} />
        <Stat label="Total spend" value={usd(kpis.spend, true)} note="US dollar equivalent" />
        <Stat label="Flagged for review" value={kpis.flagged.toLocaleString()} note={`By ${data.method.toLowerCase()}`} />
        <Stat label="Average payment" value={usd(kpis.transactions ? kpis.spend / kpis.transactions : null)} note="Per transaction" />
      </div>

      <div className="grid cols-2 section">
        <Card title="Spend by department">
          <div style={{ height: Math.max(240, data.by_department.length * 32) }}>
            <ResponsiveContainer>
              <BarChart data={data.by_department} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid horizontal={false} />
                <XAxis type="number" tickFormatter={(value) => usd(value, true)} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="department" width={128} tickLine={false} axisLine={false} />
                <Tooltip cursor={{ fill: "var(--surface-2)" }} content={({ active, payload }) => active && payload?.length ? (
                  <div className="tooltip"><strong>{String(payload[0].payload.department)}</strong><div>{usd(Number(payload[0].value))}</div></div>
                ) : null} />
                <Bar dataKey="spend" fill="var(--brand)" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Spend by month">
          <div style={{ height: 300 }}>
            <ResponsiveContainer>
              <AreaChart data={data.monthly} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="spendFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--brand)" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="var(--brand)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="month" tickFormatter={month} tickLine={false} axisLine={false} />
                <YAxis tickFormatter={(value) => usd(value, true)} width={60} tickLine={false} axisLine={false} domain={[0, "auto"]} />
                <Tooltip content={({ active, payload, label }) => active && payload?.length ? (
                  <div className="tooltip"><strong>{month(String(label))}</strong><div>{usd(Number(payload[0].value))}</div></div>
                ) : null} />
                <Area dataKey="spend" stroke="var(--brand)" strokeWidth={2} fill="url(#spendFill)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card title="Vendors to watch" sub="Most flagged payments first" className="section">
        <div className="scroll-x">
          <table className="table">
            <thead><tr><th>Vendor</th><th className="right">Payments</th><th className="right">Flagged</th><th className="right">Spend</th></tr></thead>
            <tbody>
              {data.vendors.map((vendor) => (
                <tr key={vendor.vendor}>
                  <td>{vendor.vendor}</td>
                  <td className="right">{vendor.transactions}</td>
                  <td className="right"><strong style={{ color: vendor.flagged ? "var(--brand)" : undefined }}>{vendor.flagged}</strong></td>
                  <td className="right">{usd(vendor.spend)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
