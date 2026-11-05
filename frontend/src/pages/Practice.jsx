import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Mic, Square, Type, RotateCcw } from "lucide-react";
import api, { errMsg } from "../api";

const CATS = ["Random", "Technology", "Education", "Politics", "Economics", "Environment", "Society", "Ethics", "Science", "International Relations", "Business", "Artificial Intelligence"];
const DURS = [[30, "30 sec"], [120, "2 min"], [300, "5 min"], [600, "10 min"]];
const fmt = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

export default function Practice() {
  const nav = useNavigate();
  const [stage, setStage] = useState("setup"); // setup | loading | brief | speak | judging
  const [cat, setCat] = useState("Random"); const [dur, setDur] = useState(120);
  const [d, setD] = useState(null); const [mode, setMode] = useState("voice");
  const [left, setLeft] = useState(0); const [prep, setPrep] = useState(null);
  const [rec, setRec] = useState(false); const [blob, setBlob] = useState(null); const [text, setText] = useState("");
  const [err, setErr] = useState(""); const mr = useRef(null); const chunks = useRef([]); const stream = useRef(null);

  const start = async () => {
    setStage("loading"); setErr("");
    try { setD((await api.post("/debates/start", { category: cat, duration_seconds: dur })).data); setStage("brief"); }
    catch (e) { setErr(errMsg(e)); setStage("setup"); }
  };
  useEffect(() => { if (prep === null) return; if (prep <= 0) { begin(); return; } const t = setTimeout(() => setPrep(prep - 1), 1000); return () => clearTimeout(t); }, [prep]);
  useEffect(() => { if (stage !== "speak" || blob) return; if (left <= 0) { finish(); return; } const t = setTimeout(() => setLeft(left - 1), 1000); return () => clearTimeout(t); }, [stage, left, blob]);

  const begin = async () => {
    setPrep(null); setErr("");
    if (mode === "voice") {
      try {
        stream.current = await navigator.mediaDevices.getUserMedia({ audio: true });
        mr.current = new MediaRecorder(stream.current); chunks.current = [];
        mr.current.ondataavailable = (e) => chunks.current.push(e.data);
        mr.current.onstop = () => { setBlob(new Blob(chunks.current, { type: "audio/webm" })); stream.current.getTracks().forEach((t) => t.stop()); };
        mr.current.start(); setRec(true);
      } catch { setErr("Microphone blocked. Allow access in your browser's address bar, or switch to text mode."); setMode("text"); }
    }
    setLeft(d.duration_seconds); setStage("speak");
  };
  const finish = () => { if (mode === "voice" && mr.current?.state === "recording") mr.current.stop(); setRec(false); if (mode === "text") submit(); };
  const discard = () => { setBlob(null); begin(); };
  const submit = async () => {
    setStage("judging");
    const fd = new FormData(); fd.append("mode", mode);
    if (mode === "voice") fd.append("audio", blob, "speech.webm"); else fd.append("text", text);
    try { await api.post(`/debates/${d.id}/submit`, fd); nav(`/results/${d.id}`); }
    catch (e) { setErr(errMsg(e)); setStage("speak"); }
  };

  if (stage === "setup") return (
    <div className="grid gap-6">
      <h1 className="font-display text-4xl">Take the floor.</h1>
      <fieldset><legend className="mb-2 text-sm text-mute">Topic category</legend>
        <div className="flex flex-wrap gap-2">{CATS.map((c) => <button key={c} onClick={() => setCat(c)} aria-pressed={cat === c} className={`rounded-md border px-3 py-1.5 text-sm ${cat === c ? "border-accent bg-accent/20" : "border-line"}`}>{c}</button>)}</div></fieldset>
      <fieldset><legend className="mb-2 text-sm text-mute">Speaking time</legend>
        <div className="flex gap-2">{DURS.map(([s, l]) => <button key={s} onClick={() => setDur(s)} aria-pressed={dur === s} className={`rounded-md border px-4 py-2 ${dur === s ? "border-accent bg-accent/20" : "border-line"}`}>{l}</button>)}</div></fieldset>
      {err && <p role="alert" className="text-red-400">{err}</p>}
      <button className="btn w-fit" onClick={start}>Start practice</button>
    </div>);

  if (stage === "loading") return <p className="py-24 text-center font-display text-2xl">The chair is drawing a motion…</p>;
  if (stage === "judging") return (
    <div className="py-24 text-center"><motion.div animate={{ rotate: [-12, 12, -12] }} transition={{ repeat: Infinity, duration: 1.2 }} className="mx-auto mb-6 h-1 w-40 origin-center bg-accent" />
      <p className="font-display text-2xl">The adjudicator is weighing your case…</p></div>);

  if (stage === "brief") return (
    <div className="grid gap-6">
      <p className="text-sm text-mute">The motion</p>
      <motion.h1 initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="font-display text-4xl">“{d.topic}”</motion.h1>
      <motion.div initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ delay: 0.6, duration: 0.5 }}
        className={`origin-left rounded-md p-6 ${d.assigned_side === "AFFIRMATIVE" ? "bg-pro/15 border border-pro" : "bg-accent/15 border border-accent"}`}>
        <div className="font-display text-3xl">{d.assigned_side === "AFFIRMATIVE" ? "You are Affirmative" : "You are Opposition"}</div>
        <p className="mt-1 text-mute">{d.assigned_side === "AFFIRMATIVE" ? "Defend the motion: argue that it is true." : "Oppose the motion: argue that it is false."} You have {fmt(d.duration_seconds)}.</p>
      </motion.div>
      <div className="flex gap-2">{[["voice", Mic, "Speak"], ["text", Type, "Type"]].map(([m, I, l]) => <button key={m} onClick={() => setMode(m)} aria-pressed={mode === m} className={`flex items-center gap-2 rounded-md border px-4 py-2 ${mode === m ? "border-accent bg-accent/20" : "border-line"}`}><I size={16} />{l}</button>)}</div>
      {prep === null ? <div className="flex gap-3"><button className="btn" onClick={begin}>Start now</button><button className="btn-ghost" onClick={() => setPrep(60)}>Use 60s to prepare</button></div>
        : <div className="flex items-center gap-4"><span className="font-display text-5xl">{fmt(prep)}</span><button className="btn" onClick={begin}>Skip, start speaking</button></div>}
      {err && <p role="alert" className="text-red-400">{err}</p>}
    </div>);

  return (
    <div className="grid gap-6">
      <p className="font-display text-xl text-mute">“{d.topic}” · {d.assigned_side.toLowerCase()}</p>
      <div className="font-display text-7xl" aria-live="off">{fmt(left)}</div>
      <div className="h-1.5 rounded bg-card"><div className="h-1.5 rounded bg-accent transition-all duration-1000 ease-linear" style={{ width: `${(left / d.duration_seconds) * 100}%` }} /></div>
      {err && <p role="alert" className="text-red-400">{err}</p>}
      {mode === "voice" ? (blob ? (
        <div className="grid gap-3"><audio controls src={URL.createObjectURL(blob)} className="w-full" />
          <div className="flex gap-3"><button className="btn" onClick={submit}>Submit argument</button><button className="btn-ghost flex items-center gap-2" onClick={discard}><RotateCcw size={16} />Discard and redo</button></div></div>
      ) : (
        <div className="flex items-center gap-4"><span className="flex items-center gap-2 text-red-400"><motion.span animate={{ opacity: [1, 0.2, 1] }} transition={{ repeat: Infinity, duration: 1.2 }} className="h-3 w-3 rounded-full bg-red-500" />{rec ? "Recording" : "Starting…"}</span>
          <button className="btn-ghost flex items-center gap-2" onClick={finish}><Square size={16} />Finish early</button></div>
      )) : (
        <div className="grid gap-3"><textarea className="input h-64" autoFocus value={text} disabled={left <= 0} onChange={(e) => setText(e.target.value)} placeholder="Make your case…" />
          <button className="btn w-fit" onClick={submit}>Submit argument</button></div>)}
    </div>);
}
