---
name: a-share-research
description: Structure A-share company and catalyst research with point-in-time evidence and trade-plan readiness checks. Use for research reviews; this skeleton does not implement strategies or authorize trades.
---

# A-share Research Workflow Skeleton

Phase 0 supplies only the future workflow. Do not fetch real market data or
implement a strategy under this phase. Follow the [data contract](../../docs/data_contract.md)
and [unapproved risk template](../../docs/risk_constitution.md); do not claim positive expectancy.

For a future authorized research task, use this order:

1. **Verify timestamps and availability.** State the decision cutoff, sources,
   publication/availability evidence and missing data. Exclude later information.
2. **Market context.** Describe the relevant state dimensions and uncertainty.
3. **Industry and theme context.** Separate formal membership from dynamic
   themes; identify actual economic links rather than headline associations.
4. **Primary-source verification.** Distinguish verified facts, interpretations
   and unresolved claims; prioritize filings and policy originals.
5. **Business and fundamentals.** Examine growth, earnings quality, balance
   sheet, profitability, valuation and governance using industry context.
6. **Catalyst and expectation change.** Explain novelty, transmission, materiality,
   timing, market reaction and evidence against the thesis.
7. **Price, relative strength and setup.** Identify the relevant independent
   strategy; price strength alone does not establish readiness.
8. **Risks and invalidating evidence.** Address execution constraints, gaps,
   liquidity and portfolio concentration; surface contradictory evidence.
9. **Trade-plan readiness.** Report what is established, unknown or missing.
   Human confirmation and manual broker execution remain separate steps.

No stock recommendations, fixed buy/sell thresholds or approved risk budgets are
provided. Future parameters belong in versioned configuration. This repository
skeleton is not installed into global skills or an automatic trading workflow.
