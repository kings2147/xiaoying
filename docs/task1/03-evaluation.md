# 第一题：评估与复现

在仓库根目录设置 `PYTHONPATH=src`，执行：

```powershell
py scripts/evaluate.py media --provider mock --tests
py scripts/evaluate.py media --provider codex --cases normal conflict save_failure
```

输入、实际输出和 Trace 位于 `examples/media/`；汇总为 `evaluation.mock.json` 与 `evaluation.codex.json`；自动化测试原始输出为 `tests.txt`。
每份输出的 provider / real_model 标识真实来源。Mock 覆盖全部验收点；Codex 记录展示真实模型对正常、冲突及失败结果的动作调整。
评审可修改 occupied_slots 后重跑，观察 propose_slot 参数与 pending_confirmation；重复 normal 验证草稿 ID 不变。
保存故障以 simulate_failures.save_draft=-1 注入，预期 failed 且 draft=null。
真实模型具有随机性、网络/账户依赖和较高启动开销；离线结果只验证流程与工程约束。

本次实际结果：10 项自动化测试全部通过；5 个离线场景通过；3 个真实模型场景以及真实重复保存检查通过。真实冲突建议 19:00，保留待确认状态；保存永久故障返回 failed，未伪造草稿。
