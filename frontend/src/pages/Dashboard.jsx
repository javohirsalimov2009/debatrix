import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

const Stat = ({ l, v }) => <div className="panel"><div className="text-sm text-mute">{l}</div><div className="font-display text-3xl">{v}</div></div>;

export default function Dashboard() {
  const [s, setS] = useState(null); const [recent, setRecent] = useState(null); const [p, setP] = useState(null);
  const name = JSON.parse(localStorage.getItem("user") || "{}").full_name?.split(" ")[0];
  useEffect(() => {
    api.get("/statistics/overview").then((r) => setS(r.data));
    api.get("/debates?size=8").then((r) => setRecent(r.data.items));
    api.get("/statistics/progress").then((r) => setP(r.data));
  }, []);
  if (!s || !recent) return <p className="text-mute">Loading…</p>;
  const mins = Math.round(s.total_speaking_seconds / 60);
  return (
    <div className="grid gap-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="font-display text-4xl">Welcome, {name}.</h1>
        <Link to="/practice" className="btn">Start practice</Link>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <Stat l="Debates" v={s.total_debates} /><Stat l="Average" v={s.average_score} /><Stat l="Best" v={s.highest_score} />
        <Stat l="Minutes spoken" v={mins} /><Stat l="Trend" v={p ? (p.trend > 0 ? "+" : "") + p.trend : "–"} />
      </div>
      <section className="panel">
        <h2 className="mb-4 font-bold">Skills (average out of 10)</h2>
        {s.total_debates === 0 ? <p className="text-mute">No data yet. Finish a debate to see your strengths.</p> :
          Object.entries(s.skills).map(([k, v]) => v == null ? null : (
            <div key={k} className="mb-2 grid grid-cols-[9rem_1fr_2rem] items-center gap-3 text-sm">
              <span className="capitalize text-mute">{k.replace("_", " ")}</span>
              <div className="h-2 rounded bg-ink"><div className="h-2 rounded bg-accent" style={{ width: `${v * 10}%` }} /></div><span>{v}</span>
            </div>))}
      </section>
      <section>
        <h2 className="mb-3 font-bold">Recent sessions</h2>
        {recent.length === 0 ? <p className="text-mute">Nothing yet. Your first motion is one click away.</p> :
          <ul className="grid gap-2">{recent.map((d) => (
            <li key={d.id}><Link to={`/results/${d.id}`} className="panel flex items-center justify-between gap-4 hover:border-accent">
              <span><span className="block">{d.topic}</span><span className="text-sm text-mute">{d.assigned_side} · {d.duration_seconds}s · {new Date(d.started_at).toLocaleDateString()}</span></span>
              <span className="font-display text-2xl">{d.overall_score}</span></Link></li>))}</ul>}
      </section>
    </div>
  );
}
