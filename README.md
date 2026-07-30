# OpenMultimodalLab

面向普通开发者的、本地优先的多模态模型评测与实验平台。

项目要解决的问题是：同一个图片、文档或视频任务，在不同视觉语言模型上究竟表现如何？它们的准确率、延迟、显存占用、失败方式和运行成本是否能被公平、可复现地比较？

> 当前阶段：`v0.2` 开发中。基础评测闭环已经接入第一个真实本地模型 Qwen3-VL-2B，并发布带结构化评分的 `synthetic-v1.1`。

## 你现在要做什么

1. 用 12 周完成一个可以公开发布的 `v1.0`。
2. 每周完成 2～3 个有证据的更新：功能、实验、文档或发布。
3. 优先完成评测核心，不在早期堆积模型、UI 和宣传功能。
4. 所有性能和准确率数字必须来自可复现的真实实验。

完整说明：

- [项目规划书](docs/00-project-plan.md)
- [目标与验收标准](docs/01-goals-and-success.md)
- [范围与需求](docs/02-scope-and-requirements.md)
- [技术架构](docs/03-architecture.md)
- [评测协议](docs/evaluation-protocol.md)
- [Qwen3-VL 真实模型后端](docs/backends/qwen3-vl.md)
- [Qwen3-VL 第一份真实基线报告](docs/reports/2026-07-30-qwen3-vl-baseline.md)
- [synthetic-v1.1 与结构化评分报告](docs/reports/2026-07-31-synthetic-v1-1-structured-scoring.md)
- [12 周路线图](docs/04-roadmap.md)
- [每周工作方法](docs/05-weekly-workflow.md)
- [质量与开源标准](docs/06-quality-and-open-source.md)
- [学习路线](docs/07-learning-path.md)
- [风险、假设与决策](docs/08-risks-and-decisions.md)
- [当前任务清单](TASKS.md)

## 当前最小闭环

仓库包含一个不依赖大模型的 `mock` 后端，用来验证以下数据流：

```text
JSONL 任务集 -> 模型适配器 -> 推理记录 -> 自动评分 -> JSONL 结果 -> 汇总报告
```

`mock` 后端只用于测试基础设施，不能作为模型能力结果发布。

真实模型后端使用 `--backend qwen3-vl`。它固定模型 revision、延迟加载权重，并把模型加载失败和显存不足写入原始结果。安装与首次运行见 [Qwen3-VL 后端说明](docs/backends/qwen3-vl.md)。

## 快速开始

建议使用 Python 3.11 或 3.12。当前基础设施不依赖第三方运行时包，也可以在 Python 3.13 上执行。

```powershell
python -m pip install -e .
oml doctor
oml run --dataset examples/tasks/smoke.jsonl --output runs/smoke.jsonl
oml report --input runs/smoke.jsonl
python -m unittest discover -s tests -v
```

运行当前 10 条可复现图片任务：

```powershell
oml run `
  --dataset examples/tasks/synthetic-v1.1.jsonl `
  --output runs/synthetic-v1.1-mock.jsonl
```

`synthetic-v1` 作为已发布历史版本保持不变；`synthetic-v1.1` 修正了真实模型运行发现的标注问题，并为每条任务声明确定性评分规则。媒体由标准库脚本生成，可随时重新构建：

```powershell
python scripts/generate_synthetic_images.py
```

只运行某一类任务时使用 `--category`；该参数可以重复：

```powershell
oml run `
  --dataset examples/tasks/smoke.jsonl `
  --output runs/image-and-smoke.jsonl `
  --category image-description `
  --category smoke-test
```

不安装项目时，也可以临时设置源码路径：

```powershell
$env:PYTHONPATH = "src"
python -m openmultimodal_lab doctor
```

## 计划中的 v1.0 能力

- 至少 2 个真实开源视觉语言模型后端，以及 1 个测试后端。
- 图片、文档和短视频三类输入。
- 至少 100 条版本化评测任务。
- 准确率、首 token 延迟、生成速度、峰值显存和失败类型记录。
- 可从原始结果重建的对比报告。
- Windows/Linux 安装说明、自动测试和公开复现实验。

## 项目原则

- 先可复现，再追求更多模型。
- 先命令行和结构化结果，再做 Web UI。
- 失败也是数据，不丢弃超时、OOM 或格式错误样本。
- 不把调用模型 API 包装一下就称为完整项目。
- 不承诺 Star 数量，用真实可用性提高被使用和传播的概率。

## License

项目代码采用 Apache-2.0。正式公开模型和数据实验前，还需要逐项检查所用模型、数据集和媒体样例的许可证兼容性。
