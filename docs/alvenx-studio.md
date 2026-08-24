# AlvenX Studio

AlvenX Studio is the optional local interface for OpenMultimodalLab. Its Run
workflow makes four boundaries explicit: select one source, pin one local
model, define the prompt and generation limits, then inspect the response next
to its runtime evidence. The existing `oml run` and `oml report` commands
remain the reproducible benchmark interface and source of durable evidence.

## Install on Windows

Use the Python 3.11 or 3.12 model environment documented for the selected
backend. If that environment already works, add only the Studio extra:

```powershell
.\.venv-ml\Scripts\python.exe -m pip install -e ".[studio]"
.\.venv-ml\Scripts\oml.exe studio
```

For a new Qwen3-VL environment, install the backend and Studio together after
installing the appropriate CUDA-enabled PyTorch build:

```powershell
.\.venv-ml\Scripts\python.exe -m pip install -e ".[qwen3-vl,studio]"
.\.venv-ml\Scripts\oml.exe doctor --backend qwen3-vl
.\.venv-ml\Scripts\oml.exe studio
```

The browser opens at `http://127.0.0.1:7860`. Use `--no-browser` to start it
without opening a tab, or `--port 8765` to choose another local port.

## What each tab means

- **Run** is the default workbench. It keeps one image, document screenshot, or
  short video together with local-model selection, prompt and bounded
  generation controls, response, status, and runtime metrics. Its inference is
  explicitly unscored and is not a formal benchmark.
- **Reports** opens a bounded JSONL record produced by `oml run`, derives the
  summary with the existing reporter, and never rewrites the source file.
- **Method** explains the preserved v1 scope and why task control, measurement,
  and interpretation remain separate. It does not rerun a model or replace a
  published result.

The source comes first, followed by backend, prompt, generation controls, and
the Run/Clear actions. The selected backend applies to the next run; Qwen3-VL
remains the default.

Only one queued model call runs at a time. When the backend changes, the old
adapter is released before the next model loads, which keeps the interface
practical on the verified 8 GB GPU profile.

The Run view starts with a compact four-step map and a visible local-only
boundary, followed by two coordinated panels: **Prepare the experiment** and
**Read result and runtime together**. A panel note and the run status
distinguish a **cold start** from **warm reuse**.
The first request loads the selected model and can take substantially
longer; after a successful request, Studio confirms that the model remains
warm for the next run. Clearing media, prompt, and output does not unload that
model. The wordmark is a static identity element: it is not a button and has no
hidden click interaction. The glass header, segmented navigation, media
selector, panels, and controls follow a nested radius system. Media and
response surfaces use bounded heights with aspect-safe previews, scrolling
text, and full-screen media controls. Narrow layouts return to natural document
scrolling and do not introduce horizontal overflow.

### Run generation controls

- **Max new tokens** is a hard output-length allowance, not a quality setting.
  Studio defaults to 512, permits up to 1,024, and shows an amber warning when
  the model consumes the entire allowance because the last sentence may be
  incomplete. Lower values can be useful for deliberately brief or faster
  experiments.
- **Timeout** covers media preprocessing, the first model load, and generation.
  Studio defaults to 300 seconds. Reducing it does not ask the model for a
  shorter answer; it makes a timeout failure more likely, especially on a cold
  first run.
- **Clear** removes both media inputs (including a file retained in the hidden
  image/video tab), the current prompt, response, metrics, and status. It does
  not unload the active model, so the next run can still use the warm model.
  If Run is pressed while the cleared prompt is blank, Studio restores and uses
  `Describe the important visual content and any motion.` automatically.

## Local security boundary

- The CLI accepts loopback hosts only: `127.0.0.1`, `localhost`, or `::1`.
- Gradio public sharing is always disabled and event APIs are private.
- Monitoring and telemetry analytics are disabled.
- Uploads are limited to supported media types; images are capped at 25 MiB,
  videos and the server upload boundary at 50 MiB. Videos must also remain at
  or below 60 seconds, 3,600 source frames, and 3840×2160 pixels per frame.
- Studio preserves the uploaded video instead of requiring a system FFmpeg
  executable to remove its audio track; model adapters consume the sampled
  visual frames. H.264 MP4 is the most portable browser-preview format, while
  H.265/HEVC preview support depends on the browser and operating system. After
  upload, Studio reports the codec and explains that an audio-only or frozen
  HEVC preview does not mean local model decoding failed.
- Media previews adapt to the source aspect ratio, use letterboxing rather than
  cropping, and stop growing at a bounded desktop or mobile height.
- User-facing exceptions redact common absolute local paths.
- The Studio has no delete, overwrite, publication, or GitHub action.

Do not expose the local port with a reverse proxy or tunnel. Treat uploaded
media and model output according to the selected model's terms and your own
privacy requirements.

## Design rationale and prior art

The interface adopts established product patterns rather than copying another
project's code or assets:

- [LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory) demonstrates that a
  capable CLI and an approachable local Web UI can coexist.
- [FiftyOne](https://github.com/voxel51/fiftyone) makes media inspection a
  first-class workflow rather than hiding inputs behind configuration.
- [Arize Phoenix](https://github.com/Arize-ai/phoenix) separates interactive
  exploration from durable datasets, experiments, and evaluation evidence.
- [Evidently](https://github.com/evidentlyai/evidently) favors readable metric
  cards with explicit pass/fail context.
- [Gradio Blocks](https://www.gradio.app/docs/gradio/blocks) supplies the local
  application shell, queueing, accessible components, and bounded file flow.

The AlvenX logo is an original, outline-based sans-serif wordmark. All brand
layout CSS, copy, and interactions in this repository are original project
work. No third-party frontend template or artwork is copied.

### Locked typography system

Instrument Sans is the fixed AlvenX brand and interface family. The
repository self-hosts the upstream variable WOFF2 file at commit
`7fa22308a3d0c94ee2b3cd537a1196b65db34a3e`, verifies its SHA-256 as
`aa72922aafcc0dc18f36ec1d805b0212057dabe8b9d5b8b57f67035aea1b826d`, and
packages the complete SIL Open Font License 1.1 notice. Studio never downloads
a font at runtime.

The interface enables Instrument Sans stylistic set 02 so lowercase `a` uses
one consistent single-storey construction. Headings, body copy, controls, and
evidence figures share the same family; evidence figures use tabular numerals,
while only literal code and local paths retain an explicit monospace face. The
wordmark keeps the accessible and public name `AlvenX` while using the
owner-approved connected `Al`, `l–v`, `e–n`, and `n–X` outline relationships;
`v–e` remains physically separate. Its continuous blue-to-indigo-to-violet
`Al` gradient is shared by the Studio header and portable README artwork. The Studio embeds the
same outlined SVG bytes used by the README, verifies them against SHA-256
`f6d2ed3ca53b65a274235b8d563fc3eb248199baf82f1496f7e8aac38c37c8d2`,
and does not reconstruct `Al` and `venX` with browser letter spacing.
Chinese text follows the embedded Latin face with professional platform CJK
fallbacks. Because the wordmark stores glyphs as SVG outlines, it remains
identical on GitHub and in Studio without requiring a local font install.

This font family, upstream revision, feature set, and wordmark construction are
now a stable design contract. They should change only for a demonstrated
accessibility, licensing, or rendering defect and after an explicit brand
decision plus desktop and mobile visual regression review.

The interface implements AlvenX interface revision `2026-08-25.1`. This OML
canvas is the locked common background for the OML, BrowserAgentRegression,
and PhysGauge studios. From back to front it is:

- a blue radial field at `12% 5%`, `42%` alpha, fading by `34%`;
- a violet radial field at `84% 7%`, `28%` alpha, fading by `36%`;
- an indigo radial field at `68% 88%`, `14%` alpha, fading by `38%`;
- `linear-gradient(145deg, #FBFDFF 0%, #F1F7FF 49%, #E7F1FF 100%)`.

All four layers use fixed attachment. The studios deliberately do not inherit
the website's animated ambient fields: a long-running evidence tool should not
add continuous background motion or GPU work.

Instrument Sans, dark `#0B1731` primary ink, `#334155` reading ink, and the
canonical `#2563EB → #4F46E5 → #7C3AED` accent remain shared. Primary run and
report actions use the same restrained liquid-glass construction as the
website: translucent background-reactive fill, one optical outer edge, a
softer inset top highlight, `24px` backdrop blur, continuous pill curvature,
small hover lift, active compression, and an independent focus ring. The two
edge tones represent the physical boundary and inner refraction rather than
two equally strong borders. Dense evidence tables and reading surfaces remain
quiet and mostly opaque. Green is not part of the Studio brand palette.

## 中文说明

AlvenX Studio 是 OpenMultimodalLab 的可选本地界面，不替代可复现的
`oml run` / `oml report` 流程。默认 Run 按“Source → Model → Prompt → Evidence”
组织媒体、模型、Prompt、回答和实时指标；Reports 只读打开已有 JSONL 结果；
Method 说明 v1 测量边界。单次 Run 结果不能当作正式模型排名。

Run 页先显示紧凑的四步引导和“仅本机”边界，再显示“准备实验”和“证据控制台”
两张工作卡片。卡片说明与运行状态会明确区分冷启动与热复用：第一次请求需要加载模型，成功后模型会
留在显存中供下一次请求复用；Clear 只清空媒体、Prompt、回答和指标，不卸载
模型；清空后在 Prompt 为空时点击 Run，会自动恢复默认视觉描述 Prompt。模型
选择位于媒体之后，所选后端用于下一次运行。顶部 AlvenX 标志只作为静态品牌
元素，不可点击、没有隐藏彩蛋。玻璃标题栏、分段导航、媒体控件和工作卡片采用
统一的嵌套圆角层级；窄屏恢复自然页面滚动且不产生横向溢出。媒体仍按原始比例
完整显示，长回答在框内滚动。

界面只能监听本机回环地址，关闭公开分享、监控和分析，并将 GPU 推理并发限制
为 1。切换模型时会释放上一个模型，以适配已验证的 8 GB 消费级 GPU。公开
演示时建议录制屏幕，不要把本地端口通过隧道暴露到互联网。

## Compatibility promise

`AlvenX` is the shared series identity and `AlvenX Studio` is this
project's interface name. The repository remains `OpenMultimodalLab`, the
Python distribution remains `openmultimodal-lab`, and the CLI remains `oml`; existing commands and
v1.0.0 evidence paths are intentionally unchanged.
