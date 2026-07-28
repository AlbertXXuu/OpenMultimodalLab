# 功能报告：按类别过滤任务

日期：2026-07-29

分支：`agent/category-filter`

## 问题

任务集扩大后，开发者需要只运行某一类任务，而不是每次执行完整数据集。例如调试图片描述评分器时，不应同时运行文档或空间推理任务。

## 用户接口

`--category` 使用精确匹配，并且可以重复：

```powershell
oml run `
  --dataset examples/tasks/smoke.jsonl `
  --output runs/selected.jsonl `
  --category image-description `
  --category smoke-test
```

输出保持原任务集中的顺序。

## 错误行为

如果没有任务匹配，命令：

- 返回退出码 `2`；
- 列出数据集中可用的类别；
- 不创建空结果文件。

示例：

```text
Dataset error: No tasks matched categories: video.
Available: image-description, infrastructure, smoke-test
```

## TDD 结果

实现前，两条新 CLI 测试因参数尚不存在而出现预期错误：

```text
Ran 9 tests
FAILED (errors=2)
```

实现后：

```text
Ran 9 tests
OK
```

## 端到端检查

选择 `image-description` 后：

```text
Tasks: 1
Successful: 1
Scored tasks: 1
Mean score: 1.000
```

选择不存在的 `video` 后：

```text
ExitCode=2
OutputExists=False
```

以上运行使用确定性 `mock` 后端，只验证筛选与评测管线行为。
