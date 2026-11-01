# 小影 AI Agent 项目

按题号顺序实现四个独立业务 Agent，共用有步数上限的模型/工具运行循环。
所有业务素材、制度、费用均为合成数据；仅保存本地草稿与方案。

## 环境与运行

Python 3.11+，运行和测试仅用标准库。PowerShell：

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
# 后续每题提供独立输入、命令和 examples 证据。
```

也可 `python -m pip install -e .` 后使用 `xiaoying` 命令。模型入口：

- `--provider mock`：无网络的确定性测试替身，只证明流程和约束。
- `--provider codex`：调用本机已登录的 Codex CLI，每一步由真实模型选择下一动作；无需把凭据交给项目。
- `--provider openai`：配置 `.env.example` 中的环境变量，调用兼容的 Chat Completions JSON 接口。

真实模型与 Mock 的运行记录分别存放，不把离线记录作为真实决策证据。

## 工程流程

每题依次完成需求与验收映射、工具/决策实现、自动化测试、实际示例运行、五份文档、Git commit。
每次工具调用的参数、结果和下一步简要依据存入 Trace；达到步数上限明确返回 incomplete。
README 和评估文档只记录实际运行结果。AI 使用与人工贡献据实记载。
