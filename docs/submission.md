# 提交信息

仓库：https://github.com/kings2147/xiaoying

本仓库依题号顺序完成四题。每题代码、五份文档和输入/实际输出/Trace 都在同一个仓库，README 提供评审命令。

| 题号 | 项目 | 业务实现 commit | 评审入口 |
|---|---|---|---|
| 1 | 素材审核与发布排期 Agent | f0f3320 | docs/task1/；examples/media/；src/xiaoying_agents/media.py |
| 2 | 内容任务规划 Agent | 6fd592b | docs/task2/；examples/planning/；src/xiaoying_agents/planning.py |
| 3 | 企业知识问答 Agent | d647ee8 | docs/task3/；examples/knowledge/；src/xiaoying_agents/knowledge.py |
| 4 | 短视频脚本 Agent | e10596a | docs/task4/；examples/script/；src/xiaoying_agents/script.py |

基础工程 commit 为 9ee6902；后续整体验证提交补齐评审索引、CI 和最终证据重放。
正式填写时使用最终 main 的完整 SHA，以包含后续公共设施与证据修正；可在本地执行 `git rev-parse HEAD` 获取，并用 `git ls-remote origin refs/heads/main` 核对远端。
四题可使用同一个最终 SHA，通过上表指向各自模块和材料。每题的业务 commit 记录实现阶段，最终 SHA 包含完整交付。

验证：33 项自动化测试；22 个离线场景；12 个真实模型场景，另 2 个真实重复执行；38 份输出/Trace 重放。
AI 辅助与当前实际个人贡献详见 docs/04-ai-usage.md。提交人须如实补充本人后续运行、理解和修改内容。
