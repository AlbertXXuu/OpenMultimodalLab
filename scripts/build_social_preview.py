"""Build the deterministic 1280x640 AlvenX social preview image."""

from __future__ import annotations

import argparse
import base64
import html
import shutil
import subprocess
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FONT_PATH = (
    PROJECT_ROOT
    / "src"
    / "openmultimodal_lab"
    / "assets"
    / "fonts"
    / "InstrumentSans-wdth-wght.woff2.b64"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "docs" / "assets" / "alvenx-social-preview.png"
LOCKUP_PATH = PROJECT_ROOT / "docs" / "assets" / "alvenx-lockup.svg"
CANVAS_SIZE = (1280, 640)


def _browser_candidates() -> list[Path]:
    candidates: list[Path] = []
    for command in ("msedge", "microsoft-edge", "google-chrome", "chromium"):
        resolved = shutil.which(command)
        if resolved:
            candidates.append(Path(resolved))

    program_files = (
        Path.home().drive + "\\Program Files",
        Path.home().drive + "\\Program Files (x86)",
    )
    local_app_data = Path.home() / "AppData" / "Local"
    candidates.extend(
        [
            Path(program_files[0]) / "Microsoft/Edge/Application/msedge.exe",
            Path(program_files[1]) / "Microsoft/Edge/Application/msedge.exe",
            local_app_data / "Microsoft/Edge/Application/msedge.exe",
            Path(program_files[0]) / "Google/Chrome/Application/chrome.exe",
            Path(program_files[1]) / "Google/Chrome/Application/chrome.exe",
        ]
    )
    return candidates


def _find_browser(explicit: Path | None) -> Path:
    if explicit is not None:
        browser = explicit.expanduser().resolve()
        if not browser.is_file():
            raise SystemExit(f"Browser executable does not exist: {browser}")
        return browser
    for candidate in _browser_candidates():
        if candidate.is_file():
            return candidate.resolve()
    raise SystemExit(
        "Microsoft Edge, Google Chrome, or Chromium is required to rebuild "
        "the social preview. Pass its executable with --browser."
    )


def _preview_html() -> str:
    font_base64 = "".join(FONT_PATH.read_text(encoding="ascii").split())
    wordmark_base64 = base64.b64encode(LOCKUP_PATH.read_bytes()).decode("ascii")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=1280,initial-scale=1">
<style>
@font-face {{
  font-family: "Instrument Sans";
  src: url("data:font/woff2;base64,{font_base64}") format("woff2");
  font-weight: 400 700;
  font-stretch: 75% 100%;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; width: 1280px; height: 640px; overflow: hidden; }}
body {{
  font-family: "Instrument Sans", sans-serif;
  font-feature-settings: "ss01" 1, "ss02" 1;
  color: #0f172a;
  background:
    radial-gradient(circle at 91% 5%, rgba(96,165,250,.24), transparent 31%),
    radial-gradient(circle at 91% 94%, rgba(124,58,237,.13), transparent 28%),
    #f8fbff;
}}
.canvas {{
  position: absolute; inset: 34px; overflow: hidden;
  border: 2px solid #dbeafe; border-radius: 34px; background: #fff;
}}
.brand {{
  position: absolute; top: 21px; left: 48px; width: 430px; height: 150px;
}}
.brand img {{ display: block; width: 430px; height: 150px; }}
.eyebrow {{
  position: absolute; left: 50px; top: 171px; color: #2563eb;
  font-size: 17px; font-weight: 650; letter-spacing: .08em;
}}
h1 {{
  position: absolute; left: 46px; top: 196px; margin: 0;
  font-size: 59px; line-height: 1.08; font-weight: 650;
  font-stretch: 92%; letter-spacing: -.045em;
}}
h1 span {{
  color: transparent; background: linear-gradient(115deg,#2563eb,#7c3aed);
  background-clip: text; -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}}
.summary {{
  position: absolute; left: 50px; top: 353px; width: 725px; margin: 0;
  color: #475569; font-size: 23px; line-height: 1.42; font-weight: 430;
}}
.metrics {{ position: absolute; left: 50px; bottom: 34px; display: flex; gap: 22px; }}
.metric {{
  width: 213px; height: 70px; padding: 9px 17px;
  border: 1px solid #e2e8f0; border-radius: 18px; background: #f8fafc;
}}
.metric strong {{ display: block; font-size: 23px; line-height: 1.1; font-weight: 650; }}
.metric span {{ color: #64748b; font-size: 15px; line-height: 1.5; }}
.run-card {{
  position: absolute; left: 815px; top: 156px; width: 350px; height: 340px;
  padding: 28px 30px; border: 2px solid #bfdbfe; border-radius: 28px;
  background: linear-gradient(145deg,#f8fbff,#fff);
}}
.run-kicker {{ color: #2563eb; font-size: 17px; font-weight: 650; letter-spacing: .08em; }}
.run-model {{ margin: 23px 0 25px; font-size: 30px; font-weight: 650; letter-spacing: -.025em; }}
.row {{
  display: flex; justify-content: space-between; align-items: baseline;
  height: 44px; padding: 0 0 8px; margin-bottom: 8px;
  border-bottom: 1px solid #dbeafe;
}}
.row span {{ color: #64748b; font-size: 15px; }}
.row strong {{ font-size: 19px; font-weight: 650; font-variant-numeric: tabular-nums; }}
.verified {{
  position: absolute; left: 30px; right: 30px; bottom: 14px; height: 28px;
  border-radius: 14px; background: #dbeafe; color: #1d4ed8;
  font-size: 15px; font-weight: 550; line-height: 28px; text-align: center;
}}
.verified::before {{ content: ""; display: inline-block; width: 9px; height: 9px;
  margin-right: 9px; border-radius: 50%; background: #2563eb; }}
</style>
</head>
<body>
  <main class="canvas" aria-label="AlvenX social preview">
    <div class="brand"><img src="data:image/svg+xml;base64,{wordmark_base64}" alt="AlvenX — Multimodal Evidence"></div>
    <div class="eyebrow">LOCAL-FIRST · REPRODUCIBLE · OPEN SOURCE</div>
    <h1>Local multimodal evidence,<br><span>on hardware you own.</span></h1>
    <p class="summary">Compare real vision-language models and rebuild every result<br>
      from preserved task-level records — without rerunning inference.</p>
    <div class="metrics">
      <div class="metric"><strong>102</strong><span>human-checked tasks</span></div>
      <div class="metric"><strong>2</strong><span>real open models</span></div>
      <div class="metric"><strong>612</strong><span>measured attempts</span></div>
    </div>
    <aside class="run-card">
      <div class="run-kicker">FORMAL RUN</div>
      <div class="run-model">Qwen3-VL-2B</div>
      <div class="row"><span>Mean score</span><strong>0.784</strong></div>
      <div class="row"><span>Median TTFT</span><strong>120.5 ms</strong></div>
      <div class="row"><span>Peak GPU memory</span><strong>4,180.5 MiB</strong></div>
      <div class="verified">Evidence preserved</div>
    </aside>
  </main>
</body>
</html>"""


def build_preview(output: Path, *, browser: Path | None = None) -> None:
    executable = _find_browser(browser)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="alvenx-social-preview-") as temp_dir:
        source = Path(temp_dir) / "preview.html"
        source.write_text(_preview_html(), encoding="utf-8")
        command = [
            str(executable),
            "--headless=new",
            "--disable-gpu",
            "--enable-unsafe-swiftshader",
            "--no-sandbox",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            f"--window-size={CANVAS_SIZE[0]},{CANVAS_SIZE[1]}",
            f"--screenshot={output}",
            source.as_uri(),
        ]
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
        )
        if completed.returncode != 0 or not output.is_file():
            detail = html.escape((completed.stderr or completed.stdout).strip())
            raise SystemExit(f"Browser screenshot failed: {detail}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--browser", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    build_preview(output, browser=args.browser)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
