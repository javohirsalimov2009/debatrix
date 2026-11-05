import axios from "axios";
const api = axios.create({ baseURL: "/api" });
api.interceptors.request.use((c) => { const t = localStorage.getItem("token"); if (t) c.headers.Authorization = `Bearer ${t}`; return c; });
api.interceptors.response.use((r) => r, (e) => { if (e.response?.status === 401 && localStorage.getItem("token")) { localStorage.clear(); location.href = "/login"; } return Promise.reject(e); });
export const errMsg = (e) => { const d = e.response?.data?.detail; return typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => x.msg).join(", ") : "Something went wrong. Try again."; };
export default api;
