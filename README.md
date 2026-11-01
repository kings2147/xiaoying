# 小影 AI Agent 项目

按题号顺序实现四个独立业务 Agent，共用有步数上限的模型/工具运行循环。
所有业务素材、制度、费用均为合成数据；仅保存本地草稿与方案。

## 本次验证结果

33 项自动化测试、22 个离线验收场景、12 个真实模型场景全部通过；排期和规划另有 2 份真实重复执行记录。
38 份实际输出/Trace 可用 `py scripts/audit_evidence.py` 重放业务工具核对。
`py scripts/check.py` 一次执行全量单元测试与证据重放，报告写入 `examples/validation.json` 和 `examples/tests.txt`。

| 题号 | 已验证的关键行为 | 离线场景 | 真实模型场景 |
|---|---|---:|---:|
| 1 素材审核与排期 | 18:00 冲突改建议 19:00，保留待确认；仅保存一份草稿 | 5 | 3 + 重复保存 |
| 2 内容任务规划 | 预算 10 时从报价 12 改选 8；故障保留成功结果；支持续跑 | 5 | 3 + 重复执行 |
| 3 企业知识问答 | 30 天与 15 天冲突时引用双方并请求确认，读取失败不生成答案 | 6 | 3 |
| 4 短视频脚本 | 真实模型将 48 秒初稿修订为 30 秒，并重做当前版本的两项检查 | 6 | 3 |

[完整需求](docs/01-requirements.md) · [总方案](docs/02-solution.md) · [评估方法](docs/03-evaluation.md) · [AI 使用](docs/04-ai-usage.md) · [复盘](docs/05-retrospective.md) · [提交信息](docs/submission.md)

## 环境与运行

Python 3.11+，运行和测试仅用标准库。PowerShell：

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
py -m xiaoying_agents media --input examples/media/conflict.input.json --provider mock
py -m xiaoying_agents media --input examples/media/conflict.input.json --provider codex
```

也可 `python -m pip install -e .` 后使用 `xiaoying` 命令。模型入口：

- `--provider mock`：无网络的确定性测试替身，只证明流程和约束。
- `--provider codex`：调用本机已登录的 Codex CLI，每一步由真实模型选择下一动作；无需把凭据交给项目。
- `--provider openai`：配置 `.env.example` 中的环境变量，调用兼容的 Chat Completions JSON 接口。

真实模型与 Mock 的运行记录分别存放，不把离线记录作为真实决策证据。
本机已在隔离虚拟环境验证 editable 安装及 `xiaoying` 命令。JSON 文件与标准输出使用 UTF-8。
CLI 退出码：0 为完成或明确的业务待确认/缺资料状态，1 为 failed/incomplete，2 为输入或环境错误。
默认 `.runtime/state.sqlite3` 保留幂等状态；独立试跑可指定 `--state :memory:`，持久化续跑使用相同数据库路径与业务输入。
Codex CLI 为本次实际验证的真实模型入口；OpenAI 兼容 API 入口尚未做真实服务联调。

## 工程流程

每题依次完成需求与验收映射、工具/决策实现、自动化测试、实际示例运行、五份文档、Git commit。
每次工具调用的参数、结果和下一步简要依据存入 Trace；达到步数上限明确返回 incomplete。
README 和评估文档只记录实际运行结果。AI 使用与人工贡献据实记载。

## 第一题评审入口

[需求与验收](docs/task1/01-requirements.md) · [方案](docs/task1/02-solution.md) · [评估与复现](docs/task1/03-evaluation.md) · [AI 使用](docs/task1/04-ai-usage.md) · [复盘](docs/task1/05-retrospective.md)

`py scripts/evaluate.py media --provider mock --tests` 重跑全部离线场景与测试。
`py scripts/evaluate.py media --provider codex --cases normal conflict save_failure` 重跑真实模型路径。
每份 `examples/media/*.mock.json` / `*.codex.json` 同时包含实际输出与逐步 Trace。

## 第二题评审入口

[需求与验收](docs/task2/01-requirements.md) · [方案](docs/task2/02-solution.md) · [评估与复现](docs/task2/03-evaluation.md) · [AI 使用](docs/task2/04-ai-usage.md) · [复盘](docs/task2/05-retrospective.md)

`py -m xiaoying_agents planning --input examples/planning/replan.input.json --provider codex` 运行预算重规划。
`py scripts/evaluate.py planning --provider mock --tests` 重跑全部离线场景。
`py scripts/evaluate.py planning --provider codex --cases normal replan tool_failure` 重跑真实模型场景。

## 第三题评审入口

[需求与验收](docs/task3/01-requirements.md) · [方案](docs/task3/02-solution.md) · [评估与复现](docs/task3/03-evaluation.md) · [AI 使用](docs/task3/04-ai-usage.md) · [复盘](docs/task3/05-retrospective.md)

`py -m xiaoying_agents knowledge --input examples/knowledge/conflict.input.json --provider codex` 运行制度冲突问答。
`py scripts/evaluate.py knowledge --provider mock --tests` 重跑全部离线场景。
`py scripts/evaluate.py knowledge --provider codex --cases normal conflict tool_failure` 重跑真实模型场景。

## 第四题评审入口

[需求与验收](docs/task4/01-requirements.md) · [方案](docs/task4/02-solution.md) · [评估与复现](docs/task4/03-evaluation.md) · [AI 使用](docs/task4/04-ai-usage.md) · [复盘](docs/task4/05-retrospective.md)

`py -m xiaoying_agents script --input examples/script/revise.input.json --provider codex` 运行超时长修订。
`py scripts/evaluate.py script --provider mock --tests` 重跑全部离线场景。
`py scripts/evaluate.py script --provider codex --cases normal revise tool_failure` 重跑真实模型场景。
