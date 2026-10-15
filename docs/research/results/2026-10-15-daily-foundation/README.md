# 日常入口基础：实际验证记录

本批把已有收盘流程收敛为一个配置入口，尚未完成整个M0。实现版本为`8f13a48310fa6b0509bbb8bcc9c37b13c68badd3`，基线为`83a9c8819baa2c8986c74116ddd0c4aff8cd140a`。机器可读结果、参数Hash和来源Hash见[VALIDATION.json](VALIDATION.json)。本记录是作者本地验证，不是独立审计。

## 真实保留来源的运行结果

使用`config/daily/retained-evidence.json`，观察时间固定为2026-10-14 12:22:30.843577 UTC，要求行情日为10月14日；实际行情仍截至10月12日，`market_fresh=false`。配置检查与正常运行均成功，报告内容ID为`22627805c7a856e98060d169abba35d05130a4d1fcf0379c11d7a79e2d2d04a6`。

|原有对象|本次状态|新增披露|交易资格|
|---|---|---:|---|
|600036.SH 招商银行|继续观察|0|否|
|000002.SZ 万科A|暂停新交易，等待证据|0|否|
|601872.SH 招商轮船|继续观察|0|否|

这些状态来自旧研究和旧行情的重查，不是10月15日的新市场结论。原研究依据与局限见[原三案例](../2026-10-14-decision-loop-v0/README.md)及[原市场结果](../2026-10-14-real-market-v2/README.md)。没有新增公司判断，也没有策略盈利证明。

运行前后，使用的原Store与31份PDF逐文件SHA256完全相同。JSON公开Store Hash及排序后的31个PDF Hash摘要，完整路径映射留在本地私有证据中。该核验只覆盖本次使用来源，没有扫描或验收全部历史Raw。私有数据不可访问的审查者无法独立重验其字节相等性。

本入口调用既有离线收盘路径，市场HTTP请求0、破坏性删除0、订单0。新Journal与报告写入独立私有目录；账户未知继续保持未知。

## 软件验证

在上述实现SHA上执行：

```bash
.venv/bin/python -m pytest tests/test_daily_profile.py tests/test_decision_loop.py tests/test_decision_increment.py tests/test_decision_paper.py tests/test_cli.py --basetemp /private/tmp/一个不存在的新测试目录 -q
.venv/bin/astock doctor
.venv/bin/astock data contracts
.venv/bin/astock data contracts --catalog v2
.venv/bin/astock research daily --profile config/daily/retained-evidence.json --check
.venv/bin/astock research daily --profile config/daily/retained-evidence.json
```

57项通过，1.71秒，其中新入口14项；Doctor、原12项及v2九项合同检查通过。测试使用合成数据并禁止网络。贯通测试只替换市场快照边界，实际执行来源文档校验、决策、私有Journal和不可变报告；重复运行验证内容不变。反例覆盖路径越界、软/硬链接、来源与Journal冲突、真实/模拟模式、未来观察、重复组件及额外权限字段。

`--check`不打开数据库或创建输出，通过只代表配置和路径检查通过。完整集成回归、远端CI尚未运行；旧PR成功不能覆盖本批。下一批涉及更广应用接口迁移时执行必要完整回归。

## 增量与未完成项

两次小型定向测试、一个新Journal、新私有报告及私有验证文件共33,291,411逻辑字节，约0.0333GB。逐类文件数和大小见JSON；未计代码/文档、前期审计快照，不是全项目重新盘点。两个测试目录分别保留，未触碰旧pytest根。

M0仍需首批清理候选的重建/最小失败证据核验，以及新增产物登记和退出规则。此前41.798GB总量是10月15日11:22—11:23的容量快照。候选13.266GB不能写成已释放空间；尚未执行任何删除。
