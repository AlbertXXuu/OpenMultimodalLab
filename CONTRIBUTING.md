# Contributing

OpenMultimodalLab 当前处于早期阶段，优先接受小型、可测试、能改善可复现性的贡献。

## 开发环境

正式支持 Python 3.11 和 3.12。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m unittest discover -s tests -v
```

## 修改要求

- 先说明要解决的问题和验收方式。
- 保持修改范围集中。
- 新行为需要测试。
- 文档命令必须实际运行。
- 不提交密钥、模型权重、大型数据和 `runs/` 结果。
- 不用 `mock` 后端结果描述真实模型能力。

## 新增模型 Adapter

新增 Adapter 时应提供：

- 模型名称、revision 和许可证链接；
- 安装依赖；
- 最低硬件或已验证硬件；
- 一个最小运行示例；
- Adapter 契约测试；
- 已知限制。

## 提交与 PR

推荐使用结果明确的提交标题：

```text
feat: add Qwen vision adapter
test: reject duplicate task identifiers
docs: define video sampling protocol
fix: record failures without losing completed tasks
```

PR 描述需要包含：

- 用户可见变化；
- 验证命令和结果；
- 兼容性或性能影响；
- 未解决问题。
