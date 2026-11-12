import { NavLink, Route, Routes } from "react-router-dom";
import { BarChart3, FolderOpen, Gauge, Inbox, Search, Upload } from "lucide-react";
import { useDataset } from "./components/ui";
import Overview from "./pages/Overview";
import Review from "./pages/Review";
import Cases from "./pages/Cases";
import Results from "./pages/Results";
import DataPage from "./pages/DataPage";

const LINKS = [
  { to: "/", label: "Overview", icon: BarChart3 },
  { to: "/review", label: "Review", icon: Inbox },
  { to: "/cases", label: "Cases", icon: FolderOpen },
  { to: "/results", label: "Accuracy", icon: Gauge },
  { to: "/data", label: "Your data", icon: Upload },
];

export default function App() {
  const { label, dataset } = useDataset();
  return (
    <div className="layout">
      <nav className="rail" aria-label="Main">
        <div className="rail-logo" title="Audit Desk"><Search size={20} aria-hidden /></div>
        {LINKS.map(({ to, label: text, icon: Icon }) => (
          <NavLink key={to} to={to} end={to === "/"}><Icon size={20} aria-hidden />{text}</NavLink>
        ))}
      </nav>
      <div className="content">
        <div className="topline">
          <h1>Audit Desk</h1>
          <span className="tag" style={dataset === "demo" ? { background: "var(--warn-bg)", color: "var(--warn-ink)" } : undefined}>
            {label}
          </span>
        </div>
        <main className="page">
          <Routes>
            <Route index element={<Overview />} />
            <Route path="review" element={<Review />} />
            <Route path="review/:id" element={<Review />} />
            <Route path="cases" element={<Cases />} />
            <Route path="results" element={<Results />} />
            <Route path="data" element={<DataPage />} />
          </Routes>
        </main>
      </div>
      <nav className="mobile-nav" aria-label="Main">
        {LINKS.map(({ to, label: text, icon: Icon }) => (
          <NavLink key={to} to={to} end={to === "/"}><Icon size={20} aria-hidden />{text}</NavLink>
        ))}
      </nav>
    </div>
  );
}
