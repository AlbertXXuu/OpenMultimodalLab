# 功能报告：Task Schema v1

日期：2026-07-29

分支：`feat/task-schema-v1`

## 问题

初始 JSONL 任务没有显式格式版本。如果将来修改字段含义，旧任务可能被新代码错误解释，而且无法提供可靠的兼容或迁移策略。

## 实现

- 为每条任务增加必填字段 `schema_version`。
- 当前唯一支持的版本为 `"1.0"`。
- `EvaluationTask` 保留任务的 schema 版本。
- 缺失、空白或不支持的版本会在任务加载阶段被拒绝。
- Dataset 层继续为错误补充文件路径和 JSONL 行号。
- Smoke 数据和需求文档同步到 v1 格式。

## TDD 过程

实现前先增加两个测试：

- 缺少 `schema_version` 时必须失败；
- 使用不支持的 `"9.9"` 时必须失败。

红灯结果：

```text
Ran 7 tests
FAILED (failures=2)
```

实现后由开发者在本地 PowerShell 验证：

```text
Ran 7 tests
OK
```

## 端到端验证

执行：

```powershell
.\.venv\Scripts\oml.exe run `
  --dataset examples/tasks/smoke.jsonl `
  --output runs/schema-v1-smoke.jsonl
```

结果：

```text
Tasks: 3
Successful: 3
Success rate: 100.0%
Scored tasks: 2
Mean score: 1.000
Failures: {}
```

这些数字来自确定性 `mock` 后端，只验证任务加载和评测管线，没有表示真实模型能力。

## 验收结论

Task Schema v1 功能已达到当前验收标准：

- 版本字段被保存；
- 缺失版本被拒绝；
- 不支持版本被拒绝；
- 原有测试没有回归；
- 示例任务可以端到端运行。

## 下一步

扩充字段类型错误测试，并为数据集增加按 `metadata.category` 过滤任务的能力。
