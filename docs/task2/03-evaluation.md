# 第二题：评估与复现

```powershell
py scripts/evaluate.py planning --provider mock --tests
py scripts/evaluate.py planning --provider codex --cases normal replan tool_failure
```

实际报告在 `examples/planning/evaluation.mock.json` 和 `evaluation.codex.json`，Trace 在各 `*.mock.json` / `*.codex.json` 中；测试原始输出为 `tests.txt`。
normal 预期总价 12；replan 先观察 12 超出预算 10，再改选 8；overbudget 预算 3 时所有方案不可行，返回缺口。
故障注入为 generate_script 永久失败，预期 incomplete 且保留 assets/estimates；自动化测试在同一 Store 解除故障后续跑，并断言不重复检索。
评审可改预算或截止时间，核对最终可行性和工具参数变化；脚本模板与成本表是合成业务工具，不代表真实生产服务。

本次实际结果：11 项自动化测试、5 个离线场景、3 个真实模型场景及真实重复执行检查全部通过。真实 replan 从 12 改选 8；生成工具永久失败时模型停止，保留素材与估算，状态为 incomplete。
