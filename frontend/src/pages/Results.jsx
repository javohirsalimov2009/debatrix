import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { animate, motion } from "framer-motion";
import api, { errMsg } from "../api";

const CRIT = [["logical_reasoning_score", "Logical reasoning"], ["argument_strength_score", "Argument strength"], ["clarity_score", "Clarity"], ["structure_score", "Structure"], ["relevance_score", "Relevance"], ["evidence_score", "Evidence"], ["delivery_score", "Delivery"]];
const level = (s) => (s >= 85 ? "Outstanding" : s >= 70 ? "Strong" : s >= 55 ? "Competent" : s >= 40 ? "Developing" : "Needs work");

function Counter({ to }) {
  const [v, setV] = useState(0);
  useEffect(() => { const c = animate(0, to, { duration: 1.4, onUpdate: (x) => setV(Math.round(x)) }); return () => c.stop(); }, [to]);
  return <span>{v}</span>;
}
const List = ({ title, items, open }) => items?.length ? (
  <details open={open} className="panel"><summary className="cursor-pointer font-bold">{title}</summary>
    <ul className="mt-3 grid list-disc gap-2 pl-5 text-mute">{items.map((x, i) => <li key={i}>{x}</li>)}</ul></details>) : null;

export default function Results() {
  const { id } = useParams(); const [r, setR] = useState(null); const [err, setErr] = useState("");
  useEffect(() => { api.get(`/evaluations/${id}`).then((x) => setR(x.data)).catch((e) => setErr(errMsg(e))); }, [id]);
  if (err) return <p role="alert" className="text-red-400">{err}</p>;
  if (!r) return <p className="text-mute">Loading…</p>;
  const e = r.evaluation, s = r.session;
  return (
    <div className="grid gap-5">
      <p className="text-mute">{s.assigned_side} · “{s.topic}”</p>
      <div className="flex items-end gap-4"><div className="font-display text-8xl"><Counter to={e.overall_score} /></div><div className="pb-3"><div className="text-mute">out of 100</div><div className="text-xl font-bold text-pro">{level(e.overall_score)}</div></div></div>
      <div className="panel grid gap-3">{CRIT.map(([k, l]) => (
        <div key={k} className="grid grid-cols-[10rem_1fr_3rem] items-center gap-3 text-sm"><span>{l}</span>
          {e[k] == null ? <span className="text-mute">Not available for text debates</span> :
            <><div className="h-2 rounded bg-ink"><motion.div className="h-2 rounded bg-accent" initial={{ width: 0 }} animate={{ width: `${e[k] * 10}%` }} transition={{ duration: 1 }} /></div><span>{e[k]}/10</span></>}</div>))}</div>
      <p className="panel">{e.overall_assessment}</p>
      <List title="What you did well" items={e.strengths} open /><List title="Areas for improvement" items={e.weaknesses} open />
      <details className="panel"><summary className="cursor-pointer font-bold">Logical fallacies</summary>
        {e.logical_fallacies.length === 0 ? <p className="mt-3 text-mute">None detected.</p> : e.logical_fallacies.map((f, i) => (
          <div key={i} className="mt-3"><b>{f.name}</b>{f.quote && <blockquote className="border-l-2 border-accent pl-3 text-mute">“{f.quote}”</blockquote>}<p className="text-mute">{f.explanation}</p></div>))}</details>
      <List title="Missed opportunities" items={e.missed_opportunities} /><List title="How to improve" items={e.improvement_suggestions} />
      <details className="panel"><summary className="cursor-pointer font-bold">A stronger version of your argument</summary><p className="mt-3 whitespace-pre-wrap text-mute">{e.improved_argument}</p></details>
      <p className="panel border-accent font-display text-xl">{e.final_verdict}</p>
      <div className="flex gap-3"><Link to="/practice" className="btn">Practice again</Link><Link to="/" className="btn-ghost">View history</Link></div>
    </div>);
}
