# Ailumetra Studio

Ailumetra Studio is the optional local interface for OpenMultimodalLab. It is
designed for a clear three-step workflow: open one media input, run one real
vision-language model, and inspect the response and runtime signals. The
existing `oml run` and `oml report` commands remain the reproducible benchmark
interface and source of durable evidence.

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

- **Overview** presents the already preserved v1.0.0 evidence. It does not
  rerun a model or silently replace the published result.
- **Playground** accepts exactly one image, document screenshot, or short
  video. The response and runtime metrics are useful for exploration, but the
  inference is explicitly unscored and is not a formal benchmark.
- **Reports** opens a bounded JSONL record produced by `oml run`, derives the
  summary with the existing reporter, and never rewrites the source file.

Only one queued model call runs at a time. When the backend changes, the old
adapter is released before the next model loads, which keeps the interface
practical on the verified 8 GB GPU profile.

### Playground generation controls

- **Max new tokens** is a hard output-length allowance, not a quality setting.
  Studio defaults to 512, permits up to 1,024, and shows an amber warning when
  the model consumes the entire allowance because the last sentence may be
  incomplete. Lower values can be useful for deliberately brief or faster
  experiments.
- **Timeout** covers media preprocessing, the first model load, and generation.
  Studio defaults to 300 seconds. Reducing it does not ask the model for a
  shorter answer; it makes a timeout failure more likely, especially on a cold
  first run.

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
- Media previews preserve the source aspect ratio, use letterboxing rather
  than cropping, and stop growing at a bounded desktop or mobile height.
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

The Ailumetra logo is an original, text-only sans-serif wordmark. All brand
layout CSS, copy, and interactions in this repository are original project
work. No third-party frontend template or artwork is copied.

### Locked typography system

Instrument Sans is the fixed Ailumetra brand and interface family. The
repository self-hosts the upstream variable WOFF2 file at commit
`7fa22308a3d0c94ee2b3cd537a1196b65db34a3e`, verifies its SHA-256 as
`aa72922aafcc0dc18f36ec1d805b0212057dabe8b9d5b8b57f67035aea1b826d`, and
packages the complete SIL Open Font License 1.1 notice. Studio never downloads
a font at runtime.

The interface enables Instrument Sans stylistic set 02 so lowercase `a` uses
one consistent single-storey construction. Headings, body copy, controls, and
evidence figures share the same family; evidence figures use tabular numerals,
while only literal code and local paths retain an explicit monospace face. The
wordmark visually capitalizes the existing `Ai` characters as a compact `AI`
accent without changing the accessible or public name `Ailumetra`. Its
light-blue-to-blue gradient and optically tightened join to `lumetra` are
shared by the Studio header and portable README artwork. Chinese text follows
the embedded Latin face with professional platform CJK fallbacks.
The README wordmark stores the same selected glyphs as SVG outlines, so its
appearance remains identical on GitHub without requiring a local font install.

This font family, upstream revision, feature set, and wordmark construction are
now a stable design contract. They should change only for a demonstrated
accessibility, licensing, or rendering defect and after an explicit brand
decision plus desktop and mobile visual regression review.

The interface palette uses white surfaces, dark ink, and a cobalt-led accent.
The hero emphasis and primary action both begin in blue and move through
indigo toward violet. The `AI` wordmark accent uses a separate
light-blue-to-blue gradient; cards, status indicators, evidence figures, and
the page background remain solid. Green is not part of the Studio brand
palette.

## 中文说明

Ailumetra Studio 是 OpenMultimodalLab 的可选本地界面，不替代可复现的
`oml run` / `oml report` 流程。Overview 展示已经保存的 v1.0.0 证据；
Playground 用于单张图片、文档截图或短视频的无评分体验；Reports 只读打开
已有 JSONL 结果。单次 Playground 结果不能当作正式模型排名。

界面只能监听本机回环地址，关闭公开分享、监控和分析，并将 GPU 推理并发限制
为 1。切换模型时会释放上一个模型，以适配已验证的 8 GB 消费级 GPU。公开
演示时建议录制屏幕，不要把本地端口通过隧道暴露到互联网。

## Compatibility promise

`Ailumetra` is the public-facing brand and `Ailumetra Studio` is the interface
name. The repository remains `OpenMultimodalLab`, the Python distribution
remains `openmultimodal-lab`, and the CLI remains `oml`; existing commands and
v1.0.0 evidence paths are intentionally unchanged.
