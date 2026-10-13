# P1/P2修复后的业务复现

本批新真实市场请求0。以下是同一 Research V2 实现的新公开投影，协议 RESEARCH_PUBLIC_V2_1。
默认不包含人工观察卡、Journal、源路径、自由来源说明或请求扩展；私有完整报告不变。
来源hash、单位、可知时间、业务指标、程序候选、分母及计算参数保留。

- [既有10股真实观察](actual-limited/720ba25cba91ae9a238323ced3dfedbc2588558ad532a6737296b30cc809f16e.md) / [JSON](actual-limited/720ba25cba91ae9a238323ced3dfedbc2588558ad532a6737296b30cc809f16e.json)：与PR #4已接受结果逐项比较，市场、特征、4候选及radar完全一致。源Store与原私有报告运行前后SHA256不变。没有新增真实行业来源。
- [299闭合Mock行业演示](synthetic/61a3ff691114da49c66594f524377f63b46b30b5f66a5ea1983ee237cfc8155e.md) / [JSON](synthetic/61a3ff691114da49c66594f524377f63b46b30b5f66a5ea1983ee237cfc8155e.json)：SYNTHETIC；299 COMPLETE，不是现实全市场验收。

复现Mock：`uv run --offline --frozen python scripts/research_v2_demo.py --work /private/tmp/astock-safety-demo-new --output docs/research/results/new-synthetic`。
真实Raw/许可仍为私有，公开hash不能代替供应商签名；无访问权的审查者不能独立核实全部Raw。
已检查先前3份公开JSON：没有人工卡、真实Journal内容或个人绝对路径。旧Level B的PRIVATE_RAW_SHA256/PRIVATE_EVIDENCE_SHA256为脱敏hash别名，并非实际磁盘路径；已接受历史结果保留，不改写。
