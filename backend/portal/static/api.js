// Tiện ích gọi API dùng chung cho portal. Token JWT lưu ở localStorage("aa_token")
// – game Pygame (pygbag) chạy cùng domain đọc lại token này nên không phải đăng nhập lại.
const API = {
  token() { return localStorage.getItem("aa_token") || ""; },
  setToken(t) { t ? localStorage.setItem("aa_token", t) : localStorage.removeItem("aa_token"); },
  async req(method, url, body) {
    const h = { "Content-Type": "application/json" };
    if (this.token()) h.Authorization = "Bearer " + this.token();
    const r = await fetch(url, { method, headers: h, body: body ? JSON.stringify(body) : undefined });
    let data = null;
    try { data = await r.json(); } catch (e) {}
    if (!r.ok) {
      if (r.status === 401) this.setToken("");
      throw new Error((data && (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail))) || ("Lỗi " + r.status));
    }
    return data;
  },
  get(u) { return this.req("GET", u); },
  post(u, b) { return this.req("POST", u, b || {}); },
  patch(u, b) { return this.req("PATCH", u, b || {}); },
  del(u) { return this.req("DELETE", u); },
};
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmtDate = (s) => s ? new Date(s).toLocaleString("vi-VN") : "";
const resultPill = (w) => w === 0 ? '<span class="pill win">Thắng</span>' : w === -1 ? '<span class="pill draw">Hoà</span>' : '<span class="pill loss">Thua</span>';
const DIFF = { easy: "Dễ", normal: "Thường", hard: "Khó" };
function toast(msg) { const t = document.createElement("div"); t.className = "toast"; t.textContent = msg; document.body.appendChild(t); setTimeout(() => t.remove(), 2600); }
