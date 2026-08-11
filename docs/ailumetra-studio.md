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

## Local security boundary

- The CLI accepts loopback hosts only: `127.0.0.1`, `localhost`, or `::1`.
- Gradio public sharing is always disabled and event APIs are private.
- Monitoring and telemetry analytics are disabled.
- Uploads are limited to supported media types; images are capped at 25 MiB,
  videos and the server upload boundary at 50 MiB.
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
work. No third-party frontend template, font file, or asset is vendored.

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
