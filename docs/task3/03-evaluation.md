# 第三题：评估与复现

```powershell
py scripts/evaluate.py knowledge --provider mock --tests
py scripts/evaluate.py knowledge --provider codex --cases normal conflict tool_failure
```

运行输入与输出/Trace 存放在 `examples/knowledge/`；汇总为 evaluation.mock.json、evaluation.codex.json；自动化原始输出为 tests.txt。
normal 预期引用 D01 的 30 天原文；conflict 必须同时引用 D01/D02 并请求确认；资料外问题只报告缺口。
tool_failure 注入原文读取永久失败，预期 incomplete 且不生成无引用答案。
其余离线场景覆盖问题改写与用户历史追问；自动化测试替换为 7 天制度后断言答案改变，并拒绝未读来源和只选一份冲突文档。
小型语料与合成数据不证明企业级召回率；运行报告呈现单次真实模型行为，不声称随机模型始终得到相同路径。

本次实际结果：12 项自动化测试、6 个离线场景和 3 个真实模型场景全部通过。真实冲突路径读取并引用 D01/D02，返回 conflict；原文工具永久失败时返回 incomplete 且 answer=null。
