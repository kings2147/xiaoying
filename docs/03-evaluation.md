# 全仓库验证方法

在仓库根目录：

```powershell
$env:PYTHONPATH = "src"
py -m unittest discover -s tests -v
py scripts/evaluate.py media --provider mock --tests
py scripts/evaluate.py planning --provider mock --tests
py scripts/evaluate.py knowledge --provider mock --tests
py scripts/evaluate.py script --provider mock --tests
py scripts/audit_evidence.py
py scripts/check.py
```

单元测试共 33 项：公共边界 4 项，排期 7 项，规划 7 项，知识问答 8 项，脚本 7 项。
离线验收共 22 个场景，另有排期和规划的重复执行记录。真实模型每题运行正常、关键分支、工具失败三组场景，排期/规划另运行真实重复执行。
各题汇总、实际输出和逐步 Trace 位于 examples/{media,planning,knowledge,script}/。带 provider=mock 的记录不证明真实模型决策能力。
audit_evidence.py 不调用模型，而是用记录中的动作重放当前业务工具，逐项核对工具观察、最终结果与终止状态；报告在 examples/evidence_audit.json。
测试与实际运行的最终整体结果见 README；每题预期和限制见 [第一题](task1/03-evaluation.md)、[第二题](task2/03-evaluation.md)、[第三题](task3/03-evaluation.md)、[第四题](task4/03-evaluation.md)。
GitHub CI 在 Windows/Ubuntu 与 Python 3.11/3.12 上运行离线测试、场景和证据重放；真实模型验证保留本机实际输出，不在 CI 中使用个人登录凭据。
