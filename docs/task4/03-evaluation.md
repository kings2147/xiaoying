# 第四题：评估与复现

```powershell
py scripts/evaluate.py script --provider mock --tests
py scripts/evaluate.py script --provider codex --cases normal revise tool_failure
```

输入、输出、原始版本和各版检查保存在 `examples/script/`；汇总为 evaluation.mock.json 与 evaluation.codex.json；测试原始输出为 tests.txt。
normal 目标 60 秒，详细初稿可通过；revise 目标 30 秒，详细初稿超时后由模型压缩并重做两项检查；impossible 目标 1 秒，最短脚本仍不能满足。
工具故障注入 estimate_duration 永久失败，预期 incomplete；缺受众与无素材分别返回 needs_information 和 needs_materials。
测试还验证不得引用未知事实 ID、不得添加无来源的 80% 数字，以及修改脚本后旧检查失效。
每份输出中的 scenes、duration.scenes 与 rule_check.citations 可按 scene/source_id 对照。Mock 只证明流程；真实动作证据以 codex 文件为准。

本次实际结果：11 项自动化测试、6 个离线场景和 3 个真实模型场景全部通过。真实 revise 将 48 秒初稿压缩为 30 秒，两项检查均在第 2 版通过；estimate_duration 永久失败时返回 incomplete。额外约束阻止把仅有字幕来源的镜头写成剪辑功能展示。
