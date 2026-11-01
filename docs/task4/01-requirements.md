# 第四题：需求与验收

输入主题、受众、平台、目标时长和风格；使用合成产品素材与品牌规则。
输出标题、可编辑分镜、旁白、各镜头及总时长、来源 ID、风险与任务状态。

| 验收点 | 运行/测试 |
|---|---|
| 正常生成 | normal；test_normal_generated_script_and_sources |
| 缺关键信息 | missing；test_missing_information_and_no_materials |
| 无素材 | no_material；同上，含改写查询 |
| 工具失败 | tool_failure；test_tool_failure |
| 超时长修正 | revise；test_duration_revision_rechecked |
| 无法满足时长 | impossible；test_impossible_duration_returns_incomplete |
| 禁止虚构数字/来源 | test_unsupported_claims_cannot_be_injected |
| 修改后重验 | test_revision_invalidates_previous_checks |

范围：事实编排型短视频脚本，模型选择来源、镜头、转场和停留时长；旁白由已检索原文事实与已批准转场文案组合。可编辑 JSON，不生成真实视频。
