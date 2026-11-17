"""Lớp gọi API dùng được ở cả 2 môi trường:

* Trình duyệt (pygbag/WebAssembly): Python không mở socket trực tiếp được, nên ta
  chèn một đoạn JavaScript nhỏ (bridge) dùng fetch(); Python gửi yêu cầu rồi
  "hỏi vòng" (poll) kết quả mỗi khung hình mà không chặn vòng lặp game.
  Token JWT đọc từ localStorage("aa_token") – do portal web lưu khi đăng nhập.
* Desktop (python main.py): dùng urllib trong luồng phụ, token lưu ở file .aa_token.
"""
import asyncio
import json
import os
import sys

WEB = sys.platform == "emscripten"

BRIDGE_JS = r"""
window.AA = window.AA || {
  n: 0, res: {},
  token: function(){ return localStorage.getItem('aa_token') || ''; },
  setToken: function(t){ if(t){localStorage.setItem('aa_token', t);} else {localStorage.removeItem('aa_token');} return 'ok'; },
  req: function(method, url, body){
    var id = 'r' + (++this.n), self = this;
    var h = {'Content-Type': 'application/json'};
    var t = this.token(); if (t) h['Authorization'] = 'Bearer ' + t;
    fetch(url, {method: method, headers: h, body: body ? body : undefined})
      .then(function(r){ return r.text().then(function(x){ self.res[id] = JSON.stringify({status: r.status, body: x}); }); })
      .catch(function(e){ self.res[id] = JSON.stringify({status: 0, body: String(e)}); });
    return id;
  },
  get: function(id){ var v = this.res[id]; if (v !== undefined) { delete this.res[id]; return v; } return ''; },
  hash: function(){ return window.location.hash || ''; },
  clearHash: function(){ history.replaceState(null, '', window.location.pathname + window.location.search); return 'ok'; },
  go: function(u){ window.location.href = u; return 'ok'; }
};
'ok';
"""


class ApiError(Exception):
    def __init__(self, status, msg):
        super().__init__(msg)
        self.status = status


class Net:
    def __init__(self, base=None):
        self.base = base if base is not None else ("" if WEB else os.getenv("AA_API", "http://127.0.0.1:8000"))
        self.offline = False
        self._tokfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".aa_token")
        if WEB:
            import platform  # noqa: F401  (module do pygbag cung cấp)
            self._win = platform.window
            try:
                self._win.eval(BRIDGE_JS)
            except Exception:
                platform.eval(BRIDGE_JS)

    # ---------------------------------------------------------------- token
    def token(self):
        if WEB:
            return str(self._win.AA.token() or "")
        try:
            with open(self._tokfile) as f:
                return f.read().strip()
        except OSError:
            return ""

    def set_token(self, t):
        if WEB:
            self._win.AA.setToken(t or "")
            return
        try:
            if t:
                with open(self._tokfile, "w") as f:
                    f.write(t)
            elif os.path.exists(self._tokfile):
                os.remove(self._tokfile)
        except OSError:
            pass

    def url_hash(self):
        if WEB:
            try:
                return str(self._win.AA.hash() or "")
            except Exception:
                return ""
        return os.getenv("AA_HASH", "")

    def clear_hash(self):
        if WEB:
            try:
                self._win.AA.clearHash()
            except Exception:
                pass

    def go(self, url):
        if WEB:
            self._win.AA.go(url)

    # ---------------------------------------------------------------- request
    async def request(self, method, path, body=None, timeout=20.0):
        payload = json.dumps(body) if body is not None else ""
        if WEB:
            rid = self._win.AA.req(method, self.base + path, payload)
            waited = 0.0
            while True:
                raw = str(self._win.AA.get(rid) or "")
                if raw:
                    break
                await asyncio.sleep(0.03)
                waited += 0.03
                if waited > timeout:
                    raise ApiError(0, "Hết thời gian chờ máy chủ")
            res = json.loads(raw)
            status, text = res["status"], res["body"]
        else:
            status, text = await asyncio.get_event_loop().run_in_executor(
                None, self._desktop_request, method, path, payload, timeout)
        try:
            data = json.loads(text) if text else None
        except ValueError:
            data = None
        if status == 0:
            raise ApiError(0, "Không kết nối được máy chủ")
        if status >= 400:
            msg = data.get("detail") if isinstance(data, dict) else None
            if not isinstance(msg, str):
                msg = f"Lỗi {status}"
            if status == 401:
                self.set_token("")
            raise ApiError(status, msg)
        return data

    def _desktop_request(self, method, path, payload, timeout):
        import urllib.request
        import urllib.error
        req = urllib.request.Request(self.base + path, method=method,
                                     data=payload.encode() if payload else None,
                                     headers={"Content-Type": "application/json"})
        t = self.token()
        if t:
            req.add_header("Authorization", "Bearer " + t)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()
        except Exception as e:  # mất mạng / server tắt
            return 0, str(e)

    async def get(self, path):
        return await self.request("GET", path)

    async def post(self, path, body=None):
        return await self.request("POST", path, body if body is not None else {})

    async def put(self, path, body):
        return await self.request("PUT", path, body)
