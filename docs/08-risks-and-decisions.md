# 风险、假设与决策

## 1. 当前事实

- 工作目录为 Windows。
- 当前系统默认 Python 是 3.13.5。
- GPU 为 NVIDIA GeForce RTX 4060 Laptop GPU，显存 8,188 MiB，驱动 596.49。
- D 盘验证时可用空间约 282.8 GB。
- 项目尚未确认每周准确时间。
- 现有工作区内已有 LocalModelLab 和 AgentReliabilityLab，本项目不覆盖它们。

## 2. 当前假设

- 每周可以稳定投入约 10 小时。
- 可以创建独立 Python 虚拟环境。
- 8GB 显存预计可以运行一个 2B 级别的视觉语言模型，但仍需用实际后端验证。
- 第一批公开媒体可以由项目自行生成或来自许可证清晰的数据。

假设需要在接入真实模型前通过 `doctor` 和硬件检查确认。

## 3. 主要风险

| 风险 | 影响 | 概率 | 应对 |
|---|---|---:|---|
| Python 3.13 与 ML 依赖不兼容 | 无法安装真实后端 | 高 | 正式模型环境使用 3.11/3.12 |
| 8GB 显存不足以运行候选配置 | 候选模型 OOM 或上下文过短 | 中 | 优先 2B～4B 小模型、量化、CPU 或远程可选后端 |
| 项目范围膨胀 | 12 周无法完成 | 高 | Must/Should/Could/Won't 管理范围 |
| 数据许可证不清 | 无法公开任务 | 中 | 自制媒体或使用许可明确数据 |
| 指标不公平 | 报告失去可信度 | 中 | 固定协议，公开配置和失败样本 |
| 过早做 UI | 核心评测不稳定 | 高 | v0.5 前 CLI 优先 |
| 周更变成刷提交 | 项目质量下降 | 中 | 使用 Definition of Done |
| 没有真实用户 | 难以验证易用性 | 中 | v0.8 邀请至少 5 位试用者 |

## 4. 已做决策

### D-001：建立独立仓库

选择 `OpenMultimodalLab`，不修改已有 LocalModelLab 和 AgentReliabilityLab。

原因：三者研究问题不同，独立仓库更容易形成清楚的 README、路线图和面试故事。

### D-002：先做评测核心

第一阶段使用确定性 `mock` 后端，不立即安装大型模型。

原因：先验证任务、Adapter、Runner、评分和报告的边界，可以让后续模型接入更可靠，也能让 CI 离线运行。

### D-003：CLI 优先

`v0.5` 前以 CLI + JSONL 为主要界面。

原因：UI 会增加前后端和部署成本，但不能替代可复现实验。

### D-004：正式支持 Python 3.11/3.12

基础代码兼容当前 3.13，但真实深度学习环境以 3.11/3.12 为目标。

原因：深度学习、量化和视频相关依赖通常需要更成熟的 Python 版本支持。

### D-005：第一个真实后端使用 Qwen3-VL-2B

默认模型选择 `Qwen/Qwen3-VL-2B-Instruct`，并固定 revision
`89644892e4d85e24eaac8bacfd4f463576704203`。

比较过的候选包括 SmolVLM2-2.2B、Gemma 3 4B、DeepSeek-VL2 和
Janus-Pro。Qwen3-VL-2B 的模型体积、Apache-2.0 许可、Transformers
原生支持、中文能力和空间/文档/视频扩展方向最符合第一后端要求。
Gemma 需要额外接受模型条款，DeepSeek-VL2 的原生显存要求不适合
当前 8GB GPU；Janus-Pro-1B 保留为第二后端候选。

### D-006：第二个真实后端使用 SmolVLM2-500M

编号与日期：D-006，2026-07-31。

问题：选择哪个不同模型家族来验证统一 Adapter 和公平比较协议。

可选方案：SmolVLM2-500M/2.2B、Janus-Pro-1B、DeepSeek-VL2-Tiny。

选择：`HuggingFaceTB/SmolVLM2-500M-Video-Instruct`，固定 revision
`7b375e1b73b11138ff12fe22c8f2822d8fe03467`。

理由：Apache-2.0、Transformers 原生支持，并且官方处理链同时覆盖图片和
视频，能为后续短视频任务复用。官方模型卡给出的 500M 视频推理显存约
1.8GB，更符合“普通消费级设备可复现”的项目目标。2.2B 的仓库权重约
8.6GB，在当前代理环境中首次下载成本过高，不适合作为默认快速开始模型。
Janus-Pro 更适合作为以后验证自定义运行时的第三后端；DeepSeek-VL2 的原生
资源要求不适合作为当前 8GB 设备上的低风险选择。

影响：Qwen3-VL 与 SmolVLM2 共用计时、错误分类和结果字段，但各自使用固定
的原生 processor 和 chat template。Qwen3-VL-2B 与 SmolVLM2-500M 的结果
用于分析质量、延迟和资源效率权衡，不能表述为同等参数规模下的纯架构对比。
跨模型 token/s 也必须附带 tokenizer 不可直接等价的限制说明。

何时重新评估：正式 GPU 冒烟出现无法解决的 OOM 或上游不兼容，或视频阶段
发现当前 Transformers 路径无法提供可审计的帧采样配置时。

一手资料：

- [SmolVLM2-500M-Video-Instruct model card](https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct)
- [DeepSeek Janus 官方仓库](https://github.com/deepseek-ai/Janus)
- [DeepSeek-VL2 官方仓库](https://github.com/deepseek-ai/DeepSeek-VL2)

### D-007：断点续跑采用严格前缀恢复

编号与日期：D-007，2026-07-31。

问题：如何在模型运行被中断后保留昂贵结果，同时避免重复记录或混合不同
实验配置。

可选方案：直接追加、按任务 ID 跳过、严格验证 manifest 与执行计划前缀。

选择：CLI 默认拒绝覆盖；`--resume` 只接受 `started` 或 `failed` manifest，
核对输入、模型、环境、协议、输出完整性，并要求已有记录是确定性执行计划的
严格前缀。只有显式 `--overwrite` 才允许替换结果。

理由：只按任务 ID 跳过无法区分 warm-up、重复轮次、模型 revision 或数据
变化，可能生成看似完整但不可解释的报告。严格恢复会更早暴露不一致，并让
每条保留记录仍属于同一个实验。

影响：恢复参数必须与原运行一致；完成的实验使用新输出路径；截断 JSONL 和
被修改的已哈希结果会被拒绝。每条记录同步到磁盘后，manifest 原子保存当前
记录数、字节数和 SHA-256，并记录后续恢复次数。

何时重新评估：加入并行执行或非固定任务调度后，前缀模型需要升级为带唯一
attempt ID 的集合式恢复协议。

### D-008：超时采用 Adapter 协作式截止，重试逐调用持久化

编号与日期：D-008，2026-08-01。

问题：如何限制异常长的本地推理、允许少量暂时性失败恢复，同时不隐藏失败、
不留下后台 GPU 调用，也不破坏严格断点续跑。

可选方案：线程超时后遗弃线程、子进程强杀、Adapter 协作式截止并逐调用落盘。

选择：Run record schema 0.4 为每次生成调用记录 `attempt_index`、`terminal`、
`retryable`、单次/累计延迟、超时和最大重试数。内置 Transformers Adapter
在模型一次性加载后计算剩余预算，并将其传给 `model.generate(max_time=...)`。
只有 `timeout` 与 `generation_error` 可按显式预算重试，每条失败在重试前同步
到 JSONL 与 manifest。

理由：Python 线程无法安全终止正在执行的 CUDA 内核；遗弃线程后继续重试会
造成并发 GPU 状态和虚假完成记录。每次调用先持久化，使断电后能从下一调用
序号继续，也让恢复成功的错误仍可审计。

影响：截止时间是协作式而不是硬实时保证；模型加载不被中断；自定义 Adapter
必须接受并遵守 `timeout_seconds`。发生过重试的运行不标记为正式性能运行。

何时重新评估：只有在 Adapter 能被隔离到拥有独立 GPU 生命周期的工作进程、
并能证明强杀后的资源回收与结果一致性时，才考虑硬进程超时。

## 5. 待确认决策

在第 3 周前确认：

- 是否在 Transformers 后端之外增加 llama.cpp 类后端；
- 正式项目名称和包名。

## 6. 决策记录规则

新增重要决策时记录：

```text
编号与日期：
问题：
可选方案：
选择：
理由：
影响：
何时重新评估：
```
