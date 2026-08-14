# 数据集报告：synthetic-v1

日期：2026-07-29

分支：`agent/synthetic-dataset-v1`

## 目标

在接入真实视觉语言模型前，建立一组来源清楚、答案确定、可以完全重新生成的图片任务，用它验证媒体加载、评测记录和后续模型 Adapter。

## 数据集

`synthetic-v1` 包含 10 张 320×240 RGB PNG：

| 类别 | 数量 |
|---|---:|
| Image description | 2 |
| Counting | 3 |
| Spatial reasoning | 4 |
| Visual comparison | 1 |

所有媒体均由 `scripts/generate_synthetic_images.py` 使用 Python 标准库生成，没有下载或复制第三方图片。

## 可复现性

自动测试会：

1. 在临时目录重新生成全部图片；
2. 检查文件名和数量；
3. 将新图片与仓库图片逐字节比较。

验证结果：

```text
test_committed_images_match_the_generator ... ok
test_synthetic_v1_has_ten_licensed_tasks ... ok
Ran 11 tests
OK
```

## 人工检查

人工查看了以下代表样本：

- 红色圆形与蓝色方形；
- 红色方形、紫色三角形、蓝色圆形的 between 关系；
- 五个蓝色方形的计数任务。

画面内容与 JSONL 中的任务描述、答案和类别一致。

2026-08-14 更新：所有 10 张原图及 10 条 `synthetic-v1.1` 任务均由
`AlbertXXuu` 逐项复核。正式记录见
[`docs/reviews/synthetic-v1.1.json`](../reviews/synthetic-v1.1.json)，并绑定
数据集 SHA-256 `682e4089fc2f9793209b40beb0026279bd0f58d3ec4fcf75d3f65abba88e4692`。

## 端到端结果

使用 `mock` 后端运行完整数据集：

```text
Tasks: 10
Successful: 10
Scored tasks: 10
Mean score: 1.000
Failures: {}
```

`mock` 会根据预期关键词产生确定性文本，因此此结果只证明基础设施能完整处理数据集，不表示真实视觉模型达到满分。

## 限制

- 图像只包含平面几何形状，不能代表真实世界视觉多样性。
- 当前关键词评分器对同义词和答案顺序不够稳健。
- 没有遮挡、噪声、旋转或复杂背景。
- 尚未使用真实 VLM 验证任务难度。

## 下一步

选择一个适合 8GB 显存的真实 VLM，先在这 10 条任务上建立第一个真实基线，再根据失败类型扩展任务和评分器。
