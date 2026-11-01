# 第二题：需求与验收

用户提供主题、预算、开始时间与截止时间；时间显式携带时区。使用合成素材、费用和耗时表。
输出计划步骤、依赖、工具结果、最终方案费用、保存结果，或未完成原因与预算/时间缺口。

| 验收点 | 证据 |
|---|---|
| 正常完成 | tests/test_planning.py；examples/planning/normal.*.json |
| 缺预算/截止时间 | test_missing_budget_and_deadline；missing.*.json |
| 工具失败与成功结果保留 | test_failure_preserves_success_and_resumes；tool_failure.*.json |
| 超预算调整/无法满足 | test_budget_replanning_12_to_8、test_no_feasible_budget_or_deadline；replan、overbudget.*.json |
| 重复执行 | test_duplicate_and_overbudget_guard；duplicate.*.json |
| 失败步骤续跑 | test_failure_preserves_success_and_resumes |

费用单位是模拟活动计划单位。探索阶段的检索/估算/模板生成不产生真实费用；费用合计指最终选定方案的预算，不是累加废弃候选方案的报价。
