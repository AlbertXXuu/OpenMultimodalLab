# 当前任务清单

只把当前两周内真正要做的事情放在顶部。

## Now：第 3 周

- [x] 审查代码、测试、构建、文档链接、许可证边界和 GitHub CI。
- [x] 检测 NVIDIA GPU、显存、驱动和 PyTorch CUDA 可用性。
- [x] 选择并固定第一个真实 VLM：Qwen3-VL-2B-Instruct。
- [x] 实现懒加载真实模型 Adapter 和可选择的 CLI backend。
- [x] 区分模型加载失败、显存不足和通用生成错误。
- [x] 在 RTX 4060 8GB 上完成 10 条真实图片任务基线。
- [x] 发布 `synthetic-v1.1`，修复参考答案与合成图形不一致。
- [x] 增加按任务类别选择的结构化评分器。
- [x] 定义并实现 warm-up、三次重复、TTFT、吞吐和峰值显存测量。
- [x] 选择并固定第二个可在 8GB 显存运行的不同模型家族：SmolVLM2-500M。
- [x] 为第二个模型实现相同 Adapter 与性能指标契约。
- [x] 在相同任务、提示和正式协议上发布首份双模型对比。
- [x] 默认保护已有输出，只允许显式 `--overwrite`。
- [x] 实现严格断点续跑，拒绝配置、顺序、边界或哈希不一致。
- [x] 每条记录落盘后原子更新 manifest，并记录结果字节数与 SHA-256。
- [x] 将编译、依赖、仓库审计和 wheel 构建加入 GitHub CI。
- [x] 阻止重复分支/PR CI，并取消同一 PR 的过期运行。
- [x] 将主 README 改为英文结果首页，并保留完整中文入口。
- [x] 增加从离线 smoke 到真实正式实验的可复制教程。
- [x] 增加 Bug、模型 Adapter、数据任务 Issue Form 和 PR 模板。
- [x] 增加不公开泄漏漏洞细节的安全报告策略。
- [x] 在全新 Windows Python 3.11 环境安装 wheel，并把仓库外冒烟测试加入 CI。
- [x] 固定 GitHub Actions 完整提交哈希，并配置每周分组依赖更新。

## Completed：第 1 周

- [x] 写项目规划书。
- [x] 写 12 周主目标和第一周验收标准。
- [x] 定义范围、架构、路线图和周更规则。
- [x] 建立 Python 包和 CLI。
- [x] 实现 JSONL 任务加载与校验。
- [x] 实现 `mock` Adapter。
- [x] 实现 Runner、关键词评分和 JSONL 结果。
- [x] 实现汇总报告。
- [x] 添加离线自动测试。
- [x] 添加 GitHub Actions CI。
- [x] 从新建虚拟环境验证快速开始命令。

## Completed：第 2 周

- [x] 增加 `schema_version`，拒绝缺失或不支持的版本。
- [x] 检查重复任务 ID。
- [x] 检查媒体文件存在性。
- [x] 支持按一个或多个任务类别过滤运行。
- [x] 为错误信息增加行号和任务 ID。
- [x] 建立 10 条许可证清晰且可重新生成的图片任务。
- [x] 写第一版评测协议。

## Later

- [ ] 检测并记录可用磁盘。
- [ ] 制作文档、视频和图表任务集。
- [ ] 邀请外部试用者。

## 本周出口条件

以下命令全部成功后，第 1 周才算完成：

```powershell
python -m pip install -e .
oml doctor
oml run --dataset examples/tasks/smoke.jsonl --output runs/smoke.jsonl
oml report --input runs/smoke.jsonl
python -m unittest discover -s tests -v
```

## 工作记录

完成任务后在对应复选框打勾，并把真实结果写入 PR、Release Notes 或周报。不要把计划中的数字写成已完成结果。

第一周实际结果见：[docs/reports/2026-07-28-week-01.md](docs/reports/2026-07-28-week-01.md)。

合成图片任务结果见：[docs/reports/2026-07-29-synthetic-v1.md](docs/reports/2026-07-29-synthetic-v1.md)。
