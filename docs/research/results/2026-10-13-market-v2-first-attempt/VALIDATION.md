# 验证摘要：软件成功，首次真实全市场采集停止

| 检查 | 证据与结果 |
|---|---|
| 最小测试修复 | 29c30b1仅改进程死亡测试；43 passed，5轮重复各43 passed |
| 完整本地 | 1175 passed、1 warning、1271.95s；Doctor/12 contracts PASS |
| 修复SHA push/PR CI | 38402228635 / 38402232299均成功，各1175 passed、5 warnings；最终交付HEAD CI另由PR记录 |
| 原批准计划/实现 | 16e127ef… / d8e4b225…，新main dry-run匹配；299成员，原日期/预算不变 |
| 实际新调用状态 | 1 UNKNOWN，0 COMPLETE/FAILED，298未尝试；无响应/Raw/回执 |
| 本地证据链读回 | capture_status核验claim/result/许可/plan绑定；UNKNOWN不能改写或自动重发 |
| 新股票数值抽查/Store重建 | NOT_RUN，无输入，不冒充PASS |
| 旧106保全 | 391文件SHA256无变化；39 COMPLETE/66 FAILED/1 UNKNOWN不变 |
| 历史文件保全 | 155655文件SHA256/size核查，changed=0、missing=0 |
| 采集目录实际体积 | 78,521字节，无Raw市场响应 |
| 总容量 | 16根，33,622,439,763逻辑字节；34,619,711,488文件blocks；340333文件/1961数据库，complete=true |
| 公开隐私 | 既有public_snapshot白名单；没有Journal、人工观察、私人路径、许可内容或Raw |
| 新恢复提案 | 仅改变002目的地的同299成员；plan 2006eb17…、实现d8e4b225…；dry-run通过，未授权 |

私有停采辅助快照仅用于事实投影，未从新Store生成业务分析，也未读取或写入Journal。
其附加投影检查标记不表示真实账户状态。原claim/result与辅助快照分别保留。
公开claim/result hash不能证明供应商响应真实性；本批未取得响应，没有股票/行业完整性结论。
失败安全分类无法确定具体网络根因，不输出原生异常或凭据，不另发权限/网络探测。
最终提交前对tracked/untracked非ignored文件检查明文、编码及解码凭据，结果同步PR描述；
private/Raw/审批不force-add。作者保全摘要不能代替Reviewer访问私有证据。
