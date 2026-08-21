# AlvenX Studio

AlvenX Studio is the optional local interface for OpenMultimodalLab. It is
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

- **Workspace** is the default view. It keeps model selection, one image,
  document screenshot, or short video, the prompt, optional generation
  controls, model response, and runtime metrics in one input-to-output surface.
  Its inference is explicitly unscored and is not a formal benchmark.
- **Reports** opens a bounded JSONL record produced by `oml run`, derives the
  summary with the existing reporter, and never rewrites the source file.
- **About** presents the already preserved v1.0.0 evidence after the functional
  surfaces. It does not rerun a model or replace the published result.

The backend selector sits below the primary Run/Clear actions so media and
prompt work remain the first visual focus. The selected backend still applies
to the next run; Qwen3-VL remains the default.

Only one queued model call runs at a time. When the backend changes, the old
adapter is released before the next model loads, which keeps the interface
practical on the verified 8 GB GPU profile.

The Workspace opens directly into its Input and Output cards instead of
repeating a marketing title and four-step guide. A compact note inside the
Input card and the run status distinguish a **cold start** from **warm reuse**.
The first request loads the selected model and can take substantially
longer; after a successful request, Studio confirms that the model remains
warm for the next run. Clearing media, prompt, and output does not unload that
model. The unboxed brand row removes decorative framing above the Workspace;
the primary navigation has no redundant divider, while its selected state,
media selector, cards, and controls use a nested radius system. Media and response
surfaces use compact, bounded default heights with aspect-safe previews,
scrolling text, and full-screen media controls so the two working panels enter
the initial laptop viewport without discarding content. On desktop, both cards
stay equal-height and fully bounded in the viewport while their longer contents
scroll independently; narrower layouts return to normal document scrolling.

### Workspace generation controls

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

The AlvenX logo is an original, text-only sans-serif wordmark. All brand
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
wordmark visually capitalizes the existing `Ai` characters as a compact `AI`
accent without changing the accessible or public name `AlvenX`. Its
light-blue-to-blue gradient and optically tightened join to `venX` are
shared by the Studio header and portable README artwork. The Studio embeds the
same outlined SVG bytes used by the README, verifies them against SHA-256
`9807f882dc58a9ac7c03ccba8ec8884503e8d1d6aa42525b969200cb14c6368e`,
and does not reconstruct `Al` and `venX` with browser letter spacing.
Chinese text follows the embedded Latin face with professional platform CJK
fallbacks. Because the wordmark stores glyphs as SVG outlines, it remains
identical on GitHub and in Studio without requiring a local font install.

This font family, upstream revision, feature set, and wordmark construction are
now a stable design contract. They should change only for a demonstrated
accessibility, licensing, or rendering defect and after an explicit brand
decision plus desktop and mobile visual regression review.

The interface palette uses white surfaces, dark ink, and a cobalt-led accent.
The hero emphasis and primary action both begin in blue and move through
indigo toward violet. The `Al` wordmark accent uses a separate
light-blue-to-blue gradient; cards, status indicators, evidence figures, and
the page background remain solid. Green is not part of the Studio brand
palette.

## 中文说明

AlvenX Studio 是 OpenMultimodalLab 的可选本地界面，不替代可复现的
`oml run` / `oml report` 流程。默认 Workspace 把模型、媒体、Prompt、回答和
实时指标放在同一功能区；Reports 只读打开已有 JSONL 结果；About 后置展示
已经保存的 v1.0.0 证据。单次 Workspace 结果不能当作正式模型排名。

Workspace 在主导航后直接显示 Input/Output 卡片，不再重复宣传标题和四步提示。
Input 卡片内的简短说明与运行状态会明确区分冷启动与热复用：第一次请求需要加载模型，成功后模型会
留在显存中供下一次请求复用；Clear 只清空媒体、Prompt、回答和指标，不卸载
模型；清空后在 Prompt 为空时点击 Run，会自动恢复默认视觉描述 Prompt。模型
选择放在 Run/Clear 下方，所选后端仍用于下一次运行。顶部品牌行取消装饰性大
外框，主导航取消多余分隔线；选中状态、媒体分段
控件和工作卡片采用统一的嵌套圆角层级，并压缩默认媒体与回答区域高度，使常见
笔记本首屏能直接看到 Input/Output 工作区；
桌面端两张卡片等高且外框完整留在视口内，较长内容在卡片内部滚动；窄屏恢复
自然页面滚动。媒体仍按原始比例完整显示，长回答则在框内滚动。

界面只能监听本机回环地址，关闭公开分享、监控和分析，并将 GPU 推理并发限制
为 1。切换模型时会释放上一个模型，以适配已验证的 8 GB 消费级 GPU。公开
演示时建议录制屏幕，不要把本地端口通过隧道暴露到互联网。

## Compatibility promise

`AlvenX` is the shared series identity and `AlvenX Studio` is this
project's interface name. The repository remains `OpenMultimodalLab`, the
Python distribution remains `openmultimodal-lab`, and the CLI remains `oml`; existing commands and
v1.0.0 evidence paths are intentionally unchanged.
