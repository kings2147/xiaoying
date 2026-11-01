# 第三题：需求与验收

输入问题、可选用户对话历史、带 ID 和版本日期的合成制度或 FAQ；输出有原文支撑的回答、引用、缺口与状态。

| 验收点 | 对应运行用例/自动化测试 |
|---|---|
| 明确答案 | normal；test_clear_answer_has_exact_support |
| 文档冲突 | conflict；test_conflict_does_not_choose_latest |
| 资料外问题 | outside；test_outside_knowledge_and_rewritten_query |
| 改写相似问题 | paraphrase；test_paraphrase_and_followup |
| 上下文追问 | followup；test_paraphrase_and_followup |
| 工具失败 | tool_failure；test_tool_failure_never_fabricates_answer |
| 替换资料验证 | test_changed_original_changes_answer |

默认 D01 和 D02 都适用范围未知，30 天与 15 天冲突，版本日期不提供优先级。normal 通过 document_scope 明确限定 D01。
范围为小型合成语料的词法/同义词检索与结构化事实冲突检查；不接入企业内网或个人资料。
