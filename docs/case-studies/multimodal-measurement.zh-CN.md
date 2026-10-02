# 在可复核的测量边界下比较两个本地多模态模型

2026-10-02 · OpenMultimodalLab

[English](multimodal-measurement.md) · [网站阅读版](https://alvenx.com/notes/engineering/multimodal-measurement-zh)

OpenMultimodalLab 保存了两个固定模型在 102 个任务上的 612 次正式测量。这个案例的工程价值在于，把任务质量、计算计时、内存、断点恢复和证据来源分别定义清楚，让比较结果能够复核。

## 模型比较需要完整的实验定义

一个分数无法说明它来自哪些输入、解码条件和硬件。预处理、首 token 计算与完整任务完成若混在一起，时间指标的含义也会变化。OpenMultimodalLab 用版本化任务、明确的指标定义和保存的逐次记录解决这个问题，让读者能追溯图表背后的实验。

v1.0.0 正式证据覆盖图像、文档、短视频和鲁棒性数据集中的 102 个不重复、经人工检查的合成任务。Qwen3-VL-2B-Instruct 与 SmolVLM2-500M-Video-Instruct 各完成三次正式重复，即每个后端 306 次，总计 612 次。每个后端先完成一次成功 warm-up，其记录单独保存，并从正式汇总中排除。

[冻结的正式报告](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/docs/reports/v1.0.0-candidate/report.md)

## 固定输入并分开记录质量与执行结果

两个后端在同一块 NVIDIA RTX 4060 Laptop GPU 上运行，可见容量为 8,188 MiB，batch size 为 1，采用贪心解码，测量期间没有重试或模型重新加载。模型修订固定为：Qwen 的 89644892e4d85e24eaac8bacfd4f463576704203，以及 SmolVLM2 的 7b375e1b73b11138ff12fe22c8f2822d8fe03467。

一次尝试成功表示推理和评估完成，不表示回答完全正确。因此报告分别给出运行失败与确定性任务得分。这个正式网格中，两者均没有运行失败，平均任务得分分别为 0.784 和 0.690。分类结果继续保留，因为总分可能掩盖不同任务上的表现差异。

| 固定后端 | 正式测量次数 | 平均任务得分 | 任务延迟中位数 | 峰值 GPU 已分配内存 |
| --- | --- | --- | --- | --- |
| Qwen3-VL-2B | 306 | 0.784 | 212.9 ms | 4,180.5 MiB |
| SmolVLM2-500M | 306 | 0.690 | 471.5 ms | 1,265.3 MiB |

[协议与指标定义](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/docs/evaluation-protocol.md) · [已发布结果与延迟表](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/README.md)

## 以可观察边界定义计时与内存

Transformers 适配器在生成开始前及首个生成 token 的 logits 可用时同步 CUDA。TTFT 测量这个本地计算区间，Qwen 与 SmolVLM2 的中位数分别为 120.5 ms 和 260.0 ms。任务延迟覆盖适配器调用及确定性评估，还包含生成之外的工作，所以二者使用不同的时间边界。

内存指标来自重置峰值统计后、生成期间的 torch.cuda.max_memory_allocated。它表示 PyTorch 分配的 CUDA 内存，不是进程全部显存或整块设备的峰值。吞吐率使用各模型原生 tokenizer 的 token ID 数量；不同 tokenizer 下，跨模型家族的 tokens/s 排名通常不如质量、延迟和失败结果直接。

[计时与内存分配实现](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/src/openmultimodal_lab/adapters/transformers_image_text.py) · [测量边界](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/docs/evaluation-protocol.md)

## 恢复与报告必须保持同一个实验

每条 JSONL 记录先 flush 并同步落盘，再原子更新 manifest，记录条数、字节数和 SHA-256。严格 resume 核对数据集与媒体哈希、任务顺序、模型修订、生成配置、环境，以及 phase 和 repetition 计划的精确前缀。配置变化、末尾记录截断或 manifest 不匹配都会被拒绝，恢复过程不会猜测哪些行应当保留。

报告生成器在汇总前检查完整网格、干净的源代码提交、模型身份、输入哈希和 JSONL sidecar。报告包绑定输出及生成器哈希，可直接从保存的结果重建，无需再调用模型。结果文件名使用 8 月 10 日，manifest 则单独保留实际 UTC 执行时间；本文于 10 月 2 日发布，并不代表重新运行了基准。

[持久记录与严格恢复](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/docs/run-records-and-manifests.md) · [报告来源与网格校验](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/src/openmultimodal_lab/report_bundle.py) · [Qwen 源 manifest](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/docs/reports/results/2026-08-10-qwen3-vl-v1.0.0-formal.manifest.json) · [SmolVLM2 源 manifest](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/docs/reports/results/2026-08-10-smolvlm2-v1.0.0-formal.manifest.json)

## 有边界且证据可检查的比较

这些测量只适用于保存的合成任务集、固定模型、记录的机器与解码设置。三次重复增加了本实验的可观察性，但不能建立通用模型排名或生产质量结论。SHA-256 在 manifest 可信时检测不一致；面对能够同时重写两份材料的人，它不具备数字签名的保证。

LMMs-Eval 是复用多模态任务与模型评估的一手参考。这里更具体的工程结果，是通过声明测量边界、严格恢复和报告重建，让一个小规模本地比较可以检查；文中的数字由 OpenMultimodalLab 保存的原始记录支持。

[LMMs-Eval 一手仓库](https://github.com/EvolvingLMMs-Lab/lmms-eval)

## 原始证据

- [正式基准报告](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/docs/reports/v1.0.0-candidate/report.md)
- [测量协议](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/docs/evaluation-protocol.md)
- [记录与恢复合同](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/docs/run-records-and-manifests.md)
- [确定性报告生成器](https://github.com/AlbertXXuu/OpenMultimodalLab/blob/d56e339936a03a683b8aa0eac54063c436c3ad7d/src/openmultimodal_lab/report_bundle.py)
