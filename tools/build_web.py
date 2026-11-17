"""Build game sang WebAssembly bằng pygbag rồi chỉnh nhẹ trang index (nền tối, tiêu đề)."""
import pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB = ROOT / "game" / "build" / "web"
r = subprocess.run([sys.executable, "-m", "pygbag", "--build", "--title", "Algo Arena", str(ROOT / "game")])
if r.returncode != 0 or not (WEB / "index.html").exists():
    print("pygbag build thất bại", file=sys.stderr)
    sys.exit(1)
idx = WEB / "index.html"
html = idx.read_text(encoding="utf-8")
STYLE = "<style>html,body{background:#0d1220 !important}</style>"
if STYLE not in html:
    html = html.replace("</body>", STYLE + "\n</body>") if "</body>" in html else html + STYLE
    idx.write_text(html, encoding="utf-8")
print("OK:", WEB)
