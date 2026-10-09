# Phase1 Contracts and Historical Time

The versioned source catalog is `config/phase1/contracts-v1.yaml`. `python -m astock.phase1 specs` lists its 23 executable contracts. Contracts retain native identifiers, exact wire fields, nullable values, units, natural keys, date-axis semantics, source URLs and verified/unknown caps. Unknown envelope business keys, duplicate keys/rows, nonfinite numerics, wrong scope, partial calendars and known-cap truncation stop acquisition. Diagnostic `detail/count/has_more` fields are typed and preserved; their values never prove historical completeness.

## Domains and source claims

| Domain | Provider/raw inputs | Evidenced normalized input |
|---|---|---|
| Security | `stock_basic` L/D/P; `bak_basic` archive | `listing_episodes`, `security_identifiers` |
| Calendar | `trade_cal` with every civil date and pretrade relations | Civil validation; leading predecessor separately uncertified |
| Market/status | `daily`, `daily_basic`, `adj_factor`, `stk_limit`, `stock_st`, `suspend_d` | `security_status`; single-day source events do not forward-fill |
| Financial | `income`, `balancesheet`, `cashflow`, `fina_indicator` | Immutable report/company-type/publication/update vintages |
| Industry | `index_classify`, `index_member_all` | `industry_membership` with classification version, level and half-open exit |
| Rules | Official archived document receipts | `rule_history` exchange/board/status/effective intervals and explicit unknowns |
| Reference | `index_basic`, `index_daily` | `market_crosscheck` independent evidence and normalized units |

Financial fields are intentionally core: income totals/net income/EPS/bank interest, balance assets/liabilities/equity/bank cash reserve, cash-flow net profit/operating/investing/financing and indicator EPS/ROE/ROA/margin/leverage. Missing metrics stay NULL. Ordinary per-security endpoints are used; no VIP/account entitlement is assumed. `fina_indicator.start_date/end_date` selects report periods, unlike announcement windows of the other three APIs. Report/company types remain distinct; revisions never overwrite old observations. Raw bank fields can be unknown without inventing general-company equivalents.

Source stock names/current statuses and current `bak_basic.industry` are claims, not historical episodes or membership intervals. `bak_basic` documentation starts archival coverage in 2016; it cannot fill 2013–2015 evidence gaps. Provider industry removal-day inclusivity and taxonomy lineage require approved evidence. Native code changes require explicit mappings and compatible listing episodes; same names, suffixes or reused six-digit codes never merge securities.

## Time and knowledge

Every fact carries event/report date, effective half-open interval, optional `published_at`, `available_at`, `retrieved_at`, precision, knowledge basis, immutable source object/row and lineage. SQL history views expose identifier, episode, financial, industry and rule versions from `p1_fact`.

Current downloads default to availability at retrieval. An old `ann_date` does not prove that the downloaded value was historically known. Publication mode requires a reviewed version-specific policy and actual evidence bytes. Date-only publication keeps `published_at=NULL` and can use an explicit conservative next-open-session 09:30 Shanghai availability rule only with complete intervening civil dates. Unknown timestamps/vintages are not backdated. Conflicting same-time versions are quarantined.

Queries first filter knowledge by as-of, then choose known versions and apply event/effective intervals. Later financial or status corrections do not rewrite earlier queries. Industry versions require an explicit taxonomy when ambiguous. Adjustment requires known positive factors at event and an anchor no later than as-of; missing factors return unknown. Rules require exchange/board/status, IPO listing age and complete civil-calendar coverage. Sell delay is measured in trading days after purchase, independently of cash settlement. Buy minimum/increment checks leave odd-lot sell policy and actual fills uncertified.

An as-of later than the event day is explicitly `CURRENT_RECONSTRUCTION`, not contemporaneous decision information. Same-day queries are demonstrated separately, including no early access to a closing bar. Production archived-vintage adoption references exact existing raw and actual official version evidence under the signed fact policy. Source values cannot be edited to fit that evidence; a mismatch stops the interpretation. Original FAILED calendars remain FAILED even when a new normalized derivation is independently adopted.

## Integrity and admission

`p1_attempt/event/receipt` separates consumption, validated raw capture and completeness. `p1_fact/generation/lineage/quality` publishes atomic reproducible generations. `p1_derivative_validation` retains new validation time/hash for an old failed body without changing its old receipt history. Captures require five physical files and in-transaction readback; rebuilds and as-of reads verify retained source descriptors. Full original protection remains mandatory.

Production fact adoption requires a separate exact policy/package license and actual document receipts. No current package grants it. RAW_ONLY, fixture software acceptance, scope completeness and final research eligibility remain separate. Existing402060 findings are preserved; quality groups acquisition/contract/identity/session/vintage/taxonomy/rule/missing-bar and cross-source conflict reasons by dataset, period, venue and episode. NULL is never replaced by zero, missing bars never imply suspension, and independent source disagreements never silently overwrite prices.
