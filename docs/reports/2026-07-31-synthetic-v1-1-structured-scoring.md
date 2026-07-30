# synthetic-v1.1 与结构化评分

日期：2026-07-31

## 结果

项目发布了保持历史可审计的 `synthetic-v1.1`、任务 schema 1.1，以及两种任务显式选择的确定性评分器。Qwen3-VL-2B-Instruct 在最终数据上完成 10/10 条任务，运行失败为 0，结构化平均分为 1.000。

这是一轮功能正确性验证，不是正式模型性能比较：只运行了一次，没有 warm-up，第一条延迟包含模型加载。

原始记录保存在
[`results/2026-07-31-qwen3-vl-synthetic-v1-1.jsonl`](results/2026-07-31-qwen3-vl-synthetic-v1-1.jsonl)。

## 为什么不能直接修改 v1

第一轮真实模型运行发现：

1. 模型把颜色和形状分开表达时，连续短语匹配会把正确答案判为 0 分。
2. `spatial-above-001` 的提示只要求对象，参考答案却额外要求颜色。
3. `shapes-multi-001` 的图片是 60×60 正方形，参考答案却写成矩形。

`synthetic-v1` 已经产生过公开可追溯的运行结果，所以本次没有覆盖它，而是新建 `synthetic-v1.1`。两个版本共用同一组可重复生成、Apache-2.0 的 PNG 媒体。

## 数据和提示修复

- 把 `green rectangle` 修正为 `green square`。
- 明确要求 `spatial-above-001` 同时回答两个对象的颜色和形状。
- 把 `spatial-between-001` 和 `comparison-size-001` 的短答案格式写进提示。
- 每条任务增加 `metadata.dataset_version: synthetic-v1.1`。

## 评分契约

任务 schema 1.1 要求顶层 `scoring` 对象：

| 评分器 | 用途 | 规则 |
|---|---|---|
| `normalized_exact_match` | 数字、单词、明确限定的完整短答案 | 忽略大小写和标点后完整相等 |
| `attribute_groups` | 颜色+形状、多对象描述 | 属性必须在同一局部答案单元内，可要求顺序 |

属性组不是整段文本的词袋匹配。例如 `red square and blue circle` 不会错误满足 `red circle` 与 `blue square`。Markdown 列表可以保持同一项目里的属性绑定；有序列表还会检查组出现顺序。

旧 schema 1.0 和 `keyword_coverage` 保持兼容。

## 可追溯结果

运行记录升级为 schema 0.2，并增加：

- `task_schema_version`
- `dataset_version`
- `metric_name`
- `metric_details`

评分器异常现在写成独立的 `evaluation_error`，已经成功生成的模型回答仍会保留，不再误记成生成失败。

## 验证

离线验证：

```text
Ran 29 tests
OK
```

测试覆盖：

- v1.0 向后兼容；
- v1.1 评分配置校验；
- 精确匹配对大小写、标点和额外文本的处理；
- 属性分离表达；
- 颜色/形状错误绑定；
- 有序列表逆序；
- 评分失败与模型生成失败的区分；
- v1.1 十条任务、许可证与可重复媒体。

真实验证命令：

```powershell
.\.venv-ml\Scripts\oml.exe run `
  --backend qwen3-vl `
  --dataset examples/tasks/synthetic-v1.1.jsonl `
  --max-new-tokens 64 `
  --output runs/qwen3-vl-synthetic-v1.1.jsonl
```

结果：

```text
Tasks: 10
Successful: 10
Success rate: 100.0%
Scored tasks: 10
Mean score: 1.000
Failures: {}
```

模型 revision 仍固定为：

```text
89644892e4d85e24eaac8bacfd4f463576704203
```

## 限制与下一步

- 满分只说明模型通过这十条基础合成任务，不代表真实世界多模态能力。
- 当前属性组解析器面向短英文答案；更多语言和复杂句法需要专门用例。
- 单次延迟不能用于模型比较。

下一步实现可配置 warm-up、三次重复、TTFT、生成吞吐和峰值显存，把功能验证升级成正式可比较的性能实验。
