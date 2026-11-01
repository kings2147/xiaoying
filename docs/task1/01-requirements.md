# 第一题：需求与验收

内容运营输入素材 ID、带时区的发布要求、硬性要求标记、已有占用时段及可选变更确认。
输出逐素材审核状态、风险、建议时段、待确认标记、草稿保存结果。全部使用合成业务数据。

| 验收点 | 自动化与运行证据 |
|---|---|
| 正常排期 | tests.test_media.test_normal_and_no_publication；examples/media/normal.*.json |
| 信息缺失 | test_missing_material_and_metadata；missing.*.json |
| 规则风险 | test_rule_risk_blocked；risk.*.json |
| 时段冲突和确认 | test_conflict_requires_explicit_approval；conflict.*.json |
| 重复提交 | test_repeat_save_and_failure；duplicate.*.json |
| 保存失败 | test_repeat_save_and_failure；save_failure.*.json |

范围：本地草稿；不实现真实发布、跨请求资源锁、生产级内容安全审核。
不同请求各自输入的已有排期是查询真值；同一请求内也校验素材之间的冲突。
硬性变更未确认时可以保存带 pending_confirmation 的草稿，状态保持 awaiting_confirmation。
