# 当前任务清单

只把当前两周内真正要做的事情放在顶部。

## Now：第 1 周

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

## Next：第 2 周

- [ ] 增加 `schema_version`。
- [ ] 检查重复任务 ID。
- [ ] 检查媒体文件存在性。
- [ ] 为错误信息增加行号和任务 ID。
- [ ] 建立 10 条许可证清晰的图片任务。
- [ ] 写第一版评测协议。

## Later

- [ ] 检测 GPU、显存、CUDA 和可用磁盘。
- [ ] 选择第一个真实 VLM。
- [ ] 实现真实模型 Adapter。
- [ ] 定义 warm-up、TTFT、吞吐和峰值显存测量。
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
