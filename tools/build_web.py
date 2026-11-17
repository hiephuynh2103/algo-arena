"""Build game sang WebAssembly bằng pygbag rồi chỉnh nhẹ trang index (nền tối, tiêu đề)."""
import pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB = ROOT / "game" / "build" / "web"
(ROOT / "game" / "build" / "web").mkdir(parents=True, exist_ok=True)
(ROOT / "game" / "build" / "web-cache").mkdir(parents=True, exist_ok=True)
r = subprocess.run([sys.executable, "-m", "pygbag", "--build", "--title", "Algo Arena", str(ROOT / "game")])
if r.returncode != 0 or not (WEB / "index.html").exists():
    print("pygbag build thất bại", file=sys.stderr)
    sys.exit(1)
idx = WEB / "index.html"
html = idx.read_text(encoding="utf-8")
# Giữ đúng tỉ lệ 16:9 (không kéo giãn chữ), căn giữa, nền tối, scale mượt.
STYLE = """<style>
html,body{background:#080c1a !important;margin:0;overflow:hidden}
canvas#canvas{
  width:min(100vw, calc(100vh * 16 / 9)) !important;
  height:min(100vh, calc(100vw * 9 / 16)) !important;
  top:50% !important; left:50% !important; right:auto !important; bottom:auto !important;
  transform:translate(-50%,-50%) !important; margin:0 !important;
  image-rendering:auto; border-radius:0;
}
</style>"""
if STYLE not in html:
    html = html.replace("</body>", STYLE + "\n</body>") if "</body>" in html else html + STYLE
    idx.write_text(html, encoding="utf-8")
print("OK:", WEB)
