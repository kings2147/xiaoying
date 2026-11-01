# 工程约定

四题顺序：1 素材审核与发布排期；2 内容任务规划；3 企业知识问答；4 短视频脚本。
采用 Python 3.11 标准库原生实现。模型驱动可由 Codex CLI 或兼容 API 完成；Mock 是测试替身。
各题保留独立需求、方案、评估、AI 使用、复盘与独立提交。
成功状态从工具真实返回与约束校验构造，模型的自然语言不能覆盖工具失败或批准状态。
使用 SQLite 主键约束持久化幂等；默认数据目录 .runtime 被 Git 忽略。
不含真实发布工具、真实费用支付工具或个人资料；所有业务数据为合成数据。

Codex CLI 以临时空目录、read-only sandbox、ephemeral 会话运行，并对每次调用设置超时。
后续运行显式关闭 shell_tool，并将动作选择的 reasoning effort 设为 low，以减少简单单步决策的开销；不改变本机配置文件。
配置参数参考 [OpenAI 官方配置文档](https://learn.chatgpt.com/docs/config-file/config-reference)，实际 CLI 参数经本机 `codex exec --help` 核对。
真实模型示例使用本机已安装的 Codex CLI 0.159.2。项目不读取或复制登录凭据；模型选择继承本机配置（可由 CODEX_MODEL 显式指定）。
