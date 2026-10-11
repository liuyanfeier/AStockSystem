# 当前交付与 Review 入口

本文件与代码一起提交，是最新批次的审查入口。后续批次更新这里，过去版本从 Git 查阅；
长期目标、真实状态、架构和数据契约继续各自维护，不复制成大量临时报告。
用户提供 PR 或分支链接即可。Reviewer 先取得可访问的实际仓库版本；如果无法读取代码或 CI，
应说明访问限制，不能仅凭链接或作者摘要给出 PASS。

## 当前批次与验收范围

2026-10-11，项目方向重置、渐进清理及仓库内自包含交付。
用户明确要求在现有 AStockSystem 继续建设长期投资研究与交易决策系统，并提供完整宪章 V2；
随后同意从现在开始，让 GPT 通过 Git 提交和提交内文件评估与 Review，无需额外转交材料。
当前授权允许专用分支连续提交、必要修复和测试；未授权新市场 API、真实 fact 导入、
历史事实改写、不可恢复私有数据删除或自动下单。

| 验收要求 | 对应交付与审查重点 |
|---|---|
| 完整长期目标，保持原意 | [PROJECT_CHARTER](PROJECT_CHARTER.md) 保留用户完整正文；[README](../README.md)、[AGENTS](../AGENTS.md) 统一入口与文档优先级 |
| 真实理解现有成果与不足 | [CURRENT_STATE](CURRENT_STATE.md)：代码、真实数据、空占位、Git/CI；不得将旧阶段报告当成当前软件状态 |
| 业务路线及新旧迁移边界 | [ROADMAP](ROADMAP.md)、[ARCHITECTURE](ARCHITECTURE.md)、[CODE_MIGRATION](CODE_MIGRATION.md)；核查动态依赖，未批量删除旧代码 |
| 有依据地精简历史文档 | [HISTORY](HISTORY.md)、[REPOSITORY_RESET](REPOSITORY_RESET.md)：5份删除文件、原因、原路径与Git恢复依据；重要历史审查/来源保留 |
| 数据保护与容量治理 | [STORAGE_GOVERNANCE](STORAGE_GOVERNANCE.md)、[容量工具](../scripts/repository_inventory.py)、[边界测试](../tests/test_repository_inventory.py)；私有清理只是提案 |
| 下一批直接产生研究价值 | [RESEARCH_V1](RESEARCH_V1.md)：真实行情 → 独立 Research Store → Market Regime / Screening → 候选观察报告；已列已有依赖、数据和新模块 |
| Git 内自包含 Review | 本入口、AGENTS交付规范及[PR模板](../.github/PULL_REQUEST_TEMPLATE.md)；任务范围、证据、局限和版本随提交公开 |

## 版本与审查方式

- 仓库：[liuyanfeier/AStockSystem](https://github.com/liuyanfeier/AStockSystem)。
- 开发分支：[codex/project-reset-research-v1](https://github.com/liuyanfeier/AStockSystem/tree/codex/project-reset-research-v1)。
- 开始基线：`c1a9ef7f0ebb063f4b0ebd3ec6e4733a15e6f5db`。
- 方向、清理及容量工具提交：`7a27b53ab97b695fb857722fefa4c7ecfd076fbf`。
- 本地验证记录提交：`3c6ecace207c052e2373b0c52aa3d3d5eed121f4`。
- 后续提交落实本入口与交付规范；最终版本取当前 PR head 或 `git rev-parse HEAD`。
  Reviewer 开始时记录具体 SHA，避免审查过程中分支更新改变对象。

~~~bash
git rev-parse HEAD
git log --oneline c1a9ef7f0ebb063f4b0ebd3ec6e4733a15e6f5db..HEAD
git diff --stat c1a9ef7f0ebb063f4b0ebd3ec6e4733a15e6f5db...HEAD
git diff c1a9ef7f0ebb063f4b0ebd3ec6e4733a15e6f5db...HEAD
~~~

这些是只读审查命令。审查要沿实际 diff 检查相关调用、配置和回归，不限于提交摘要。
当前批次没有替换既有业务实现；容量工具新增3条测试，既有测试和安全检查完整保留。
main 未改动，历史不重写。文档恢复办法见清理记录；Git不能恢复未入库的私有数据。

## 验证证据与实际局限

| 验证 | 已观察结果与范围 |
|---|---|
| 本地既有全套回归 | 既有源码/测试与开始基线c1a9ef7一致：1005 passed，1个既有fork弃用警告，1217.32秒；新测试另运行 |
| 新增容量工具回归 | 对应7a27b53中的新增脚本和测试：`uv run --offline --frozen pytest tests/test_repository_inventory.py`：3 passed，0.32秒；与上一行分开运行，不冒充一次1008项全套 |
| 本地离线诊断与契约 | doctor、v1/v2 contracts、identity/slice specs、probe/slice plan及统一23契约 specs通过；命令见[清理记录](REPOSITORY_RESET.md)和[操作资料](phase1/operations.md) |
| 数据与来源保护 | 作者本机自检：既有155,655数据文件全hash起止一致、146,656保护路径、171固定pin、23运行pin及V1/V2来源验证通过；4个主要DB只读查询前后hash不变且无WAL |
| 公开材料与秘密 | 作者自检：入口链接、diff和明文/编码/解码凭据检查通过，无私有数据入Git；Review仍应检查实际提交 |
| 本次交付规范更新 | 5份新增/修改文件本地链接、明文/编码/解码凭据与diff检查通过；宪章仍与用户原文逐字节相同，既有运行代码、测试、配置和CI工作流无改动 |
| GitHub CI | [3c6ecac运行](https://github.com/liuyanfeier/AStockSystem/actions/runs/38106829086)在本入口写入时仍in_progress，无成功结论；[当前分支CI](https://github.com/liuyanfeier/AStockSystem/actions?query=branch%3Acodex%2Fproject-reset-research-v1)可核对新HEAD |

CI状态是上述版本的观察记录，之后可能变化。Reviewer须核对 run 的 head_sha、status、
conclusion和日志；前一版本CI或本地分组通过不等于最新HEAD CI通过。
本批后续交付规范改动仅涉及文档与PR模板，完整软件验证与最终文档HEAD分别记录。
复现公开软件检查使用README命令；不用真实市场API或私有原库写入来验证本批文档整理。

私有核验清单、原文副本及全hash证据保留在本地 ignored `data/private/repository-governance/2026-10-11/`，
不需要用户每批转交。公开仓库只足以复查软件、文档、方法、公开CI与脱敏摘要；
没有私有访问权限时，真实数据保护结果只能标为作者自检，不能写成独立数据验收PASS。
独立Review不能自动扩大采集、删除、风险参数或交易授权。

## 未完成项与下一批

- Research Store、Market Regime、Screening和业务报告仍未实现；本批完成的是明确可执行入口。
- 最新真实股票报告需要当前用途适合的近期来源；旧离散样本、RAW_ONLY和未准入facts不能冒充最新连续行情。
- 全历史研究准入仍有缺口；它不应变成重新开启大规模Phase1的默认任务。
- 私有冗余/缓存候选约0.881GB，未删除；实际释放受备份、共享块、依赖和用户批准影响。

下一批按RESEARCH_V1完成最小观察闭环。新增真实调用、私有破坏性清理及风险参数需要各自明确授权，
普通离线开发与回归按当前范围持续完成后统一Review。
