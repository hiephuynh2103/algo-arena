# Algo Arena – Game Card Battle học Thuật toán (Deck Building + Replay)

Game thẻ bài chạy trên trình duyệt. Mỗi lá bài là một **cấu trúc dữ liệu / chiến lược thuật toán** (Stack, Queue, BFS, Dijkstra, DP, Heap, …), có **chi phí, hiệu ứng và điều kiện sử dụng**. Giữa sân luôn có một **Bài toán** (ví dụ "Balo 0/1", "Đồ thị có cạnh âm"). Người chơi dùng đúng thẻ tối ưu thì được thưởng. Dùng thẻ "bẫy" (trông có vẻ đúng nhưng sai) thì hiệu ứng bị giảm một nửa. Sau trận, game giải thích từng quyết định, và mọi trận đều xem lại được bằng replay.

| Thành phần | Công nghệ |
|---|---|
| Game 2D | **Pygame-ce**, đóng gói WebAssembly bằng **pygbag** |
| Rule engine, AI | Python thuần, tất định (deterministic), dùng chung cho game và server |
| Backend | **FastAPI**, SQLAlchemy 2, JWT, bcrypt |
| CSDL | **PostgreSQL (Supabase)**; SQLite khi chạy local |
| Portal web | HTML/CSS/JS thuần: đăng nhập, dashboard, bảng xếp hạng, thư viện thẻ, trang quản trị |
| Deploy | **Render** (1 web service phục vụ API + portal + game ở `/play`) |

## Cấu trúc thư mục

```
algoarena/
├── game/                  # Game Pygame (thư mục được pygbag đóng gói)
│   ├── main.py            # vòng lặp async (bắt buộc với pygbag)
│   ├── engine/            # RULE ENGINE dùng chung
│   │   ├── cards.py       # 24 thẻ: chi phí, hiệu ứng, bài học, điều kiện mở khoá
│   │   ├── challenges.py  # 20 bài toán: thẻ tối ưu / chấp nhận được / bẫy + giải thích
│   │   ├── engine.py      # luật chơi, lượt, hiệu ứng, ghi nhận quyết định, replay
│   │   ├── ai.py          # AI 3 mức: ngẫu nhiên / tham lam / tìm kiếm DFS
│   │   ├── puzzles.py     # 6 thử thách mở khoá thẻ
│   │   └── tutorials.py   # 6 bài hướng dẫn theo chủ đề
│   ├── net.py             # gọi API: JS bridge (web) hoặc urllib (desktop)
│   ├── ui.py, scenes_*.py, scene_battle.py, scene_deck.py   # giao diện
│   ├── assets/            # font DejaVu (hỗ trợ tiếng Việt)
│   └── build/web/         # bản build WebAssembly (do pygbag tạo)
├── backend/
│   ├── app/main.py        # FastAPI app, phục vụ portal + /play
│   ├── app/db.py          # models: users, decks, matches, events
│   ├── app/routes_game.py # auth, deck, match (xác minh replay), puzzle, leaderboard, events
│   ├── app/routes_admin.py# quản lý user, thống kê, cân bằng thẻ
│   └── portal/            # index.html, admin.html, static/
├── tests/                 # pytest: engine + API
├── tools/simulate.py      # giải vét cạn puzzle, mô phỏng AI vs AI để cân bằng
├── tools/ui_smoke.py      # chạy game headless qua mọi màn hình, chụp ảnh
├── tools/build_web.py     # build pygbag
├── render.yaml, Dockerfile, requirements.txt
```

## Chạy trên máy (local)

```bash
pip install -r requirements-dev.txt
python tools/build_web.py                    # build game WebAssembly → game/build/web
cd backend && uvicorn app.main:app --port 9000
```

Mở http://127.0.0.1:9000 → đăng ký → **Vào game**. Tài khoản quản trị mặc định là `admin` / `admin123` (đổi bằng biến môi trường `ADMIN_USERNAME`, `ADMIN_PASSWORD`).

> ⚠️ Khi chạy local, **đừng dùng cổng 8000 với `localhost`**: pygbag coi `localhost:8000` là server dev của nó và sẽ tải thư viện sai chỗ. Dùng cổng khác như 9000, hoặc truy cập bằng `127.0.0.1`.

Chạy game bản desktop (tiện khi phát triển): `cd game && AA_API=http://127.0.0.1:9000 python main.py`

Kiểm thử:

```bash
python -m pytest -q tests          # 14 test engine + API
python tools/simulate.py 60        # kiểm tra puzzle + cân bằng AI
python tools/ui_smoke.py /tmp/shots  # cần backend chạy ở cổng 8000 (bản desktop)
```

## Deploy online (Supabase + Render), khoảng 20 phút

### Bước 1. Tạo CSDL PostgreSQL trên Supabase
1. Vào https://supabase.com, đăng nhập bằng GitHub, chọn **New project**. Đặt tên `algo-arena`, đặt **Database Password** (ghi lại), chọn **Region: Southeast Asia (Singapore)**.
2. Khi project tạo xong, bấm nút **Connect** ở đầu trang → tab **Connection string** → chọn **Session pooler**. Copy chuỗi dạng:
   `postgresql://postgres.abcxyz:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres`
   rồi thay `[YOUR-PASSWORD]` bằng mật khẩu ở bước 1.
   > Phải dùng **Session pooler** (IPv4) vì Render không kết nối được địa chỉ "Direct connection" (IPv6) của Supabase.
3. Không cần tạo bảng: backend tự tạo bảng khi khởi động lần đầu.

### Bước 2. Đưa code lên GitHub
1. Tạo repository mới trên GitHub (ví dụ `algo-arena`).
2. Giải nén file zip rồi đẩy code lên:
   ```bash
   cd algoarena
   git init && git add . && git commit -m "Algo Arena"
   git branch -M main
   git remote add origin https://github.com/<tai-khoan>/algo-arena.git
   git push -u origin main
   ```
   Thư mục `game/build/web` (bản build sẵn) cũng được đẩy lên. Nếu build trên Render lỗi, server vẫn chạy được bằng bản này.

### Bước 3. Tạo web service trên Render
1. Vào https://render.com, đăng nhập bằng GitHub, chọn **New → Blueprint** rồi chọn repo `algo-arena`. Render tự đọc file `render.yaml`.
2. Render hỏi giá trị cho các biến:
   - `DATABASE_URL`: chuỗi Session pooler ở bước 1
   - `ADMIN_PASSWORD`: mật khẩu cho tài khoản quản trị
3. Bấm **Apply**. Build mất khoảng 3–5 phút. Khi xong, bạn có URL dạng `https://algo-arena-xxxx.onrender.com`.
   (Nếu không dùng Blueprint: chọn **New → Web Service**, Build Command và Start Command lấy từ `render.yaml`, rồi tự thêm các biến môi trường `PYTHON_VERSION=3.12.7`, `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD`.)

### Bước 4. Kiểm tra
- `https://<url>/healthz` trả về `{"ok": true, "game_built": true}`
- `https://<url>/` hiện portal. Đăng ký tài khoản rồi bấm **Vào game**.
- `https://<url>/admin`: đăng nhập `admin` để vào trang quản trị.
- `https://<url>/docs`: tài liệu API tự sinh (Swagger), dùng để demo cho hội đồng.

> Gói free của Render tự "ngủ" sau 15 phút không có truy cập. Lần mở đầu tiên sau đó mất khoảng 50 giây. **Trước giờ bảo vệ khoảng 5 phút, hãy mở URL một lần** cho server thức dậy và game được trình duyệt cache.

## Phân quyền

| Vai trò | Quyền |
|---|---|
| Khách (offline) | Chơi thử, không lưu tiến trình |
| `player` | Chơi, lưu deck, lưu trận, replay, bảng xếp hạng, mở khoá thẻ |
| `admin` | Thêm: trang `/admin` (khoá/mở khoá, đổi vai trò, đặt lại mật khẩu, xoá user), thống kê, cân bằng thẻ |

## API chính

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/api/auth/register`, `/api/auth/login` | Trả JWT |
| GET | `/api/me` | Hồ sơ, cấp độ, thẻ đã mở, deck đang dùng |
| GET/POST/PUT/DELETE | `/api/decks[/{id}]` | Quản lý bộ bài (server kiểm tra thẻ đã mở khoá) |
| POST | `/api/matches` | Gửi seed + chuỗi hành động; **server chạy lại engine để xác minh** rồi mới cộng điểm |
| GET | `/api/matches/mine`, `/api/matches/{id}` | Lịch sử, dữ liệu replay |
| POST | `/api/puzzles/{id}/complete` | Xác minh lời giải rồi mở khoá thẻ |
| GET | `/api/leaderboard` | Bảng xếp hạng |
| POST | `/api/events` | Analytics |
| GET/PATCH/DELETE | `/api/admin/users[/{id}]` | Quản lý user (admin) |
| GET | `/api/admin/stats` | Thống kê, cân bằng thẻ, bài toán |
