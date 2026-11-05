import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api, { errMsg } from "../api";

export default function Auth({ register }) {
  const nav = useNavigate();
  const [f, setF] = useState({}); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const go = async (e) => {
    e.preventDefault(); setBusy(true); setErr("");
    try {
      const { data } = await api.post(register ? "/auth/register" : "/auth/login", f);
      localStorage.setItem("token", data.token); localStorage.setItem("user", JSON.stringify(data.user)); nav("/");
    } catch (x) { setErr(errMsg(x)); } finally { setBusy(false); }
  };
  const fields = register
    ? [["full_name", "Full name"], ["username", "Username"], ["email", "Email", "email"], ["password", "Password", "password"], ["confirm_password", "Confirm password", "password"]]
    : [["identifier", "Username or email"], ["password", "Password", "password"]];
  return (
    <div className="mx-auto grid min-h-screen max-w-md content-center gap-6 px-5">
      <h1 className="font-display text-4xl">{register ? "Join Debatrix" : "Back to the floor"}</h1>
      <form onSubmit={go} className="grid gap-3">
        {fields.map(([k, l, t]) => <label key={k} className="grid gap-1 text-sm text-mute">{l}<input required type={t || "text"} className="input" onChange={set(k)} /></label>)}
        {err && <p role="alert" className="text-sm text-red-400">{err}</p>}
        <button className="btn" disabled={busy}>{register ? "Create account" : "Log in"}</button>
      </form>
      <Link className="text-sm text-mute hover:text-white" to={register ? "/login" : "/register"}>{register ? "Have an account? Log in" : "New here? Create an account"}</Link>
    </div>
  );
}
